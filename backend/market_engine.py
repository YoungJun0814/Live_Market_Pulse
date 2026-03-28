"""
market_sentiment_engine.py
===========================
Complete US Market Sentiment Engine - All 5 Layers
  Layer 1: Price Signals        (yfinance)
  Layer 2: Market Breadth       (yfinance - 200MA breadth, RSI, 52w highs/lows)
  Layer 3: Options Market       (yfinance options chain - P/C ratio, IV, Skew)
  Layer 4: Macro / Economic     (FRED API)
  Layer 5: Sentiment Surveys    (CNN Fear & Greed, Google Trends)

Install:
    pip install yfinance pandas fastapi uvicorn requests fredapi pytrends

Run API server:
    uvicorn market_sentiment_engine:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    GET /                       - service info
    GET /health                 - system status
    GET /snapshot/full          - all 5 layers + composite score + directional split
    GET /snapshot/prices        - Layer 1 only
    GET /snapshot/breadth       - Layer 2 only
    GET /snapshot/options       - Layer 3 only
    GET /snapshot/macro         - Layer 4 only
    GET /snapshot/surveys       - Layer 5 only
    GET /snapshot/sentiment     - composite score + directional split + key signals (best for Gemini)
"""

import os
import re
import logging
import time
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
load_dotenv()  # loads backend/.env

import pandas as pd
import requests
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# -- Optional imports ----------------------------------------------------------
try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


# -----------------------------------------------------------------------------
# CONFIG  (all secrets loaded from .env)
# -----------------------------------------------------------------------------
FRED_API_KEY      = os.getenv("FRED_API_KEY", "")   # set in backend/.env
CACHE_TTL_SECONDS = 300                              # 5-minute default cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# -- Shared HTTP session (browser headers to reduce blocking) ------------------
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control":   "no-cache",
})


# -----------------------------------------------------------------------------
# TICKER REGISTRY
# -----------------------------------------------------------------------------
TICKERS = {
    # -- Equity Indices --------------------------------------------------------
    "^GSPC":     "S&P 500",
    "^IXIC":     "NASDAQ Composite",
    "^DJI":      "Dow Jones Industrial Average",
    "^RUT":      "Russell 2000 (Small-Cap)",
    "^NDX":      "NASDAQ-100",
    "^MID":      "S&P MidCap 400",
    # -- Volatility -----------------------------------------------------------
    "^VIX":      "CBOE Volatility Index (VIX)",
    "^VXN":      "NASDAQ Volatility (VXN)",
    "^RVX":      "Russell 2000 Volatility (RVX)",
    "^VVIX":     "VIX of VIX (VVIX)",
    # -- Treasury Yields -------------------------------------------------------
    "^IRX":      "13-Week T-Bill Yield (3M)",
    "^FVX":      "5-Year Treasury Yield",
    "^TNX":      "10-Year Treasury Yield",
    "^TYX":      "30-Year Treasury Yield",
    # -- Treasury ETFs ---------------------------------------------------------
    "SHY":       "iShares 1-3 Year Treasury ETF",
    "IEF":       "iShares 7-10 Year Treasury ETF",
    "TLT":       "iShares 20+ Year Treasury ETF",
    "TIPS":      "iShares TIPS Bond ETF",
    # -- Credit ----------------------------------------------------------------
    "HYG":       "iShares High Yield Corporate Bond ETF",
    "LQD":       "iShares Investment Grade Corp Bond ETF",
    "JNK":       "SPDR Bloomberg High Yield Bond ETF",
    "EMB":       "iShares JP Morgan EM Bond ETF",
    # -- Commodities -----------------------------------------------------------
    "GC=F":      "Gold Futures",
    "SI=F":      "Silver Futures",
    "CL=F":      "Crude Oil WTI Futures",
    "BZ=F":      "Brent Crude Oil Futures",
    "NG=F":      "Natural Gas Futures",
    "HG=F":      "Copper Futures",
    "ZC=F":      "Corn Futures",
    "ZW=F":      "Wheat Futures",
    # -- FX -------------------------------------------------------------------
    "DX-Y.NYB":  "US Dollar Index (DXY)",
    "EURUSD=X":  "EUR/USD",
    "USDJPY=X":  "USD/JPY",
    "GBPUSD=X":  "GBP/USD",
    "USDCNH=X":  "USD/CNH (Offshore Yuan)",
    # -- Sector ETFs -----------------------------------------------------------
    "XLK":       "Technology",
    "XLF":       "Financials",
    "XLE":       "Energy",
    "XLV":       "Health Care",
    "XLI":       "Industrials",
    "XLC":       "Communication Services",
    "XLY":       "Consumer Discretionary",
    "XLP":       "Consumer Staples",
    "XLU":       "Utilities",
    "XLRE":      "Real Estate",
    "XLB":       "Materials",
    # -- Broad ETFs ------------------------------------------------------------
    "SPY":       "S&P 500 ETF",
    "QQQ":       "NASDAQ-100 ETF",
    "IWM":       "Russell 2000 ETF",
    "ARKK":      "ARK Innovation ETF (Risk Appetite)",
    "GLD":       "Gold ETF",
    "USO":       "Oil ETF",
    # -- Crypto ----------------------------------------------------------------
    "BTC-USD":   "Bitcoin",
    "ETH-USD":   "Ethereum",
    # -- Global ----------------------------------------------------------------
    "^N225":     "Nikkei 225 (Japan)",
    "^HSI":      "Hang Seng (Hong Kong)",
    "^FTSE":     "FTSE 100 (UK)",
    "^GDAXI":    "DAX (Germany)",
    # -- Macro ETFs ------------------------------------------------------------
    "IAU":       "iShares Gold Trust",
    "PDBC":      "Invesco Commodity Diversified",
    "DBB":       "Base Metals ETF",
}

