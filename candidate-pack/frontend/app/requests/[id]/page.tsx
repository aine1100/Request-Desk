"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Dropdown } from "../../../components/Dropdown";
import { STATUS_LABEL, api, formatDay, formatWhen, loadUser } from "../../../lib/api";
import { notifyErrorFrom, notifySuccess } from "../../../lib/toast";
import type { DatasetRequest, Episode, Page, RequestStatus, Role } from "../../../lib/types";

const QUALITY_OPTIONS = [
  { value: "", label: "Any quality" },
  { value: "good", label: "Good" },
  { value: "usable", label: "Usable" },
  { value: "bad", label: "Bad" },
];

export default function RequestDetailPage() {
  const params = useParams<{ id: string }>();
  const [request, setRequest] = useState<DatasetRequest | null>(null);
  const [failed, setFailed] = useState(false);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [taskName, setTaskName] = useState("");
  const [quality, setQuality] = useState("");
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [role, setRole] = useState<Role | null>(null);

  const load = useCallback(async () => {
    const detail = await api<DatasetRequest>(`/api/requests/${params.id}/`);
    setRequest(detail);
    setTaskName((current) => current || detail.task_name);
    return detail;
  }, [params.id]);

  const loadEpisodes = useCallback(async (nextPage: number, task: string, selectedQuality: string) => {
    const query = new URLSearchParams({ available: "true", page: String(nextPage) });
    if (task.trim()) query.set("task_name", task.trim());
    if (selectedQuality) query.set("quality", selectedQuality);
    const result = await api<Page<Episode>>(`/api/episodes/?${query}`);
    setEpisodes(result.results);
    setHasNext(Boolean(result.next));
    setPage(nextPage);
  }, []);

  useEffect(() => {
    const current = loadUser();
    setRole(current?.role ?? null);
    load()
      .then((detail) => {
        if (current && current.role !== "client") {
          return loadEpisodes(1, detail.task_name, "");
        }
      })
      .catch((err) => {
        notifyErrorFrom(err, "Could not load this request.");
        setFailed(true);
      });
  }, [load, loadEpisodes]);

  async function run(action: () => Promise<void>, success?: string) {
    try {
      await action();
      if (success) notifySuccess(success);
    } catch (err) {
      notifyErrorFrom(err, "Action failed.");
    }
  }

  if (!request) {
    return (
      <div className="stack">
        <BackLink />
        {failed ? <p className="muted">This request could not be loaded.</p> : <p className="muted">Loading…</p>}
      </div>
    );
  }

  const actions = nextActions(role ?? undefined, request.status);
  const staff = role === "operator" || role === "admin";

  return (
    <div className="stack">
      <BackLink />
      <div className="row">
        <div>
          <h1>{request.task_name}</h1>
          <p className="lede">Request #{request.id} for {request.client_name}</p>
        </div>
        <span className={`pill ${request.status}`}>{STATUS_LABEL[request.status]}</span>
      </div>
      <section className="meta">
        <div><span>Assigned</span><strong>{request.assigned_count} / {request.episodes_requested}</strong></div>
        <div><span>Deadline</span><strong>{formatDay(request.deadline)}</strong></div>
        <div><span>Client</span><strong>{request.client_email}</strong></div>
        <div><span>Updated</span><strong>{formatWhen(request.updated_at)}</strong></div>
      </section>
      {request.notes && <section className="card">{request.notes}</section>}
      {actions.length > 0 && (
        <div className="row">
          {actions.map((action) => (
            <button
              key={action.to}
              className={action.to === "rejected" ? "btn danger" : "btn"}
              onClick={() =>
                run(async () => {
                  const updated = await api<DatasetRequest>(`/api/requests/${request.id}/transition/`, {
                    method: "POST",
                    body: JSON.stringify({ to_status: action.to }),
                  });
                  setRequest(updated);
                }, action.success)
              }
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
      <div className={staff && request.status === "in_progress" ? "split" : ""}>
        <section className="card stack">
          <h2>Assigned episodes</h2>
          {(request.assignments || []).length === 0 && <p className="muted">None yet.</p>}
          {(request.assignments || []).map((assignment) => (
            <div className="row" key={assignment.episode_id}>
              <div>
                <strong>{assignment.episode_id}</strong>
                <div className="muted">{assignment.robot_id} · {assignment.duration_seconds}s</div>
              </div>
              <span className={`pill ${assignment.quality}`}>{assignment.quality}</span>
              {staff && request.status === "in_progress" && (
                <button
                  className="btn secondary"
                  onClick={() =>
                    run(async () => {
                      const updated = await api<DatasetRequest>(
                        `/api/requests/${request.id}/assignments/${assignment.episode_id}/`,
                        { method: "DELETE" },
                      );
                      setRequest(updated);
                      await loadEpisodes(page, taskName, quality);
                    }, `${assignment.episode_id} removed`)
                  }
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </section>
        {staff && request.status === "in_progress" && (
          <section className="card stack">
            <h2>Available episodes</h2>
            <div className="filters">
              <label>
                Task
                <input value={taskName} onChange={(event) => setTaskName(event.target.value)} />
              </label>
              <div>
                <span className="field-label">Quality</span>
                <Dropdown label="Quality" value={quality} options={QUALITY_OPTIONS} onChange={setQuality} />
              </div>
              <button className="btn secondary" onClick={() => run(() => loadEpisodes(1, taskName, quality))}>
                Filter
              </button>
            </div>
            {episodes.length === 0 && <p className="muted">No matching episodes. Import a CSV first.</p>}
            {episodes.map((episode) => (
              <div className="row" key={episode.episode_id}>
                <div>
                  <strong>{episode.episode_id}</strong>
                  <div className="muted">{episode.task_name} · {episode.robot_id}</div>
                </div>
                <span className={`pill ${episode.quality}`}>{episode.quality}</span>
                <button
                  className="btn"
                  disabled={episode.quality === "bad"}
                  onClick={() =>
                    run(async () => {
                      const updated = await api<DatasetRequest>(`/api/requests/${request.id}/assignments/`, {
                        method: "POST",
                        body: JSON.stringify({ episode_id: episode.episode_id }),
                      });
                      setRequest(updated);
                      await loadEpisodes(page, taskName, quality);
                    }, `${episode.episode_id} assigned`)
                  }
                >
                  Assign
                </button>
              </div>
            ))}
            <div className="pager">
              <button className="btn secondary" disabled={page <= 1} onClick={() => run(() => loadEpisodes(page - 1, taskName, quality))}>
                Previous
              </button>
              <span className="muted">Page {page}</span>
              <button className="btn secondary" disabled={!hasNext} onClick={() => run(() => loadEpisodes(page + 1, taskName, quality))}>
                Next
              </button>
            </div>
          </section>
        )}
      </div>
      <section className="card">
        <h2>History</h2>
        <ul className="history">
          {(request.events || []).map((event, index) => (
            <li key={`${event.created_at}-${index}`}>
              <span>
                {event.from_status ? `${STATUS_LABEL[event.from_status] || event.from_status} → ` : ""}
                {STATUS_LABEL[event.to_status] || event.to_status}
                <span className="muted"> · {event.actor_name}</span>
              </span>
              <span className="muted">{formatWhen(event.created_at)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function BackLink() {
  return (
    <Link href="/requests" className="back">
      <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M12 5l-5 5 5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Requests
    </Link>
  );
}

function nextActions(role: string | undefined, status: RequestStatus) {
  if (role === "client" && status === "delivered") {
    return [
      { to: "accepted", label: "Accept delivery", success: "Delivery accepted" },
      { to: "rejected", label: "Reject delivery", success: "Delivery rejected" },
    ];
  }
  if (!role || role === "client") return [];
  if (status === "submitted") return [{ to: "in_progress", label: "Start work", success: "Work started" }];
  if (status === "in_progress") return [{ to: "delivered", label: "Mark delivered", success: "Request delivered" }];
  if (status === "rejected") return [{ to: "in_progress", label: "Resume work", success: "Work resumed" }];
  return [];
}
