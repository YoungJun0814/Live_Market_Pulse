interface HeadlinesTickerProps {
  items: string[];
}

export function HeadlinesTicker({ items }: HeadlinesTickerProps) {
  const line = items.join("   //   ");

  return (
    <section className="ticker">
      <div className="ticker__label">Zone 6 - 24hr Headlines Ticker</div>
      <div className="ticker__track">
        <span>{line}</span>
        <span aria-hidden="true">{line}</span>
      </div>
    </section>
  );
}
