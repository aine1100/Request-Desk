"use client";

import { useRef, useState } from "react";
import { notifyError } from "../lib/toast";

export function FileUpload({
  file,
  onChange,
}: {
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  function take(list: FileList | null) {
    const next = list?.[0];
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".csv")) {
      notifyError("Choose a CSV file.");
      return;
    }
    onChange(next);
  }

  return (
    <div
      className={`dropzone${over ? " over" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        take(event.dataTransfer.files);
      }}
    >
      <input
        ref={input}
        type="file"
        accept=".csv,text/csv"
        hidden
        onChange={(event) => take(event.target.files)}
      />
      {file ? (
        <div className="file-chip">
          <div>
            <strong>{file.name}</strong>
            <span className="muted">{formatSize(file.size)}</span>
          </div>
          <button type="button" className="btn secondary" onClick={() => onChange(null)}>
            Remove
          </button>
        </div>
      ) : (
        <>
          <strong>Drop a CSV here</strong>
          <span className="muted">or choose the episode export from your computer</span>
          <button type="button" className="btn secondary" onClick={() => input.current?.click()}>
            Choose file
          </button>
        </>
      )}
    </div>
  );
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
