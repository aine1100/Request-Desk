export type Role = "client" | "operator" | "admin";

export type User = {
  id: number;
  email: string;
  name: string;
  role: Role;
  organisation: string;
  is_active: boolean;
};

export type RequestStatus =
  | "submitted"
  | "in_progress"
  | "delivered"
  | "accepted"
  | "rejected";

export type Assignment = {
  episode_id: string;
  task_name: string;
  quality: string;
  robot_id: string;
  duration_seconds: number;
  assigned_at: string;
};

export type StatusEvent = {
  from_status: string;
  to_status: string;
  actor_email: string;
  actor_name: string;
  created_at: string;
};

export type DatasetRequest = {
  id: number;
  client_name: string;
  client_email: string;
  task_name: string;
  episodes_requested: number;
  assigned_count: number;
  deadline: string;
  notes: string;
  status: RequestStatus;
  created_at: string;
  updated_at: string;
  assignments?: Assignment[];
  events?: StatusEvent[];
};

export type Episode = {
  episode_id: string;
  robot_id: string;
  task_name: string;
  recorded_at: string;
  duration_seconds: number;
  operator_name: string;
  quality: string;
  assigned_request_id: number | null;
};

export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Analytics = {
  start: string;
  end: string;
  episodes_per_day_per_robot: { date: string; robot_id: string; count: number }[];
  requests_by_status: Record<RequestStatus, number>;
  median_seconds_submitted_to_delivered: number | null;
  top_tasks_by_good_episodes: { task_name: string; count: number }[];
};

export type ImportReport = {
  imported: number;
  unchanged: number;
  conflicts: number;
  rejected: number;
  rejection_reasons: Record<string, number>;
  issues: { row: number; episode_id: string; outcome: string; reason: string }[];
  issues_truncated: boolean;
};