CATEGORY_MAP = {
    "^GSPC": "equity_indices",  "^IXIC": "equity_indices",
    "^DJI":  "equity_indices",  "^RUT":  "equity_indices",
    "^NDX":  "equity_indices",  "^MID":  "equity_indices",
    "SPY":   "equity_indices",  "QQQ":   "equity_indices",
    "IWM":   "equity_indices",
    "^VIX":  "volatility",      "^VXN":  "volatility",
    "^RVX":  "volatility",      "^VVIX": "volatility",
    "ARKK":  "volatility",
    "^IRX":  "treasury_yields", "^FVX":  "treasury_yields",
    "^TNX":  "treasury_yields", "^TYX":  "treasury_yields",
    "SHY":   "treasury_etfs",   "IEF":   "treasury_etfs",
    "TLT":   "treasury_etfs",   "TIPS":  "treasury_etfs",
    "HYG":   "credit",          "LQD":   "credit",
    "JNK":   "credit",          "EMB":   "credit",
    "GC=F":  "commodities",     "SI=F":  "commodities",
    "CL=F":  "commodities",     "BZ=F":  "commodities",
    "NG=F":  "commodities",     "HG=F":  "commodities",
    "ZC=F":  "commodities",     "ZW=F":  "commodities",
    "GLD":   "commodities",     "USO":   "commodities",
    "DX-Y.NYB": "fx",           "EURUSD=X": "fx",
    "USDJPY=X": "fx",           "GBPUSD=X": "fx",
    "USDCNH=X": "fx",
    "XLK":   "sectors",         "XLF":   "sectors",
    "XLE":   "sectors",         "XLV":   "sectors",
    "XLI":   "sectors",         "XLC":   "sectors",
    "XLY":   "sectors",         "XLP":   "sectors",
    "XLU":   "sectors",         "XLRE":  "sectors",
    "XLB":   "sectors",
    "BTC-USD": "crypto",        "ETH-USD": "crypto",
    "^N225": "global",          "^HSI":  "global",
    "^FTSE": "global",          "^GDAXI": "global",
    "IAU":   "macro_etfs",      "PDBC":  "macro_etfs",
    "DBB":   "macro_etfs",
}

# Top 50 S&P 500 constituents for breadth calculation
SP500_SAMPLE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B",
    "TSLA", "AVGO", "JPM", "LLY", "UNH", "V", "XOM", "MA", "JNJ",
    "PG", "HD", "MRK", "COST", "ABBV", "CVX", "ORCL", "BAC", "KO",
    "AMD", "NFLX", "PEP", "TMO", "WMT", "CSCO", "CRM", "ACN", "LIN",
    "MCD", "ABT", "DHR", "TXN", "ADBE", "PM", "NKE", "NEE", "QCOM",
    "INTC", "RTX", "UPS", "HON", "IBM", "CAT",
]


# -----------------------------------------------------------------------------
# CACHE
# -----------------------------------------------------------------------------
_cache_store: dict = {}

def cached(ttl: int = CACHE_TTL_SECONDS):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{str(args[1:])}:{str(kwargs)}"
            now = time.time()
            if key in _cache_store:
                result, ts = _cache_store[key]
                if now - ts < ttl:
                    logger.info(f"[CACHE HIT] {fn.__name__}")
                    return result
            result = fn(*args, **kwargs)
            _cache_store[key] = (result, now)
            return result
        return wrapper
    return decorator


# -----------------------------------------------------------------------------
# LAYER 5 HELPERS
# -----------------------------------------------------------------------------

# def _score_to_label(score: float) -> str:
#     if score <= 20:   return "Extreme Fear"
#     if score <= 40:   return "Fear"
#     if score <= 60:   return "Neutral"
#     if score <= 80:   return "Greed"
#     return "Extreme Greed"
def _score_to_label(score: float) -> str:
    if score <= -60:  return "Extreme Bearish"
    if score <= -20:  return "Bearish"
    if score <= 20:   return "Neutral"
    if score <= 60:   return "Bullish"
    return "Extreme Bullish"


def _fetch_cnn_fear_greed() -> dict:
    """
    CNN Fear & Greed with 3-level fallback:
      1. Official CNN dataviz endpoint
      2. Alternative.me public API
      3. HTML scrape of CNN markets page
    """
    # -- Level 1: Official CNN endpoint ---------------------------------------
    try:
        resp = _SESSION.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json()
        fg  = raw.get("fear_and_greed", {})
        if fg and fg.get("score"):
            score = float(fg["score"])
            return {
                "score":  round(score, 1),
                "label":  fg.get("rating", _score_to_label(score)),
                "source": "CNN Fear & Greed (official)",
                "as_of":  fg.get("timestamp", ""),
            }
    except Exception:
        pass

    # -- Level 2: Alternative.me -----------------------------------------------
    try:
        resp = _SESSION.get(
            "https://api.alternative.me/fng/?limit=1&format=json",
            timeout=10,
        )
        resp.raise_for_status()
        raw  = resp.json()
        item = raw.get("data", [{}])[0]
        if item.get("value"):
            score = float(item["value"])
            ts    = item.get("timestamp")
            return {
                "score":  round(score, 1),
                "label":  item.get("value_classification", _score_to_label(score)),
                "source": "Alternative.me Fear & Greed",
                "as_of":  datetime.utcfromtimestamp(int(ts)).isoformat() if ts else "",
            }
    except Exception:
        pass

    # -- Level 3: HTML scrape CNN markets page ---------------------------------
    try:
        resp  = _SESSION.get("https://www.cnn.com/markets/fear-and-greed", timeout=15)
        match = re.search(r'"score"\s*:\s*(\d+\.?\d*)', resp.text)
        if match:
            score = float(match.group(1))
            return {
                "score":  round(score, 1),
                "label":  _score_to_label(score),
                "source": "CNN Fear & Greed (HTML scrape)",
                "as_of":  datetime.utcnow().isoformat() + "Z",
            }
    except Exception:
        pass

    return {"error": "All CNN F&G endpoints failed - try again later."}


