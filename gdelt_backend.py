"""
GDELT Global Events Backend
============================
Fetches GDELT 2.0 events every 15 minutes.
Filters for war / economic-impact events.
Serves aggregated country heatmap + event feed via Flask.

Install: pip install flask flask-cors requests
Run:     python gdelt_backend.py
"""

import io, csv, zipfile, threading, time, logging
from datetime import datetime, timezone
import requests
from flask import Flask, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger(__name__)

app  = Flask(__name__)
CORS(app)

REFRESH_SECONDS = 900   # 15 minutes
MAX_FEED_EVENTS = 150   # how many events to keep in the live feed

# ── FIPS-10-4  →  ISO-3166-1 alpha-2 ──────────────────────────────────────
# GDELT ActionGeo_CountryCode uses FIPS; GeoJSON uses ISO_A2
FIPS_TO_ISO2 = {
    "AF":"AF","AL":"AL","AG":"DZ","AQ":"AS","AR":"AR","BA":"BH","BF":"BB",
    "BC":"BW","BE":"BE","BG":"BG","BH":"BZ","BL":"BO","BM":"BM","BN":"BJ",
    "BO":"BO","BP":"SB","BR":"BR","BT":"BT","BU":"BG","BX":"BN","BY":"BY",
    "CA":"CA","CB":"KH","CD":"TD","CF":"CG","CG":"CD","CH":"CN","CI":"CL",
    "CJ":"KY","CK":"CC","CM":"CM","CN":"CN","CO":"CO","CQ":"MP","CR":"CR",
    "CS":"CS","CT":"CF","CU":"CU","CV":"CV","CW":"CK","CY":"CY","DA":"DK",
    "DJ":"DJ","DO":"DM","DR":"DO","EC":"EC","EG":"EG","EI":"IE","EK":"GQ",
    "EN":"EE","ER":"ER","ES":"SV","ET":"ET","EZ":"CZ","FG":"GF","FI":"FI",
    "FJ":"FJ","FK":"FK","FM":"FM","FO":"FO","FP":"PF","FR":"FR","FS":"TF",
    "GA":"GM","GB":"GA","GG":"GE","GH":"GH","GI":"GI","GJ":"GD","GM":"DE",
    "GO":"GH","GP":"GP","GQ":"GU","GR":"GR","GT":"GT","GV":"GN","GY":"GY",
    "HA":"HT","HK":"HK","HO":"HN","HU":"HU","IC":"IS","ID":"ID","IM":"IM",
    "IN":"IN","IO":"IO","IR":"IR","IS":"IL","IT":"IT","IV":"CI","IZ":"IQ",
    "JA":"JP","JE":"JE","JM":"JM","JN":"SJ","JO":"JO","JQ":"JQ","JU":"JU",
    "KE":"KE","KG":"KG","KN":"KP","KQ":"KQ","KR":"KR","KS":"KR","KT":"TW",
    "KU":"KW","KV":"XK","KZ":"KZ","LA":"LA","LE":"LB","LG":"LV","LH":"LT",
    "LI":"LY","LO":"SK","LQ":"PR","LS":"LS","LT":"LT","LU":"LU","LY":"LY",
    "MA":"MG","MB":"MO","MC":"MO","MD":"MD","MF":"MF","MG":"MG","MI":"MW",
    "MK":"MK","ML":"ML","MO":"MA","MP":"MP","MQ":"MQ","MR":"MR","MT":"MT",
    "MU":"OM","MV":"MV","MX":"MX","MY":"MY","MZ":"MZ","NA":"NA","NC":"NC",
    "NE":"NE","NF":"NF","NG":"NG","NH":"VU","NI":"NI","NL":"NL","NM":"NU",
    "NO":"NO","NP":"NP","NR":"NR","NS":"SR","NU":"NI","NZ":"NZ","OC":"TL",
    "PA":"PA","PE":"PE","PF":"PF","PG":"PG","PH":"PH","PK":"PK","PL":"PL",
    "PM":"PM","PO":"PT","PP":"PG","PS":"PS","PU":"GW","QA":"QA","RE":"RE",
    "RI":"RS","RM":"MH","RO":"RO","RP":"PH","RQ":"PR","RS":"RU","RU":"RU",
    "RW":"RW","SA":"SA","SB":"SB","SC":"KN","SE":"SC","SF":"ZA","SG":"SG",
    "SH":"SH","SI":"SI","SL":"SL","SM":"SM","SN":"SN","SO":"SO","SP":"ES",
    "SR":"SR","ST":"LC","SU":"SD","SV":"SV","SW":"SE","SX":"GN","SY":"SY",
    "SZ":"SZ","TC":"TC","TD":"TD","TH":"TH","TI":"TJ","TK":"TK","TN":"TN",
    "TO":"TO","TP":"TP","TS":"TN","TT":"TT","TU":"TR","TV":"TV","TW":"TW",
    "TX":"TX","TZ":"TZ","UA":"UA","UG":"UG","UK":"GB","UP":"UA","US":"US",
    "UV":"BF","UY":"UY","UZ":"UZ","VC":"VC","VE":"VE","VI":"VI","VM":"VN",
    "VQ":"VQ","WA":"NA","WF":"WF","WI":"WI","WQ":"WQ","WS":"WS","WZ":"SZ",
    "YM":"YE","ZA":"ZM","ZI":"ZW","ZM":"ZM","ZW":"ZW",
}

