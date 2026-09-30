"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { STATUS_LABEL, api, formatDay, loadUser } from "../../lib/api";
import { notifyErrorFrom } from "../../lib/toast";
import type { DatasetRequest, Page, User } from "../../lib/types";

export default function RequestsPage() {
  const router = useRouter();
  const [rows, setRows] = useState<DatasetRequest[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  useEffect(() => {
    setUser(loadUser());
    api<Page<DatasetRequest>>(`/api/requests/?page=${page}`)
      .then((result) => {
        setRows(result.results);
        setHasNext(Boolean(result.next));
      })
      .catch((err) => notifyErrorFrom(err, "Could not load requests."));
  }, [page]);

  return (
    <div className="stack">
      <div className="row">
        <div>
          <h1>{user?.role === "client" ? "Your requests" : "All requests"}</h1>
          <p className="lede">Each request is an order for a number of episode records.</p>
        </div>
        {user?.role === "client" && (
          <button className="btn" onClick={() => router.push("/requests/new")}>
            New request
          </button>
        )}
      </div>
      <div className="card table-card">
        {rows.length === 0 ? (
          <p className="muted">No requests yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Task</th>
                {user?.role !== "client" && <th>Client</th>}
                <th>Progress</th>
                <th>Deadline</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td><Link href={`/requests/${row.id}`}>{row.task_name}</Link></td>
                  {user?.role !== "client" && <td>{row.client_name}</td>}
                  <td>{row.assigned_count} / {row.episodes_requested}</td>
                  <td>{formatDay(row.deadline)}</td>
                  <td><span className={`pill ${row.status}`}>{STATUS_LABEL[row.status]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="pager">
          <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
            Previous
          </button>
          <span className="muted">Page {page}</span>
          <button className="btn secondary" disabled={!hasNext} onClick={() => setPage((current) => current + 1)}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