# -----------------------------------------------------------------------------
# MAIN ENGINE CLASS
# -----------------------------------------------------------------------------
class MarketSentimentEngine:

    def __init__(self):
        self.fred = Fred(api_key=FRED_API_KEY) if FRED_AVAILABLE else None

    # ==========================================================================
    # LAYER 1 - PRICE SIGNALS
    # ==========================================================================

    @cached(ttl=300)
    def get_price_signals(self) -> dict:
        logger.info("Layer 1 | Fetching price signals...")
        symbols = list(TICKERS.keys())

        try:
            raw = yf.download(
                symbols, period="5d", interval="1d",
                progress=False, auto_adjust=True, group_by="ticker",
            )
        except Exception as e:
            logger.error(f"Bulk download failed: {e}")
            return {}

        grouped: dict = {cat: {} for cat in set(CATEGORY_MAP.values())}

        for sym in symbols:
            try:
                close = (
                    raw[sym]["Close"].dropna()
                    if len(symbols) > 1
                    else raw["Close"].dropna()
                )
                if close.empty:
                    continue
                latest = float(close.iloc[-1])
                prev   = float(close.iloc[-2]) if len(close) >= 2 else latest
                chg    = ((latest - prev) / prev) * 100
                cat    = CATEGORY_MAP.get(sym, "other")
                grouped.setdefault(cat, {})[sym] = {
                    "symbol":     sym,
                    "label":      TICKERS.get(sym, sym),
                    "price":      round(latest, 4),
                    "prev_close": round(prev, 4),
                    "change_pct": round(chg, 4),
                    "direction":  "up" if chg > 0 else ("down" if chg < 0 else "flat"),
                }
            except Exception:
                continue

        signals = self._compute_price_derived_signals(grouped)
        return {"data": grouped, "signals": signals}

    def _compute_price_derived_signals(self, grouped: dict) -> dict:
        signals = {}

        # VIX fear level
        vix_data = grouped.get("volatility", {}).get("^VIX")
        if vix_data:
            v = vix_data["price"]
            signals["vix_fear_level"] = {
                "value": v,
                "label": (
                    "Extreme Fear" if v >= 30 else
                    "Fear"         if v >= 20 else
                    "Neutral"      if v >= 15 else
                    "Greed"        if v >= 12 else
                    "Extreme Greed"
                ),
                "interpretation": "Core fear gauge. >20 = markets pricing in stress.",
            }

        # Yield curve 10Y - 3M
        y10 = grouped.get("treasury_yields", {}).get("^TNX", {}).get("price")
        y3m = grouped.get("treasury_yields", {}).get("^IRX", {}).get("price")
        if y10 and y3m:
            # Yahoo stores yields x10 (e.g. 42.1 = 4.21%)
            spread = round((y10 - y3m) / 10, 3)
            signals["yield_curve_10y_3m"] = {
                "ten_year_pct":    round(y10 / 10, 3),
                "three_month_pct": round(y3m / 10, 3),
                "spread_pct":      spread,
                "inverted":        spread < 0,
                "label": (
                    "Deeply Inverted - Strong Recession Risk" if spread < -0.5 else
                    "Inverted - Recession Warning"            if spread < 0    else
                    "Flat - Caution"                          if spread < 0.5  else
                    "Normal - Healthy"                        if spread < 1.5  else
                    "Steep - Expansion"
                ),
            }

        # Dollar strength
        dxy = grouped.get("fx", {}).get("DX-Y.NYB")
        if dxy:
            signals["dollar_strength"] = {
                "value":  dxy["price"],
                "change": dxy["change_pct"],
                "label":  (
                    "Strong Dollar" if dxy["change_pct"] > 0.3  else
                    "Weak Dollar"   if dxy["change_pct"] < -0.3 else
                    "Stable"
                ),
                "interpretation": "Strong USD = risk-off, commodities pressure.",
            }

        # Gold vs S&P flight-to-safety
        gold = grouped.get("commodities", {}).get("GC=F", {}).get("change_pct")
        sp   = grouped.get("equity_indices", {}).get("^GSPC", {}).get("change_pct")
        if gold is not None and sp is not None:
            signals["gold_vs_sp500"] = {
                "gold_chg":  gold,
                "sp500_chg": sp,
                "risk_off":  gold > 0.5 and sp < -0.3,
                "label": (
                    "Flight to Safety" if gold > 0.5 and sp < -0.3 else
                    "Risk-On"          if sp > 0.5 and gold < 0     else
                    "Mixed"
                ),
            }

        # Sector rotation
        defensive = ["XLU", "XLP", "XLV"]
        cyclical  = ["XLK", "XLY", "XLF"]
        def_chg   = [grouped.get("sectors", {}).get(s, {}).get("change_pct", 0) for s in defensive]
        cyc_chg   = [grouped.get("sectors", {}).get(s, {}).get("change_pct", 0) for s in cyclical]
        if any(def_chg) and any(cyc_chg):
            avg_def = sum(def_chg) / len(def_chg)
            avg_cyc = sum(cyc_chg) / len(cyc_chg)
            signals["sector_rotation"] = {
                "defensive_avg_chg": round(avg_def, 3),
                "cyclical_avg_chg":  round(avg_cyc, 3),
                "rotation": (
                    "Risk-Off (Defensive Leading)" if avg_def > avg_cyc + 0.3 else
                    "Risk-On (Cyclical Leading)"   if avg_cyc > avg_def + 0.3 else
                    "Neutral"
                ),
            }

        return signals

    # ==========================================================================
    # LAYER 2 - MARKET BREADTH
    # ==========================================================================

    @cached(ttl=600)
    def get_market_breadth(self) -> dict:
        logger.info("Layer 2 | Computing market breadth...")

        try:
            raw = yf.download(
                SP500_SAMPLE, period="1y", interval="1d",
                progress=False, auto_adjust=True, group_by="ticker",
            )
        except Exception as e:
            return {"error": str(e)}

        above_200ma = above_50ma = at_52w_high = at_52w_low = total = 0
        rsi_values = []

        for sym in SP500_SAMPLE:
            try:
                close = raw[sym]["Close"].dropna()
                if len(close) < 200:
                    continue
                total  += 1
                latest  = float(close.iloc[-1])
                ma200   = float(close.rolling(200).mean().iloc[-1])
                ma50    = float(close.rolling(50).mean().iloc[-1])
                high52  = float(close.tail(252).max())
                low52   = float(close.tail(252).min())

                if latest > ma200:          above_200ma += 1
                if latest > ma50:           above_50ma  += 1
                if latest >= high52 * 0.98: at_52w_high += 1
                if latest <= low52  * 1.02: at_52w_low  += 1

                delta = close.diff()
                gain  = delta.clip(lower=0).rolling(14).mean()
                loss  = (-delta.clip(upper=0)).rolling(14).mean()
                rs    = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 1
                rsi_values.append(round(100 - 100 / (1 + rs), 1))
            except Exception:
                continue

        if total == 0:
            return {"error": "No breadth data available"}

        pct_200    = round(above_200ma / total * 100, 1)
        avg_rsi    = round(sum(rsi_values) / len(rsi_values), 1) if rsi_values else None
        overbought = sum(1 for r in rsi_values if r > 70)
        oversold   = sum(1 for r in rsi_values if r < 30)

        return {
            "sample_size":         total,
            "pct_above_200day_ma": pct_200,
            "pct_above_50day_ma":  round(above_50ma  / total * 100, 1),
            "pct_at_52w_high":     round(at_52w_high / total * 100, 1),
            "pct_at_52w_low":      round(at_52w_low  / total * 100, 1),
            "avg_rsi":             avg_rsi,
            "overbought_pct":      round(overbought / total * 100, 1),
            "oversold_pct":        round(oversold   / total * 100, 1),
            "breadth_label": (
                "Very Healthy"  if pct_200 > 70 else
                "Healthy"       if pct_200 > 55 else
                "Deteriorating" if pct_200 > 40 else
                "Weak"          if pct_200 > 25 else
                "Extremely Weak"
            ),
            "interpretation": (
                f"{pct_200}% of S&P 500 sample stocks are above their 200-day MA."
            ),
        }

    # ==========================================================================
    # LAYER 3 - OPTIONS MARKET
    # ==========================================================================

    @cached(ttl=300)
    def get_options_signals(self) -> dict:
        logger.info("Layer 3 | Fetching options market data...")
        results = {}

        for sym in ["SPY", "QQQ", "IWM"]:
            try:
                ticker     = yf.Ticker(sym)
                exp_dates  = ticker.options
                if not exp_dates:
                    continue

                near_chain = ticker.option_chain(exp_dates[0])
                next_chain = ticker.option_chain(exp_dates[1]) if len(exp_dates) > 1 else None
                puts       = near_chain.puts
                calls      = near_chain.calls

                put_vol  = puts["volume"].fillna(0).sum()
                call_vol = calls["volume"].fillna(0).sum()
                pc_ratio = round(put_vol / call_vol, 3) if call_vol > 0 else None

                spot = ticker.fast_info.last_price

                def get_atm_iv(chain_df, s):
                    if chain_df is None or chain_df.empty:
                        return None
                    chain_df         = chain_df.copy()
                    chain_df["dist"] = abs(chain_df["strike"] - s)
                    atm              = chain_df.nsmallest(1, "dist")
                    iv               = atm["impliedVolatility"].values[0]
                    return round(float(iv) * 100, 2) if pd.notna(iv) else None

                near_iv  = get_atm_iv(calls, spot)
                next_iv  = get_atm_iv(next_chain.calls if next_chain else None, spot)

                otm_puts = puts[puts["strike"] < spot * 0.95]
                otm_iv   = (
                    round(float(otm_puts["impliedVolatility"].mean()) * 100, 2)
                    if not otm_puts.empty else None
                )
                skew = round(otm_iv - near_iv, 2) if (otm_iv and near_iv) else None

                put_oi  = puts["openInterest"].fillna(0).sum()
                call_oi = calls["openInterest"].fillna(0).sum()

                results[sym] = {
                    "expiry_near":           exp_dates[0],
                    "put_call_volume_ratio": pc_ratio,
                    "put_call_oi_ratio":     round(put_oi / call_oi, 3) if call_oi > 0 else None,
                    "atm_iv_near_pct":       near_iv,
                    "atm_iv_next_pct":       next_iv,
                    "iv_term_structure": (
                        "Contango (normal)"      if (near_iv and next_iv and next_iv > near_iv) else
                        "Backwardation (stress)" if (near_iv and next_iv and next_iv < near_iv) else
                        "Flat"
                    ),
                    "otm_put_iv_pct":        otm_iv,
                    "iv_skew_pct":           skew,
                    "skew_interpretation": (
                        "High downside fear"   if skew and skew > 5 else
                        "Moderate protection"  if skew and skew > 2 else
                        "Low hedging demand"
                    ),
                    "pc_ratio_signal": (
                        "Extreme Fear"   if pc_ratio and pc_ratio > 1.2 else
                        "Fear"           if pc_ratio and pc_ratio > 0.9 else
                        "Neutral"        if pc_ratio and pc_ratio > 0.7 else
                        "Greed"          if pc_ratio and pc_ratio > 0.5 else
                        "Extreme Greed"
                    ),
                }
            except Exception as e:
                logger.warning(f"Options [{sym}] error: {e}")
                results[sym] = {"error": str(e)}

        return results

    # ==========================================================================
    # LAYER 4 - MACRO / FRED
    # ==========================================================================

    @cached(ttl=3600)
    def get_macro_signals(self) -> dict:
        logger.info("Layer 4 | Fetching macro data from FRED...")

        if not FRED_AVAILABLE or self.fred is None:
            return {"error": "fredapi not installed or FRED_API_KEY not configured"}

        FRED_SERIES = {
            "fed_funds_rate":        ("FEDFUNDS",         "Federal Funds Rate (%)",          1),
            "cpi_yoy":               ("CPIAUCSL",         "CPI YoY Inflation (%)",           13),
            "core_cpi_yoy":          ("CPILFESL",         "Core CPI YoY (%)",                13),
            "pce_yoy":               ("PCEPI",            "PCE Inflation YoY (%)",           13),
            "unemployment":          ("UNRATE",           "Unemployment Rate (%)",            2),
            "nonfarm_payrolls":      ("PAYEMS",           "Nonfarm Payrolls (thousands)",     2),
            "consumer_confidence":   ("UMCSENT",          "U Michigan Consumer Sentiment",    2),
            "m2_money_supply":       ("M2SL",             "M2 Money Supply ($B)",             2),
            "10y_breakeven":         ("T10YIE",           "10Y Breakeven Inflation Rate",     2),
            "5y_breakeven":          ("T5YIE",            "5Y Breakeven Inflation Rate",      2),
            "credit_spread_hy":      ("BAMLH0A0HYM2",     "High Yield OAS Spread (%)",        2),
            "credit_spread_ig":      ("BAMLC0A0CM",       "Investment Grade OAS Spread (%)",  2),
            "gdp_growth":            ("A191RL1Q225SBEA",  "Real GDP Growth QoQ (%)",          2),
            "industrial_production": ("INDPRO",           "Industrial Production Index",      2),
            "retail_sales":          ("RSAFS",            "Retail Sales ($M)",                2),
            "housing_starts":        ("HOUST",            "Housing Starts (thousands)",       2),
        }

        data = {}
        for key, (series_id, label, limit) in FRED_SERIES.items():
            try:
                series = self.fred.get_series(series_id, limit=limit).dropna()
                if series.empty:
                    continue
                latest = float(series.iloc[-1])
                prev   = float(series.iloc[-2]) if len(series) >= 2 else latest
                yoy    = None
                if "yoy" in key and len(series) >= 13:
                    yoy = round(
                        ((series.iloc[-1] - series.iloc[-13]) / series.iloc[-13]) * 100, 2
                    )
                data[key] = {
                    "label":     label,
                    "value":     yoy if yoy is not None else round(latest, 3),
                    "prev":      round(prev, 3),
                    "change":    round(latest - prev, 3),
                    "as_of":     str(series.index[-1].date()),
                    "series_id": series_id,
                }
            except Exception as e:
                logger.warning(f"FRED [{series_id}] error: {e}")
                data[key] = {"error": str(e)}

        signals = self._compute_macro_signals(data)
        return {"data": data, "signals": signals}

    def _compute_macro_signals(self, data: dict) -> dict:
        signals = {}

        fed_rate = data.get("fed_funds_rate", {}).get("value")
        cpi      = data.get("cpi_yoy",        {}).get("value")
        if fed_rate and cpi:
            real_rate = round(fed_rate - cpi, 2)
            signals["fed_policy_stance"] = {
                "fed_rate":  fed_rate,
                "cpi_yoy":   cpi,
                "real_rate": real_rate,
                "stance": (
                    "Restrictive"    if real_rate > 0.5  else
                    "Neutral"        if real_rate > -0.5 else
                    "Accommodative"
                ),
            }

        unemp     = data.get("unemployment",        {}).get("value")
        gdp       = data.get("gdp_growth",          {}).get("value")
        cc        = data.get("consumer_confidence", {}).get("value")
        hy_spread = data.get("credit_spread_hy",    {}).get("value")
        flags     = []
        if gdp       and gdp < 0:          flags.append("Negative GDP")
        if unemp     and unemp > 5:        flags.append("Rising Unemployment")
        if cc        and cc < 70:          flags.append("Low Consumer Confidence")
        if hy_spread and hy_spread > 500:  flags.append("Wide HY Spreads")
        signals["recession_risk"] = {
            "flags":      flags,
            "risk_level": (
                "High"     if len(flags) >= 3 else
                "Elevated" if len(flags) >= 2 else
                "Moderate" if len(flags) >= 1 else
                "Low"
            ),
            "score": len(flags),
        }

        breakeven = data.get("10y_breakeven", {}).get("value")
        if cpi and breakeven:
            signals["inflation_regime"] = {
                "cpi_yoy":            cpi,
                "market_expects_pct": breakeven,
                "regime": (
                    "Hyperinflationary" if cpi > 8 else
                    "High Inflation"    if cpi > 4 else
                    "Moderate"          if cpi > 2 else
                    "Low / Deflationary"
                ),
            }

        return signals

    # ==========================================================================
    # LAYER 5 - SENTIMENT SURVEYS
    # ==========================================================================

    @cached(ttl=900)
    def get_sentiment_surveys(self) -> dict:
        logger.info("Layer 5 | Fetching sentiment surveys...")
        results = {}

        # 1. CNN Fear & Greed (3-level fallback)
        results["cnn_fear_greed"] = _fetch_cnn_fear_greed()

        # 2. Google Trends
        if PYTRENDS_AVAILABLE:
            try:
                pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
                keywords = ["stock market crash", "recession 2025", "market bubble", "buy the dip"]
                pytrends.build_payload(keywords, timeframe="now 7-d", geo="US")
                trend_df = pytrends.interest_over_time()
                if not trend_df.empty:
                    latest      = trend_df.iloc[-1]
                    fear_score  = int(
                        (latest.get("stock market crash", 0) +
                         latest.get("recession 2025", 0)) / 2
                    )
                    greed_score = int(latest.get("buy the dip", 0))
                    results["google_trends"] = {
                        "fear_keywords_score":  fear_score,
                        "greed_keywords_score": greed_score,
                        "keywords": {k: int(latest.get(k, 0)) for k in keywords},
                        "trend_signal": (
                            "Fear Dominant"  if fear_score > greed_score + 20 else
                            "Greed Dominant" if greed_score > fear_score + 20 else
                            "Mixed"
                        ),
                        "source": "Google Trends (US, 7-day)",
                    }
            except Exception as e:
                results["google_trends"] = {"error": str(e)}
        else:
            results["google_trends"] = {"error": "pytrends not installed"}

        return results

    # ==========================================================================
    # DIRECTIONAL SPLIT  (NEW)
    # ==========================================================================

    def compute_directional_split(self, components: dict) -> dict:
        """
        Derive Bullish / Sideways / Bearish percentage from composite components.

        Each component already has a score 0-100 where:
          100 = maximum greed/bullish
            0 = maximum fear/bearish
           50 = perfectly neutral/sideways

        For every component with score S and weight W we compute three
        continuous contributions that always sum to W:

          bullish_w  = W x max(0, S - 50) / 50      -> peaks at S=100
          bearish_w  = W x max(0, 50 - S) / 50      -> peaks at S=0
          sideways_w = W x (1 - |S - 50| / 50)      -> peaks at S=50

        Final percentages = each bucket's total weight / sum of all weights x 100.
        The three values always add up to exactly 100%.

        The dominant direction is whichever bucket is largest,
        with a secondary label when one is within 10 pp of the leader.
        """
        if not components:
            return {
                "bullish_pct":  None,
                "sideways_pct": None,
                "bearish_pct":  None,
                "dominant":     "Insufficient Data",
                "breakdown":    {},
            }

        bull_w = side_w = bear_w = 0.0
        breakdown = {}

        for name, comp in components.items():
            s = float(comp["score"])   # 0-100
            w = float(comp["weight"])

            b  = max(0.0, s - 50) / 50 * w   # bullish contribution
            be = max(0.0, 50 - s) / 50 * w   # bearish contribution
            si = (1 - abs(s - 50) / 50) * w  # sideways contribution

            bull_w += b
            bear_w += be
            side_w += si

            breakdown[name] = {
                "score":       round(s, 1),
                "weight":      w,
                "bullish_w":   round(b, 2),
                "sideways_w":  round(si, 2),
                "bearish_w":   round(be, 2),
            }

        total = bull_w + side_w + bear_w
        if total == 0:
            return {
                "bullish_pct":  None,
                "sideways_pct": None,
                "bearish_pct":  None,
                "dominant":     "Insufficient Data",
                "breakdown":    breakdown,
            }

        bull_pct = round(bull_w / total * 100, 1)
        side_pct = round(side_w / total * 100, 1)
        # Ensure exactly 100 despite floating-point rounding
        bear_pct = round(100 - bull_pct - side_pct, 1)

        # Dominant label
        mx = max(bull_pct, side_pct, bear_pct)
        if bull_pct == mx:
            dominant = "Bullish"
        elif bear_pct == mx:
            dominant = "Bearish"
        else:
            dominant = "Sideways"

        # Secondary label: any other bucket within 10 pp of leader
        others = {
            "Bullish":  bull_pct,
            "Sideways": side_pct,
            "Bearish":  bear_pct,
        }
        near = [k for k, v in others.items() if k != dominant and mx - v <= 10]
        if near:
            dominant = f"{dominant} / {near[0]}"

        return {
            "bullish_pct":  bull_pct,
            "sideways_pct": side_pct,
            "bearish_pct":  bear_pct,
            "dominant":     dominant,
            "interpretation": (
                f"Bullish {bull_pct}% - Sideways {side_pct}% - Bearish {bear_pct}%. "
                f"Market leans {dominant}."
            ),
            "breakdown": breakdown,
        }

    # ==========================================================================
    # COMPOSITE FEAR & GREED SCORE
    # ==========================================================================

    def compute_composite_score(
        self,
        prices:  dict,
        breadth: dict,
        options: dict,
        macro:   dict,
        surveys: dict,
    ) -> dict:
        components     = {}
        weighted_total = 0.0
        weight_total   = 0

        def add(label: str, score: float, weight: int, reason: str = ""):
            nonlocal weighted_total, weight_total
            score = max(0.0, min(100.0, float(score)))
            components[label] = {"score": round(score, 1), "weight": weight, "reason": reason}
            weighted_total += score * weight
            weight_total   += weight

        # 1. VIX (25%)
        vix_val = prices.get("signals", {}).get("vix_fear_level", {}).get("value")
        if vix_val:
            add("vix", max(0, min(100, 100 - (vix_val - 10) * (100 / 30))),
                25, f"VIX={vix_val}")

        # 2. Market Breadth (20%)
        pct_200 = breadth.get("pct_above_200day_ma")
        if pct_200 is not None:
            add("breadth", max(0, min(100, (pct_200 - 30) * (100 / 40))),
                20, f"{pct_200}% above 200MA")

        # 3. Put/Call ratio - SPY (15%)
        pc_ratio = options.get("SPY", {}).get("put_call_volume_ratio")
        if pc_ratio:
            add("put_call_ratio", max(0, min(100, 100 - (pc_ratio - 0.5) * 100)),
                15, f"P/C={pc_ratio}")

        # 4. Yield Curve (10%)
        spread = prices.get("signals", {}).get("yield_curve_10y_3m", {}).get("spread_pct")
        if spread is not None:
            add("yield_curve", max(0, min(100, (spread + 1) * (100 / 2.5))),
                10, f"spread={spread}%")

        # 5. S&P 500 20-day momentum (15%)
        try:
            sp_hist = yf.download("^GSPC", period="3mo", interval="1d",
                                  progress=False, auto_adjust=True)
            close = sp_hist["Close"].squeeze().dropna()
            ma20  = float(close.rolling(20).mean().iloc[-1])
            pct   = ((float(close.iloc[-1]) - ma20) / ma20) * 100
            add("sp500_momentum", max(0, min(100, 50 + pct * 5)),
                15, f"{round(pct, 2)}% from 20MA")
        except Exception:
            pass

        # 6. HYG junk bond demand (10%)
        try:
            hyg_hist = yf.download("HYG", period="3mo", interval="1d",
                                   progress=False, auto_adjust=True)
            close = hyg_hist["Close"].squeeze().dropna()
            ma20  = float(close.rolling(20).mean().iloc[-1])
            pct   = ((float(close.iloc[-1]) - ma20) / ma20) * 100
            add("junk_bond_demand", max(0, min(100, 50 + pct * 15)),
                10, f"HYG {round(pct, 2)}% from 20MA")
        except Exception:
            pass

        # 7. CNN Fear & Greed (5%)
        cnn_score = surveys.get("cnn_fear_greed", {}).get("score")
        if cnn_score is not None:
            add("cnn_fear_greed", float(cnn_score), 5, f"CNN={cnn_score}")

        if weight_total == 0:
            return {
                "score":            None,
                "label":            "Insufficient Data",
                "components":       {},
                "directional_split": self.compute_directional_split({}),
            }

        # final = weighted_total / weight_total
        final_0_100 = weighted_total / weight_total
        # Map the internal 0-100 score to the external -100 to +100 scale.
        final_mapped = (final_0_100 - 50) * 2

        # -- Directional split derived from the same components ----------------
        directional = self.compute_directional_split(components)

        return {
            "score":             int(round(final_mapped)),  # Keep an integer score for the Hub contract.
            "label":             _score_to_label(final_mapped),
            "interpretation": (
                f"Composite score {int(round(final_mapped))}/100 (Scale -100 to +100). "
                f"Current sentiment: '{_score_to_label(final_mapped)}'."
            ),
            "components":        components,
            "weights_used":      weight_total,
            "directional_split": directional,
        }

    # ==========================================================================
    # MASTER ORCHESTRATOR
    # ==========================================================================

    def get_full_snapshot(self) -> dict:
        logger.info("RUN Running full 5-layer snapshot...")
        prices    = self.get_price_signals()
        breadth   = self.get_market_breadth()
        options   = self.get_options_signals()
        macro     = self.get_macro_signals()
        surveys   = self.get_sentiment_surveys()
        composite = self.compute_composite_score(prices, breadth, options, macro, surveys)
        return {
            "meta": {
                "fetched_at":   datetime.utcnow().isoformat() + "Z",
                "source":       "Yahoo Finance + FRED + CNN Fear & Greed + Google Trends",
                "layers_count": 5,
                "note":         "Prices ~15min delayed during market hours.",
            },
            "composite_sentiment": composite,
            "layer_1_prices":      prices,
            "layer_2_breadth":     breadth,
            "layer_3_options":     options,
            "layer_4_macro":       macro,
            "layer_5_surveys":     surveys,
        }