# ── CAMEO root code → human-readable label ─────────────────────────────────
CAMEO_ROOT = {
    "01":"Public Statement",  "02":"Appeal",            "03":"Cooperation Intent",
    "04":"Consult",           "05":"Diplomatic Coop.",  "06":"Material Coop.",
    "07":"Aid Provided",      "08":"Yield",             "09":"Investigate",
    "10":"Demand",            "11":"Disapprove",        "12":"Reject",
    "13":"Threaten",          "14":"Protest",           "15":"Force Posture",
    "16":"Reduce Relations",  "17":"Coerce",            "18":"Assault",
    "19":"Armed Conflict",    "20":"Mass Violence",
}

# ── CAMEO sub-codes that carry strong economic / financial weight ──────────
ECONOMIC_CODES = {
    "0231","0232","0233","0234",   # economic sanctions / aid
    "0611","0612","0613","0614",   # material economic cooperation
    "1631","1632","1633","1634",   # reduce economic relations / sanctions
    "1721","1722","1723","1724",   # economic coercion / embargo
}

# ── Column indices for GDELT 2.0 Events CSV ───────────────────────────────
COL = {
    "DATE":       1,   "ACTOR1":     6,   "ACTOR2":    16,
    "EVENTCODE":  26,  "ROOTCODE":   28,  "QUADCLASS": 29,
    "GOLDSTEIN":  30,  "MENTIONS":   31,  "AVGTONE":   34,
    "GEO_FULL":   52,  "GEO_FIPS":   53,  "GEO_LAT":   56,
    "GEO_LON":    57,  "DATEADDED":  59,  "URL":        60,
}

# ── Shared state ──────────────────────────────────────────────────────────
_state = {
    "countries": {},      # ISO2 → {count, weight, events:[...]}
    "feed":      [],      # list of event dicts, newest first
    "updated_at": None,
    "source_url": None,
    "error": None,
}
_lock = threading.Lock()


def is_relevant(row) -> bool:
    """Return True if this event is war- or economy-related."""
    try:
        quad      = int(row[COL["QUADCLASS"]] or 0)
        root      = (row[COL["ROOTCODE"]] or "").strip()
        code      = (row[COL["EVENTCODE"]] or "").strip()
        goldstein = float(row[COL["GOLDSTEIN"]] or 0)

        # Material conflict / verbal conflict
        if quad in (3, 4):
            return True
        # Conflict root codes (protest → mass violence)
        if root in {"13","14","15","16","17","18","19","20"}:
            return True
        # Economic CAMEO sub-codes
        if code in ECONOMIC_CODES:
            return True
        # Very negative Goldstein score
        if goldstein <= -5:
            return True
    except (ValueError, IndexError):
        pass
    return False


