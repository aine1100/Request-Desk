"use client";

import { FormEvent, useState } from "react";
import { FileUpload } from "../../components/FileUpload";
import { api } from "../../lib/api";
import { notify, notifyError, notifyErrorFrom, notifySuccess } from "../../lib/toast";
import type { ImportReport } from "../../lib/types";

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      notifyError("Choose a CSV file.");
      return;
    }
    setPending(true);
    try {
      const body = new FormData();
      body.set("file", file);
      const result = await api<ImportReport>("/api/episodes/import/", { method: "POST", body });
      setReport(result);
      const problems = result.rejected + result.conflicts;
      const summary = `Imported ${result.imported}, unchanged ${result.unchanged}, rejected ${result.rejected}, conflicts ${result.conflicts}.`;
      if (problems > 0) notify(summary);
      else notifySuccess(summary);
    } catch (err) {
      notifyErrorFrom(err, "Import failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack">
      <div>
        <h1>Import episodes</h1>
        <p className="lede">
          Upload the recording-system CSV. Each row is metadata for a clip that already exists.
          Running the same file again does not create duplicates.
        </p>
      </div>
      <form className="card stack" onSubmit={onSubmit}>
        <FileUpload file={file} onChange={setFile} />
        <button className="btn" disabled={pending || !file} type="submit">
          {pending ? "Importing…" : "Import"}
        </button>
      </form>
      {report && (
        <section className="card stack">
          <div className="meta">
            <div><span>Imported</span><strong>{report.imported}</strong></div>
            <div><span>Unchanged</span><strong>{report.unchanged}</strong></div>
            <div><span>Conflicts</span><strong>{report.conflicts}</strong></div>
            <div><span>Rejected</span><strong>{report.rejected}</strong></div>
          </div>
          {report.issues.length > 0 && (
            <table>
              <thead>
                <tr><th>Row</th><th>Episode</th><th>Outcome</th><th>Reason</th></tr>
              </thead>
              <tbody>
                {report.issues.map((issue) => (
                  <tr key={`${issue.row}-${issue.outcome}-${issue.reason}`}>
                    <td>{issue.row}</td>
                    <td>{issue.episode_id || "—"}</td>
                    <td>{issue.outcome}</td>
                    <td>{issue.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {report.issues_truncated && <p className="muted">Showing the first 100 issues.</p>}
        </section>
      )}
    </div>
  );
}