# -----------------------------------------------------------------------------
# FASTAPI APP
# -----------------------------------------------------------------------------
app = FastAPI(
    title="US Market Sentiment API",
    description="5-layer market sentiment engine: Prices, Breadth, Options, Macro, Surveys",
    version="2.3.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = MarketSentimentEngine()


@app.get("/", tags=["Info"])
def root():
    return {
        "service": "US Market Sentiment API",
        "version": "2.3.0",
        "endpoints": {
            "full snapshot":     "GET /snapshot/full",
            "prices only":       "GET /snapshot/prices",
            "breadth only":      "GET /snapshot/breadth",
            "options only":      "GET /snapshot/options",
            "macro only":        "GET /snapshot/macro",
            "surveys only":      "GET /snapshot/surveys",
            "sentiment summary": "GET /snapshot/sentiment  <- best for Gemini",
            "health":            "GET /health",
            "interactive docs":  "GET /docs",
        },
    }


@app.get("/health", tags=["Info"])
def health():
    return {
        "status":             "ok",
        "timestamp":          datetime.utcnow().isoformat() + "Z",
        "fred_available":     FRED_AVAILABLE,
        "pytrends_available": PYTRENDS_AVAILABLE,
        "cache_entries":      len(_cache_store),
    }


@app.get("/snapshot/full", tags=["Snapshot"])
def full_snapshot():
    """All 5 layers + composite score + directional split. First call takes ~15-30s."""
    try:
        return JSONResponse(engine.get_full_snapshot())
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/snapshot/prices", tags=["Snapshot"])
def prices():
    """Layer 1 - 60+ price tickers with change%, direction, derived signals."""
    try:
        return JSONResponse(engine.get_price_signals())
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/snapshot/breadth", tags=["Snapshot"])
def breadth():
    """Layer 2 - % above 200MA, RSI distribution, 52-week highs/lows."""
    try:
        return JSONResponse(engine.get_market_breadth())
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/snapshot/options", tags=["Snapshot"])
def options():
    """Layer 3 - Put/Call ratio, IV, IV skew for SPY / QQQ / IWM."""
    try:
        return JSONResponse(engine.get_options_signals())
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/snapshot/macro", tags=["Snapshot"])
def macro():
    """Layer 4 - FRED: CPI, unemployment, Fed rate, GDP, consumer confidence."""
    try:
        return JSONResponse(engine.get_macro_signals())
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/snapshot/surveys", tags=["Snapshot"])
def surveys():
    """Layer 5 - CNN Fear & Greed, Google Trends."""
    try:
        return JSONResponse(engine.get_sentiment_surveys())
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/snapshot/sentiment", tags=["Snapshot"])
def sentiment_summary():
    """
    Composite score + directional split + key signals - no raw data.
    Fastest meaningful endpoint. Ideal for passing directly to Gemini.
    """
    try:
        prices    = engine.get_price_signals()
        breadth   = engine.get_market_breadth()
        options   = engine.get_options_signals()
        macro     = engine.get_macro_signals()
        surveys   = engine.get_sentiment_surveys()
        composite = engine.compute_composite_score(prices, breadth, options, macro, surveys)

        return JSONResponse({
            "meta": {"fetched_at": datetime.utcnow().isoformat() + "Z"},

            # -- Core sentiment output ----------------------------------------
            "composite_sentiment": {
                "score":             composite.get("score"),
                "label":             composite.get("label"),
                "interpretation":    composite.get("interpretation"),
            },

            # -- NEW: Directional split ---------------------------------------
            "directional_split": composite.get("directional_split"),

            # -- Supporting signals -------------------------------------------
            "price_signals":   prices.get("signals", {}),
            "breadth_summary": {
                "pct_above_200ma": breadth.get("pct_above_200day_ma"),
                "breadth_label":   breadth.get("breadth_label"),
                "avg_rsi":         breadth.get("avg_rsi"),
            },
            "options_summary": {
                sym: {
                    "pc_ratio":  v.get("put_call_volume_ratio"),
                    "pc_signal": v.get("pc_ratio_signal"),
                    "atm_iv":    v.get("atm_iv_near_pct"),
                    "iv_skew":   v.get("iv_skew_pct"),
                }
                for sym, v in options.items()
                if isinstance(v, dict) and "error" not in v
            },
            "macro_signals":  macro.get("signals", {}),
            "survey_signals": {
                "cnn_score":           surveys.get("cnn_fear_greed", {}).get("score"),
                "cnn_label":           surveys.get("cnn_fear_greed", {}).get("label"),
                "cnn_source":          surveys.get("cnn_fear_greed", {}).get("source"),
                "google_trend_signal": surveys.get("google_trends", {}).get("trend_signal"),
                "google_keywords":     surveys.get("google_trends", {}).get("keywords"),
            },
        })
    except Exception as e:
        raise HTTPException(500, str(e))
    
@app.get("/api/hub_payload", tags=["Hackathon"])
def get_hub_payload():
    """
    Endpoint tailored for the Central Hub.
    Returns a payload aligned with the section 5-3 JSON contract.
    """
    try:
        prices    = engine.get_price_signals()
        breadth   = engine.get_market_breadth()
        options   = engine.get_options_signals()
        macro     = engine.get_macro_signals()
        surveys   = engine.get_sentiment_surveys()
        composite = engine.compute_composite_score(prices, breadth, options, macro, surveys)

        # The composite score is already expressed on the -100 to +100 scale.
        sentiment_score = composite.get("score", 0)

        # Helper for pulling the specific tickers needed by the Hub payload.
        def get_ticker_data(ticker):
            data = prices.get("data", {})
            for category in data.values():
                if ticker in category:
                    return category[ticker]
            return {"price": 0, "change_pct": 0}

        sp500_data = get_ticker_data("^GSPC")
        vix_data   = get_ticker_data("^VIX")
        
        # Dynamic confidence calculation.
        # 1. Coverage score: up to 100, based on the total captured engine weight.
        coverage_score = composite.get("weights_used", 0)

        # 2. Consensus score: up to 100, based on the dominant directional share.
        split = composite.get("directional_split", {})
        bull_pct = split.get("bullish_pct") or 0
        bear_pct = split.get("bearish_pct") or 0
        side_pct = split.get("sideways_pct") or 0
        consensus_score = max(bull_pct, bear_pct, side_pct)

        # Weight coverage at 70% and consensus at 30%.
        raw_confidence = (coverage_score * 0.7) + (consensus_score * 0.3)
        
        # Clamp confidence into the 0-100 integer range.
        dynamic_confidence = max(0, min(100, int(round(raw_confidence))))

        # Build a one-line signal summary from the five-layer engine output.
        dominant = composite.get("directional_split", {}).get("dominant", "Neutral")
        signal_text = f"S&P {sp500_data['change_pct']}%, VIX {vix_data['change_pct']}% - {dominant} sentiment based on 5-layer breadth & macro analysis."

        payload = {
            "source": "market_data",
            "sentiment_score": sentiment_score,
            "confidence": dynamic_confidence,  # Use the dynamic confidence score above.
            "signal": signal_text,
            "details": {
                "sp500": {"price": sp500_data["price"], "change_pct": sp500_data["change_pct"]},
                "nasdaq": {
                    "price": get_ticker_data("^IXIC")["price"],
                    "change_pct": get_ticker_data("^IXIC")["change_pct"],
                },
                "vix":   {"price": vix_data["price"],   "change_pct": vix_data["change_pct"]},
                "oil":   {"price": get_ticker_data("CL=F")["price"], "change_pct": get_ticker_data("CL=F")["change_pct"]},
                "dxy":   {"price": get_ticker_data("DX-Y.NYB")["price"], "change_pct": get_ticker_data("DX-Y.NYB")["change_pct"]},
                "gold":  {"price": get_ticker_data("GC=F")["price"], "change_pct": get_ticker_data("GC=F")["change_pct"]},
                # Yahoo stores 10Y yields like 4.25% as 42.5, so divide by 10.
                "us10y": {
                    "yield": round(get_ticker_data("^TNX")["price"] / 10, 2), 
                    "change_bps": round(get_ticker_data("^TNX")["change_pct"] * 10, 1) # Approximate bps change.
                }
            },
            "market_status": "open", # Replace with a real session-status check if needed.
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return JSONResponse(payload)
    except Exception as e:
        raise HTTPException(500, str(e))
