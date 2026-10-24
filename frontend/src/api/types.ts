export type UserRole = "admin" | "user";

export interface User {
  id: string;
  username: string;
  display_name: string;
  email: string | null;
  role: UserRole;
  created_at: string;
}

export interface AuthResponse {
  ok: boolean;
  user: User;
}

export interface MeResponse {
  authenticated: boolean;
  user: User | null;
}

export type Stack = "static" | "react" | "next";

export type TaskStatus =
  | "queued"
  | "running"
  | "deploying"
  | "done"
  | "error"
  | "interrupted";

export interface Task {
  id: string;
  prompt: string;
  capability: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  result: Record<string, unknown> | null;
  error: string | null;
  source: string;
  title: string;
  revision: number;
  stack: Stack;
  url: string;
  shared: boolean;
  share_url: string | null;
  event_count: number;
}

export interface ProjectListResponse {
  items: Task[];
}

export interface ProjectDetailResponse {
  task: Task;
  events: TaskEvent[];
}

export interface TaskEvent {
  seq: number;
  type: string;
  ts: string;
}

export interface Capability {
  key: string;
  label: string;
  short: string;
  description: string;
  example: string;
  prompt: string;
}

export interface SandboxStatus {
  backend: string;
  image: string | null;
}

export interface CapabilitiesResponse {
  items: Capability[];
  sandbox: SandboxStatus;
  ssr_preview: boolean;
  ssr_port: number | null;
}

export interface CreateProjectRequest {
  prompt: string;
  capability: string | null;
}

export interface CreateProjectResponse {
  task: Task;
  events: TaskEvent[];
}
