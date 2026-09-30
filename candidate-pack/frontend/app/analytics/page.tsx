"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";
import { BarChart, ColumnChart } from "../../components/BarChart";
import { STATUS_LABEL, api, loadUser } from "../../lib/api";
import { notifyErrorFrom } from "../../lib/toast";
import type { Analytics, RequestStatus } from "../../lib/types";

const PAGE_SIZE = 10;
const STATUSES: RequestStatus[] = ["submitted", "in_progress", "delivered", "accepted", "rejected"];
const STATUS_COLOR: Record<RequestStatus, string> = {
  submitted: "#e5b800",
  in_progress: "#2c6ecb",
  delivered: "#1a7f4b",
  accepted: "#0c5132",
  rejected: "#c5280c",
};

export default function AnalyticsPage() {
  const [start, setStart] = useState(() => daysAgo(90));
  const [end, setEnd] = useState(() => daysAgo(0));
  const [report, setReport] = useState<Analytics | null>(null);
  const [denied, setDenied] = useState(false);

  async function load(nextStart: string, nextEnd: string) {
    const query = new URLSearchParams({ start: nextStart, end: nextEnd });
    setReport(await api<Analytics>(`/api/analytics/?${query}`));
  }

  useEffect(() => {
    const current = loadUser();
    if (current?.role === "client") {
      setDenied(true);
      return;
    }
    const nextStart = daysAgo(90);
    const nextEnd = daysAgo(0);
    setStart(nextStart);
    setEnd(nextEnd);
    load(nextStart, nextEnd).catch((err) => notifyErrorFrom(err, "Could not load analytics."));
  }, []);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    load(start, end).catch((err) => notifyErrorFrom(err, "Could not load analytics."));
  }

  if (denied) {
    return <p className="muted">Analytics is available to operators and admins.</p>;
  }

  return (
    <div className="stack">
      <div>
        <h1>Analytics</h1>
        <p className="lede">
          Episode counts use the recording date. Request counts use the day the request was submitted.
        </p>
      </div>
      <form className="card filters" onSubmit={onSubmit}>
        <label>
          Start
          <input type="date" value={start} onChange={(event) => setStart(event.target.value)} required />
        </label>
        <label>
          End
          <input type="date" value={end} onChange={(event) => setEnd(event.target.value)} required />
        </label>
        <button className="btn" type="submit">Apply</button>
      </form>
      {report && (
        <>
          <section className="meta">
            <div>
              <span>Median submitted to delivered</span>
              <strong>{formatMedian(report.median_seconds_submitted_to_delivered)}</strong>
            </div>
          </section>
          <div className="chart-grid">
            <section className="card stack">
              <h2>Requests by status</h2>
              <BarChart
                items={STATUSES.map((status) => ({
                  label: STATUS_LABEL[status],
                  value: report.requests_by_status[status] ?? 0,
                  color: STATUS_COLOR[status],
                }))}
              />
            </section>
            <section className="card stack">
              <h2>Episodes by robot</h2>
              <BarChart items={sumBy(report.episodes_per_day_per_robot, (row) => row.robot_id, "value")} />
            </section>
          </div>
          <section className="card stack">
            <h2>Episodes recorded per day</h2>
            <ColumnChart items={sumBy(report.episodes_per_day_per_robot, (row) => row.date, "label")} />
          </section>
          <section className="stack">
            <h2>Top tasks by good episodes</h2>
            <PagedTable
              resetKey={`${report.start}:${report.end}:tasks`}
              rows={report.top_tasks_by_good_episodes}
              empty="No good episodes in this range."
              head={<tr><th>Task</th><th>Good episodes</th></tr>}
              renderRow={(row) => (
                <tr key={row.task_name}>
                  <td>{row.task_name}</td>
                  <td>{row.count}</td>
                </tr>
              )}
            />
          </section>
          <section className="stack">
            <h2>Episodes per day, per robot</h2>
            <PagedTable
              resetKey={`${report.start}:${report.end}:episodes`}
              rows={report.episodes_per_day_per_robot}
              empty="No episodes recorded in this range."
              head={<tr><th>Date</th><th>Robot</th><th>Episodes</th></tr>}
              renderRow={(row) => (
                <tr key={`${row.date}-${row.robot_id}`}>
                  <td>{row.date}</td>
                  <td>{row.robot_id}</td>
                  <td>{row.count}</td>
                </tr>
              )}
            />
          </section>
        </>
      )}
    </div>
  );
}

function PagedTable<T>({
  rows,
  resetKey,
  empty,
  head,
  renderRow,
}: {
  rows: T[];
  resetKey: string;
  empty: string;
  head: ReactNode;
  renderRow: (row: T) => ReactNode;
}) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [resetKey]);

  if (rows.length === 0) return <p className="muted">{empty}</p>;

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  const start = (current - 1) * PAGE_SIZE;
  const slice = rows.slice(start, start + PAGE_SIZE);

  return (
    <div className="card table-card">
      <table>
        <thead>{head}</thead>
        <tbody>{slice.map(renderRow)}</tbody>
      </table>
      <div className="pager">
        <button className="btn secondary" type="button" disabled={current <= 1} onClick={() => setPage(current - 1)}>
          Previous
        </button>
        <span className="muted">
          {start + 1}–{start + slice.length} of {rows.length}
        </span>
        <button className="btn secondary" type="button" disabled={current >= pages} onClick={() => setPage(current + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}

function sumBy<T extends { count: number }>(rows: T[], key: (row: T) => string, order: "value" | "label") {
  const totals = new Map<string, number>();
  for (const row of rows) {
    const name = key(row);
    totals.set(name, (totals.get(name) ?? 0) + row.count);
  }
  const entries = [...totals.entries()];
  entries.sort((left, right) =>
    order === "label" ? left[0].localeCompare(right[0]) : right[1] - left[1] || left[0].localeCompare(right[0]),
  );
  return entries.map(([label, value]) => ({ label, value }));
}

function daysAgo(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function formatMedian(seconds: number | null) {
  if (seconds === null) return "No deliveries";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return rest === 0 ? `${minutes}m` : `${minutes}m ${rest}s`;
}
