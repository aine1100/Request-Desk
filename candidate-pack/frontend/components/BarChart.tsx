"use client";

export function BarChart({
  items,
}: {
  items: { label: string; value: number; color?: string }[];
}) {
  const max = Math.max(1, ...items.map((item) => item.value));
  if (items.length === 0) return <p className="muted">Nothing in this range.</p>;

  return (
    <div className="bars">
      {items.map((item) => (
        <div className="bar-row" key={item.label}>
          <span className="bar-label" title={item.label}>{item.label}</span>
          <div className="bar-track" role="img" aria-label={`${item.label}: ${item.value}`}>
            <div
              className="bar-fill"
              style={{
                width: item.value === 0 ? "0%" : `${(item.value / max) * 100}%`,
                background: item.color || "#005bd3",
              }}
            />
          </div>
          <strong className="bar-value">{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

export function ColumnChart({ items }: { items: { label: string; value: number }[] }) {
  const max = Math.max(1, ...items.map((item) => item.value));
  if (items.length === 0) return <p className="muted">Nothing in this range.</p>;

  return (
    <div className="columns-scroll">
      <div className="columns">
        {items.map((item) => (
          <div className="column" key={item.label}>
            <span className="column-value">{item.value}</span>
            <div className="column-track" role="img" aria-label={`${item.label}: ${item.value}`}>
              <div
                className="column-fill"
                style={{ height: item.value === 0 ? "0%" : `${(item.value / max) * 100}%` }}
              />
            </div>
            <span className="column-label" title={item.label}>{item.label.slice(5)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