def severity(row) -> int:
    """0–10 severity for colour weighting."""
    try:
        quad      = int(row[COL["QUADCLASS"]] or 0)
        goldstein = float(row[COL["GOLDSTEIN"]] or 0)
        root      = (row[COL["ROOTCODE"]] or "").strip()
        mentions  = int(row[COL["MENTIONS"]] or 1)

        base = 0
        if quad == 4: base = 6
        elif quad == 3: base = 3
        if root in {"18","19","20"}: base = max(base, 8)
        if goldstein <= -8: base = max(base, 9)
        elif goldstein <= -5: base = max(base, 6)
        base += min(3, mentions // 5)
        return min(10, base)
    except (ValueError, IndexError):
        return 1


def make_label(row) -> str:
    """Build a readable one-line event description."""
    a1   = (row[COL["ACTOR1"]] or "").strip() or "Unknown actor"
    a2   = (row[COL["ACTOR2"]] or "").strip()
    root = (row[COL["ROOTCODE"]] or "").strip()
    geo  = (row[COL["GEO_FULL"]] or "").strip()
    verb = CAMEO_ROOT.get(root, "Event")

    label = f"{a1.title()} — {verb}"
    if a2:
        label += f" vs {a2.title()}"
    if geo:
        label += f"  [{geo}]"
    return label[:140]


def fetch_gdelt() -> bool:
    """Download latest GDELT batch, parse, update _state. Returns True on success."""
    try:
        log.info("Fetching GDELT lastupdate.txt …")
        r = requests.get("http://data.gdeltproject.org/gdeltv2/lastupdate.txt", timeout=15)
        r.raise_for_status()
        lines = [l.strip() for l in r.text.strip().splitlines() if l.strip()]

        # Line 0 = Events, Line 1 = Mentions, Line 2 = GKG
        event_line = lines[0] if lines else ""
        parts = event_line.split()
        if len(parts) < 3:
            raise ValueError(f"Unexpected lastupdate format: {event_line!r}")

        zip_url = parts[2]
        log.info(f"Downloading events ZIP: {zip_url}")
        r2 = requests.get(zip_url, timeout=60)
        r2.raise_for_status()

        countries: dict = {}
        feed_events: list = []

        with zipfile.ZipFile(io.BytesIO(r2.content)) as zf:
            fname = zf.namelist()[0]
            with zf.open(fname) as f:
                reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"),
                                    delimiter="\t")
                for row in reader:
                    if len(row) < 61:
                        continue
                    if not is_relevant(row):
                        continue

                    fips = (row[COL["GEO_FIPS"]] or "").strip().upper()
                    iso2 = FIPS_TO_ISO2.get(fips, fips)
                    if not iso2:
                        continue

                    sev = severity(row)

                    if iso2 not in countries:
                        countries[iso2] = {"count": 0, "weight": 0, "events": []}
                    countries[iso2]["count"]  += 1
                    countries[iso2]["weight"] += sev

                    # Build feed item
                    try:
                        lat = float(row[COL["GEO_LAT"]] or 0)
                        lon = float(row[COL["GEO_LON"]] or 0)
                    except ValueError:
                        lat, lon = 0.0, 0.0

                    ts_raw = (row[COL["DATEADDED"]] or row[COL["DATE"]] or "").strip()
                    ts = ts_raw[:12] if len(ts_raw) >= 12 else ts_raw

                    event = {
                        "id":       row[0],
                        "ts":       ts,
                        "label":    make_label(row),
                        "country":  iso2,
                        "geo":      (row[COL["GEO_FULL"]] or "").strip(),
                        "severity": sev,
                        "root":     (row[COL["ROOTCODE"]] or "").strip(),
                        "tone":     round(float(row[COL["AVGTONE"]] or 0), 2),
                        "mentions": int(row[COL["MENTIONS"]] or 1),
                        "lat":      lat,
                        "lon":      lon,
                        "url":      (row[COL["URL"]] or "").strip(),
                    }
                    feed_events.append(event)

        # Sort feed newest-first, cap at MAX_FEED_EVENTS
        feed_events.sort(key=lambda e: e["ts"], reverse=True)
        feed_events = feed_events[:MAX_FEED_EVENTS]

        with _lock:
            _state["countries"]  = countries
            _state["feed"]       = feed_events
            _state["updated_at"] = datetime.now(timezone.utc).isoformat()
            _state["source_url"] = zip_url
            _state["error"]      = None

        log.info(f"GDELT OK — {sum(c['count'] for c in countries.values())} events, "
                 f"{len(countries)} countries, {len(feed_events)} feed items")
        return True

    except Exception as e:
        log.error(f"GDELT fetch failed: {e}")
        with _lock:
            _state["error"] = str(e)
        return False


