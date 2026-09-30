"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../../lib/api";
import { notifyErrorFrom, notifySuccess } from "../../../lib/toast";

export default function NewRequestPage() {
  const router = useRouter();
  const [taskName, setTaskName] = useState("pick cup");
  const [count, setCount] = useState(5);
  const [deadline, setDeadline] = useState("2026-10-31");
  const [notes, setNotes] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const created = await api<{ id: number; task_name: string }>("/api/requests/", {
        method: "POST",
        body: JSON.stringify({
          task_name: taskName,
          episodes_requested: Number(count),
          deadline,
          notes,
        }),
      });
      notifySuccess(`Request submitted for ${created.task_name}`);
      router.push(`/requests/${created.id}`);
    } catch (err) {
      notifyErrorFrom(err, "Could not create the request.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="card stack" onSubmit={onSubmit}>
      <div>
        <h1>New request</h1>
        <p className="lede">Ask for a number of episodes of one task, due by a date.</p>
      </div>
      <label>
        Task name
        <input value={taskName} onChange={(event) => setTaskName(event.target.value)} required />
      </label>
      <div className="grid">
        <label>
          Episodes requested
          <input
            type="number"
            min={1}
            value={count}
            onChange={(event) => setCount(Number(event.target.value))}
            required
          />
        </label>
        <label>
          Deadline
          <input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} required />
        </label>
      </div>
      <label>
        Notes
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
      </label>
      <button className="btn" disabled={pending} type="submit">
        {pending ? "Submitting…" : "Submit request"}
      </button>
    </form>
  );
}
