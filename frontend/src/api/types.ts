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

export interface TaskCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface TaskBuild {
  files: number;
  bytes: number;
  duration_ms: number;
  sandbox_id?: string;
}

export interface RuntimeState {
  status: string;
  revision?: number | null;
  started_at?: string | null;
  last_active_at?: string | null;
  preview?: boolean;
  url?: string | null;
  error?: string | null;
}

export interface TaskResult {
  url?: string | null;
  title?: string;
  capability?: string;
  source?: string;
  elapsed_ms?: number;
  revision?: number;
  stack?: Stack;
  runtime?: RuntimeState | null;
  build?: TaskBuild;
  checks?: TaskCheck[];
  assets?: number;
  media?: Record<string, unknown>;
}

export interface Task {
  id: string;
  prompt: string;
  capability: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  result: TaskResult | null;
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
  message?: string;
  prompt?: string;
  capability?: string;
  label?: string;
  description?: string;
  mode_hint?: string;
  summary?: string;
  title?: string;
  detail?: string;
  index?: number;
  steps?: string[];
  name?: string;
  ok?: boolean;
  url?: string | null;
  revision?: number;
  source?: string;
  instruction?: string;
  checks?: TaskCheck[];
  line?: string;
  files?: number;
  bytes?: number;
  duration_ms?: number;
  path?: string;
  before?: string;
  after?: string;
  created?: boolean;
  reason?: string;
  language?: string;
  args?: Record<string, unknown>;
  status?: string;
  progress?: number;
  total?: number;
  elapsed?: number;
  image?: string;
  port?: number;
  mime?: string;
}

export interface RuntimeResponse {
  runtime: RuntimeState;
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