def load_mock():
    """Fallback mock data so the frontend always has something to show."""
    log.info("Loading mock data …")
    countries = {
        "UA":{"count":45,"weight":90,"events":[]},
        "RU":{"count":38,"weight":76,"events":[]},
        "IL":{"count":32,"weight":70,"events":[]},
        "PS":{"count":30,"weight":68,"events":[]},
        "SY":{"count":18,"weight":44,"events":[]},
        "YE":{"count":16,"weight":38,"events":[]},
        "SD":{"count":14,"weight":32,"events":[]},
        "IR":{"count":20,"weight":48,"events":[]},
        "CN":{"count":22,"weight":40,"events":[]},
        "US":{"count":18,"weight":30,"events":[]},
        "KP":{"count":10,"weight":24,"events":[]},
        "MM":{"count":12,"weight":28,"events":[]},
        "ET":{"count":8,"weight":20,"events":[]},
        "ML":{"count":6,"weight":14,"events":[]},
        "AF":{"count":15,"weight":36,"events":[]},
        "SA":{"count":10,"weight":22,"events":[]},
        "PK":{"count":9, "weight":18,"events":[]},
        "IQ":{"count":11,"weight":26,"events":[]},
        "LB":{"count":14,"weight":32,"events":[]},
        "TR":{"count":8, "weight":16,"events":[]},
        "VE":{"count":5, "weight":10,"events":[]},
        "IN":{"count":7, "weight":12,"events":[]},
    }
    feed = [
        {"id":"M001","ts":"202503241430","label":"Russia Armed Conflict vs Ukraine [Kyiv, Ukraine]",           "country":"UA","geo":"Kyiv, Ukraine",       "severity":9,"root":"19","tone":-8.4,"mentions":320,"lat":50.45,"lon":30.52,"url":""},
        {"id":"M002","ts":"202503241415","label":"Israel Assault vs Hamas [Gaza Strip, Palestinian Territory]","country":"PS","geo":"Gaza Strip",          "severity":9,"root":"18","tone":-9.1,"mentions":280,"lat":31.35,"lon":34.31,"url":""},
        {"id":"M003","ts":"202503241400","label":"Houthi Forces — Force Posture [Red Sea, Yemen]",            "country":"YE","geo":"Red Sea",             "severity":8,"root":"15","tone":-6.5,"mentions":145,"lat":15.55,"lon":42.55,"url":""},
        {"id":"M004","ts":"202503241345","label":"China — Reduce Relations vs Taiwan [Taiwan Strait]",        "country":"CN","geo":"Taiwan Strait",       "severity":7,"root":"16","tone":-5.2,"mentions":210,"lat":24.50,"lon":121.00,"url":""},
        {"id":"M005","ts":"202503241330","label":"Iran — Threaten vs United States [Tehran, Iran]",           "country":"IR","geo":"Tehran, Iran",        "severity":7,"root":"13","tone":-7.1,"mentions":180,"lat":35.69,"lon":51.39,"url":""},
        {"id":"M006","ts":"202503241315","label":"North Korea — Force Posture [Pyongyang, North Korea]",      "country":"KP","geo":"Pyongyang",           "severity":8,"root":"15","tone":-6.8,"mentions":120,"lat":39.02,"lon":125.73,"url":""},
        {"id":"M007","ts":"202503241300","label":"Sudan Armed Forces — Mass Violence [Khartoum, Sudan]",      "country":"SD","geo":"Khartoum",            "severity":9,"root":"20","tone":-9.5,"mentions":95, "lat":15.55,"lon":32.53,"url":""},
        {"id":"M008","ts":"202503241245","label":"Myanmar Military — Assault vs Civilians [Yangon, Myanmar]", "country":"MM","geo":"Yangon, Myanmar",     "severity":8,"root":"18","tone":-8.2,"mentions":88, "lat":16.87,"lon":96.19,"url":""},
        {"id":"M009","ts":"202503241230","label":"US — Economic Coercion vs China [Washington DC, USA]",      "country":"US","geo":"Washington DC",       "severity":6,"root":"17","tone":-4.3,"mentions":240,"lat":38.90,"lon":-77.03,"url":""},
        {"id":"M010","ts":"202503241215","label":"Pakistan — Armed Conflict vs India [Line of Control]",      "country":"PK","geo":"Line of Control",     "severity":7,"root":"19","tone":-7.4,"mentions":130,"lat":34.00,"lon":74.00,"url":""},
        {"id":"M011","ts":"202503241200","label":"Saudi Arabia — Reduce Relations vs Iran [Riyadh, Saudi Arabia]","country":"SA","geo":"Riyadh",         "severity":6,"root":"16","tone":-5.6,"mentions":105,"lat":24.68,"lon":46.72,"url":""},
        {"id":"M012","ts":"202503241145","label":"Ethiopia — Armed Conflict [Tigray, Ethiopia]",              "country":"ET","geo":"Tigray",              "severity":8,"root":"19","tone":-8.0,"mentions":78, "lat":14.02,"lon":38.32,"url":""},
        {"id":"M013","ts":"202503241130","label":"Venezuela — Protest [Caracas, Venezuela]",                  "country":"VE","geo":"Caracas",             "severity":5,"root":"14","tone":-4.1,"mentions":60, "lat":10.49,"lon":-66.88,"url":""},
        {"id":"M014","ts":"202503241115","label":"Lebanon — Armed Conflict [Beirut, Lebanon]",                "country":"LB","geo":"Beirut, Lebanon",     "severity":8,"root":"19","tone":-7.8,"mentions":115,"lat":33.87,"lon":35.50,"url":""},
        {"id":"M015","ts":"202503241100","label":"Mali — Armed Conflict vs Insurgents [Bamako, Mali]",        "country":"ML","geo":"Bamako",              "severity":7,"root":"19","tone":-7.2,"mentions":55, "lat":12.65,"lon":-8.00,"url":""},
    ]
    with _lock:
        _state["countries"]  = countries
        _state["feed"]       = feed
        _state["updated_at"] = datetime.now(timezone.utc).isoformat()
        _state["source_url"] = "mock"
        _state["error"]      = "Using demo data — GDELT fetch not yet run"


