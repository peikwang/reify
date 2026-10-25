export type CompanionStage =
  | "plan"
  | "write"
  | "build"
  | "deploy"
  | "error"
  | "done";

const STAGE_BY_EVENT: Record<string, CompanionStage> = {
  task_started: "plan",
  intent: "plan",
  plan: "plan",
  step_started: "plan",
  step_done: "plan",
  thinking: "plan",
  tool_call: "write",
  tool_result: "write",
  file_diff: "write",
  asset_created: "write",
  media_progress: "write",
  build_started: "build",
  build_log: "build",
  build_done: "build",
  runtime_built: "build",
  runtime_starting: "build",
  preview_ready: "deploy",
  deployed: "deploy",
  runtime_ready: "deploy",
  error: "error",
  build_failed: "error",
  runtime_error: "error",
  interrupted: "error",
  refine_failed: "error",
  done: "done",
};

export function companionStageForEvent(type: string): CompanionStage | null {
  return STAGE_BY_EVENT[type] ?? null;
}

export type CompanionAction =
  | { type: "reset" }
  | { type: "event"; eventType: string };

export function companionReducer(
  state: CompanionStage,
  action: CompanionAction,
): CompanionStage {
  if (action.type === "reset") return "plan";
  return companionStageForEvent(action.eventType) ?? state;
}

export const COMPANION_COPY: Record<
  CompanionStage,
  { label: string; say: string }
> = {
  plan: { label: "正在理解你的想法…", say: "plan · thinking" },
  write: { label: "叮叮当当写文件…", say: "write_file · diff" },
  build: { label: "把构建炉烧旺…", say: "npm ci · build" },
  deploy: { label: "部署完成，给你！", say: "deploy · /p/" },
  error: { label: "哎呀，重试一次…", say: "error · recoverable" },
  done: { label: "做好啦，随时可改", say: "done" },
};
