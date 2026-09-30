import type { User } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function loadUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("desk_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function saveSession(token: string, user: User) {
  localStorage.setItem("desk_token", token);
  localStorage.setItem("desk_user", JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem("desk_token");
  localStorage.removeItem("desk_user");
}

function formatError(data: unknown): string {
  if (!data || typeof data !== "object") return "Request failed.";
  const record = data as Record<string, unknown>;
  if (typeof record.detail === "string") return record.detail;
  return Object.entries(record)
    .map(([key, value]) => {
      const text = Array.isArray(value) ? value.join(" ") : String(value);
      return `${key}: ${text}`;
    })
    .join(" ");
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = typeof window === "undefined" ? null : localStorage.getItem("desk_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(options.body instanceof FormData)) {
    headers.set("Accept", "application/json");
    if (options.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text.slice(0, 300) };
    }
  }
  if (!response.ok) {
    throw new ApiError(formatError(data), response.status);
  }
  return data as T;
}

export function formatWhen(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Africa/Kigali",
  }).format(date);
}

export function formatDay(value: string) {
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;
  return `${day}/${month}/${year}`;
}

export const STATUS_LABEL: Record<string, string> = {
  submitted: "Submitted",
  in_progress: "In progress",
  delivered: "Delivered",
  accepted: "Accepted",
  rejected: "Rejected",
};