def updater_loop():
    """Background thread: fetch GDELT every 15 min."""
    while True:
        fetch_gdelt()
        time.sleep(REFRESH_SECONDS)


# ── Flask routes ──────────────────────────────────────────────────────────

@app.route("/api/all")
def api_all():
    with _lock:
        return jsonify({
            "countries":  _state["countries"],
            "feed":       _state["feed"],
            "updated_at": _state["updated_at"],
            "source_url": _state["source_url"],
            "mock":       _state["source_url"] == "mock",
            "error":      _state["error"],
        })

@app.route("/api/countries")
def api_countries():
    with _lock:
        return jsonify(_state["countries"])

@app.route("/api/feed")
def api_feed():
    with _lock:
        return jsonify(_state["feed"])

@app.route("/health")
def health():
    with _lock:
        return jsonify({"status":"ok","updated_at":_state["updated_at"]})


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  GDELT Global Events Backend")
    print("  http://localhost:5001")
    print("  Endpoints:")
    print("    GET /api/all        → countries + feed + meta")
    print("    GET /api/countries  → per-country event counts")
    print("    GET /api/feed       → latest events (newest first)")
    print("    GET /health         → server status")
    print("=" * 60)

    # Seed with mock data immediately so the UI has something
    load_mock()

    # First real GDELT fetch in background (non-blocking)
    t = threading.Thread(target=updater_loop, daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=5001, debug=False)
