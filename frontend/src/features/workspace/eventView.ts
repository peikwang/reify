import type { RuntimeState, Task, TaskEvent } from "../../api/types";

export type PlanStepStatus = "pending" | "active" | "done";
export type TimelineKind =
  | "thought"
  | "step"
  | "file"
  | "verify"
  | "error"
  | "done"
  | "deploy"
  | "tool";

export interface TimelineItem {
  key: string;
  kind: TimelineKind;
  title: string;
  summary: string;
  detail?: string;
  chip?: string;
  chipTone?: "ok" | "fail" | "tool";
  stepIndex?: number;
  ts: string;
}

export interface FileSnapshot {
  path: string;
  content: string;
  language: string;
  before: string;
  after: string;
  created: boolean;
  reason: string;
}

export type TerminalKind = "cmd" | "out" | "ok" | "err" | "muted";

export interface TerminalLine {
  kind: TerminalKind;
  text: string;
}

export interface ProjectViewState {
  plan: string[];
  planStatus: PlanStepStatus[];
  timeline: TimelineItem[];
  checks: Array<{ name: string; ok: boolean; detail: string }>;
  files: Record<string, FileSnapshot>;
  terminalLines: TerminalLine[];
  lastSeq: number;
  terminal: "done" | "error" | "interrupted" | null;
  previewReady: boolean;
  currentStep: number | null;
  outcome: { title: string; text: string } | null;
}

export const initialProjectView: ProjectViewState = {
  plan: [],
  planStatus: [],
  timeline: [],
  checks: [],
  files: {},
  terminalLines: [{ kind: "muted", text: "$ vibeforge agent --wait" }],
  lastSeq: 0,
  terminal: null,
  previewReady: false,
  currentStep: null,
  outcome: null,
};

function countLines(value: string): number {
  return value ? value.split("\n").length : 0;
}

function withTimeline(
  state: ProjectViewState,
  item: TimelineItem,
): ProjectViewState {
  return {
    ...state,
    timeline: [...state.timeline, item].slice(-80),
  };
}

function withTerminal(
  state: ProjectViewState,
  line: TerminalLine,
): ProjectViewState {
  return {
    ...state,
    terminalLines: [...state.terminalLines, line].slice(-160),
  };
}

function upsertChecks(
  checks: ProjectViewState["checks"],
  incoming: ProjectViewState["checks"],
): ProjectViewState["checks"] {
  const next = [...checks];
  for (const check of incoming) {
    const index = next.findIndex((item) => item.name === check.name);
    if (index >= 0) next[index] = check;
    else next.push(check);
  }
  return next;
}

function sourceLabel(source: string | undefined): string | undefined {
  if (source === "llm") return "LLM DIRECTOR";
  if (source === "media" || source === "media-edit") return "MEDIA RENDER";
  if (source === "director" || source === "refine-failed") return "LOCAL DIRECTOR";
  return undefined;
}

export function applyProjectEvent(
  state: ProjectViewState,
  event: TaskEvent,
): ProjectViewState {
  if (
    !event ||
    typeof event.seq !== "number" ||
    event.seq <= state.lastSeq
  ) {
    return state;
  }
  const base: ProjectViewState = { ...state, lastSeq: event.seq };

  switch (event.type) {
    case "task_started": {
      return withTimeline(
        withTerminal(base, { kind: "muted", text: "● task started" }),
        {
          key: `evt-${event.seq}`,
          kind: "thought",
          title: "TASK / STARTED",
          summary: event.prompt || "Agent 已接收任务",
          ts: event.ts,
        },
      );
    }
    case "intent": {
      return withTimeline(base, {
        key: `evt-${event.seq}`,
        kind: "thought",
        title: "INTENT",
        summary: [event.label, event.description].filter(Boolean).join(" · "),
        ts: event.ts,
      });
    }
    case "plan": {
      const steps = Array.isArray(event.steps) ? event.steps : [];
      return withTimeline(
        withTerminal(
          {
            ...base,
            plan: steps,
            planStatus: steps.map(() => "pending"),
          },
          { kind: "muted", text: "● plan ready · " + steps.length + " steps" },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "thought",
          title: "PLAN READY",
          summary: steps.map((step, index) => `0${index + 1} ${step}`).join(" · "),
          ts: event.ts,
        },
      );
    }
    case "step_started": {
      const index = typeof event.index === "number" ? event.index : -1;
      if (index < 0) return base;
      const planStatus = base.planStatus.map((status, i) =>
        i === index ? "active" : status,
      );
      return withTimeline(
        withTerminal(
          { ...base, planStatus, currentStep: index },
          { kind: "cmd", text: "▸ step 0" + (index + 1) + " · " + (event.title || "") },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "step",
          title: `STEP 0${index + 1}`,
          summary: event.title || "",
          stepIndex: index,
          ts: event.ts,
        },
      );
    }
    case "step_done": {
      const index = typeof event.index === "number" ? event.index : -1;
      if (index < 0) return base;
      const planStatus = base.planStatus.map((status, i) =>
        i === index ? "done" : status,
      );
      const withLog = withTerminal(base, {
        kind: "ok",
        text: "✓ step 0" + (index + 1) + " · " + (event.summary || "done"),
      });
      const timeline = withLog.timeline.map((item) =>
        item.kind === "step" && item.stepIndex === index
          ? { ...item, chip: event.summary || "DONE", chipTone: "ok" as const }
          : item,
      );
      return { ...withLog, planStatus, timeline };
    }
    case "thinking": {
      return withTimeline(base, {
        key: `evt-${event.seq}`,
        kind: "thought",
        title: "THINKING",
        summary: event.summary || event.message || "",
        detail: event.detail,
        chip: sourceLabel(event.source),
        chipTone: event.source ? "tool" : undefined,
        ts: event.ts,
      });
    }
    case "tool_call": {
      const args = JSON.stringify(event.args || {});
      return withTimeline(
        withTerminal(base, {
          kind: "cmd",
          text: "$ " + (event.name || "tool") + " " + args.slice(0, 180),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "tool",
          title: "TOOL / " + (event.name || "tool"),
          summary: event.summary || "",
          ts: event.ts,
        },
      );
    }
    case "tool_result": {
      return withTimeline(
        withTerminal(base, {
          kind: event.ok === false ? "err" : "ok",
          text:
            (event.ok === false ? "✗ " : "✓ ") +
            (event.summary || event.name || "done"),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "tool",
          title: "TOOL / " + (event.name || "result"),
          summary: event.summary || (event.ok === false ? "执行失败" : "执行完成"),
          chip: event.ok === false ? "FAIL" : "PASS",
          chipTone: event.ok === false ? "fail" : "ok",
          ts: event.ts,
        },
      );
    }
    case "file_diff": {
      const path = event.path || "index.html";
      const before = event.before || "";
      const after = event.after || "";
      const added = countLines(after) - countLines(before);
      const snapshot: FileSnapshot = {
        path,
        content: after,
        language: event.language || "text",
        before,
        after,
        created: Boolean(event.created),
        reason: event.reason || "",
      };
      return withTimeline(
        withTerminal(
          {
            ...base,
            files: { ...base.files, [path]: snapshot },
          },
          {
            kind: "ok",
            text:
              "✓ " +
              path +
              " · " +
              (event.created ? "created" : "updated") +
              " (" +
              countLines(after) +
              " lines)",
          },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "file",
          title: "FILE / " + path,
          summary:
            (event.created ? "创建 " : "更新 ") +
            path +
            " · " +
            (added >= 0 ? "+" + added : String(added)) +
            " 行",
          detail: event.reason || undefined,
          chip: event.language,
          chipTone: "tool",
          ts: event.ts,
        },
      );
    }
    case "preview_ready": {
      return withTimeline(
        withTerminal(
          {
            ...base,
            previewReady: true,
            outcome: {
              title: event.title || "页面已可预览",
              text: "代码已经写入，Agent 正在做最后的自检。",
            },
          },
          { kind: "muted", text: "● preview ready · " + (event.url || "") },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "deploy",
          title: "PREVIEW / READY",
          summary: event.url || "",
          ts: event.ts,
        },
      );
    }
    case "asset_created": {
      return withTimeline(
        withTerminal(base, {
          kind: "ok",
          text: "✓ asset " + (event.path || "") + " · " + (event.mime || ""),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "file",
          title: "ASSET / " + (event.path || ""),
          summary:
            (event.summary || "媒体素材已保存") +
            " · " +
            Math.round((event.bytes || 0) / 1024) +
            " KB",
          chip: event.mime,
          chipTone: "tool",
          ts: event.ts,
        },
      );
    }
    case "media_progress": {
      return withTimeline(
        withTerminal(base, {
          kind: "out",
          text: "◆ " + (event.message || "media progress"),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "thought",
          title: "MEDIA / " + (event.status || "PROGRESS"),
          summary: event.message || "",
          ts: event.ts,
        },
      );
    }
    case "build_started": {
      return withTimeline(
        withTerminal(base, {
          kind: "muted",
          text: "● sandbox build started · " + (event.image || "node"),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "step",
          title: "BUILD / SANDBOX",
          summary:
            (event.image || "node") + " · " + (event.files || 0) + " 个源码文件",
          ts: event.ts,
        },
      );
    }
    case "build_log": {
      return withTerminal(base, { kind: "muted", text: event.line || "" });
    }
    case "build_done": {
      return withTimeline(
        withTerminal(base, {
          kind: "ok",
          text:
            "✓ build complete · " +
            Math.round((event.bytes || 0) / 1024) +
            " KB",
        }),
        {
          key: `evt-${event.seq}`,
          kind: "verify",
          title: "BUILD / DONE",
          summary:
            (event.files || 0) +
            " 个产物 · " +
            Math.round((event.bytes || 0) / 1024) +
            " KB · " +
            (event.duration_ms || 0) +
            " ms",
          chip: "PASS",
          chipTone: "ok",
          ts: event.ts,
        },
      );
    }
    case "build_failed": {
      return withTimeline(
        withTerminal(base, {
          kind: "err",
          text: "✗ build failed · " + (event.message || ""),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "error",
          title: "BUILD / FAILED",
          summary: event.message || "构建失败",
          ts: event.ts,
        },
      );
    }
    case "runtime_built": {
      return withTimeline(
        withTerminal(base, {
          kind: "ok",
          text:
            "● standalone ready · " +
            Math.round((event.bytes || 0) / 1024 / 1024) +
            " MB",
        }),
        {
          key: `evt-${event.seq}`,
          kind: "step",
          title: "RUNTIME / BUILT",
          summary:
            event.message ||
            "应用运行时产物已生成 · " +
              Math.round((event.bytes || 0) / 1024 / 1024) +
              " MB",
          ts: event.ts,
        },
      );
    }
    case "runtime_starting": {
      return withTimeline(
        withTerminal(base, {
          kind: "muted",
          text: "● starting app runtime on :" + (event.port || 3000),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "thought",
          title: "RUNTIME / STARTING",
          summary: "正在启动应用运行时",
          ts: event.ts,
        },
      );
    }
    case "runtime_ready": {
      return withTimeline(
        withTerminal(
          { ...base, previewReady: true },
          { kind: "ok", text: "✔ app runtime ready" },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "deploy",
          title: "RUNTIME / READY",
          summary: event.url || "应用运行时已启动",
          ts: event.ts,
        },
      );
    }
    case "runtime_error": {
      return withTimeline(
        withTerminal(base, {
          kind: "err",
          text: "✗ app runtime failed · " + (event.message || ""),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "error",
          title: "RUNTIME / FAILED",
          summary: event.message || "应用运行时启动失败",
          ts: event.ts,
        },
      );
    }
    case "runtime_stopped": {
      return withTimeline(
        withTerminal(base, {
          kind: "muted",
          text: "● app runtime stopped",
        }),
        {
          key: `evt-${event.seq}`,
          kind: "step",
          title: "RUNTIME / STOPPED",
          summary: event.message || "应用运行时已停止",
          ts: event.ts,
        },
      );
    }
    case "verify": {
      const name = event.name || "check";
      const check = {
        name,
        ok: Boolean(event.ok),
        detail: event.detail || "",
      };
      return withTimeline(
        withTerminal(
          { ...base, checks: upsertChecks(base.checks, [check]) },
          {
            kind: event.ok ? "ok" : "err",
            text:
              (event.ok ? "✓ " : "✗ ") +
              name +
              " · " +
              (event.detail || ""),
          },
        ),
        {
          key: `evt-${event.seq}`,
          kind: event.ok ? "verify" : "error",
          title: "VERIFY / " + name,
          summary: (event.ok ? "通过" : "未通过") + (event.detail ? " · " + event.detail : ""),
          chip: event.ok ? "PASS" : "FAIL",
          chipTone: event.ok ? "ok" : "fail",
          ts: event.ts,
        },
      );
    }
    case "deployed": {
      return withTimeline(
        withTerminal(
          {
            ...base,
            previewReady: true,
            outcome: {
              title: event.title || "已部署",
              text: "已部署到 Agent Server，页面可直接交互。",
            },
          },
          { kind: "ok", text: "✔ deployed → " + (event.url || "") },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "deploy",
          title: "DEPLOYED",
          summary: event.url || "",
          ts: event.ts,
        },
      );
    }
    case "done": {
      const checks = Array.isArray(event.checks)
        ? event.checks.map((check) => ({
            name: check.name,
            ok: check.ok,
            detail: check.detail,
          }))
        : [];
      return withTimeline(
        withTerminal(
          {
            ...base,
            terminal: "done",
            previewReady: true,
            currentStep: null,
            checks: checks.length ? upsertChecks(base.checks, checks) : base.checks,
            outcome: {
              title: event.title || "已完成",
              text: event.summary || "任务完成。",
            },
          },
          {
            kind: "ok",
            text: "● task complete · " + (event.url || event.summary || ""),
          },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "done",
          title: event.source === "refine-failed" ? "UNCHANGED" : "COMPLETE",
          summary: event.summary || "任务完成。",
          ts: event.ts,
        },
      );
    }
    case "refine_started": {
      return withTimeline(
        withTerminal(
          {
            ...base,
            currentStep: null,
            outcome: {
              title: "正在修改",
              text: event.instruction || "Agent 正在根据你的要求修改。",
            },
          },
          { kind: "cmd", text: "$ refine · " + (event.instruction || "") },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "step",
          title: "YOUR EDIT",
          summary: event.instruction || "",
          ts: event.ts,
        },
      );
    }
    case "refine_failed": {
      return withTimeline(
        withTerminal(base, {
          kind: "err",
          text: "✗ " + (event.message || "修改未应用"),
        }),
        {
          key: `evt-${event.seq}`,
          kind: "error",
          title: "EDIT NOT APPLIED",
          summary: event.message || "修改未应用，原页面保持不变。",
          ts: event.ts,
        },
      );
    }
    case "interrupted": {
      return withTimeline(
        withTerminal(
          {
            ...base,
            terminal: "interrupted",
            currentStep: null,
            outcome: {
              title: "任务已中断",
              text: "任务在服务重启前中断，原产物已保留。",
            },
          },
          {
            kind: "err",
            text: "! " + (event.message || "task interrupted"),
          },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "error",
          title: "INTERRUPTED",
          summary: event.message || "任务在服务重启前中断，原产物已保留。",
          ts: event.ts,
        },
      );
    }
    case "error": {
      return withTimeline(
        withTerminal(
          {
            ...base,
            terminal: "error",
            currentStep: null,
            outcome: {
              title: "生成失败",
              text: event.message || event.summary || "任务执行失败。",
            },
          },
          { kind: "err", text: "✗ " + (event.message || "task failed") },
        ),
        {
          key: `evt-${event.seq}`,
          kind: "error",
          title: "ERROR",
          summary: event.message || event.summary || "任务执行失败。",
          ts: event.ts,
        },
      );
    }
    default:
      return base;
  }
}

export function buildProjectView(events: TaskEvent[]): ProjectViewState {
  return [...events]
    .sort((a, b) => a.seq - b.seq)
    .reduce(applyProjectEvent, initialProjectView);
}

export function projectPageStatus(
  task: Task,
  view: ProjectViewState,
  runtime: RuntimeState | null,
): { label: string; tone: "running" | "done" | "error" } {
  if (view.terminal === "error" || task.status === "error") {
    return { label: "FAILED", tone: "error" };
  }
  if (view.terminal === "interrupted" || task.status === "interrupted") {
    return { label: "INTERRUPTED", tone: "error" };
  }
  if (task.status === "done" || view.terminal === "done") {
    if (task.stack === "next") {
      return runtime?.status === "running"
        ? { label: "APP RUNNING", tone: "done" }
        : { label: "BUILT", tone: "done" };
    }
    return { label: "DEPLOYED", tone: "done" };
  }
  if (task.status === "deploying") return { label: "DEPLOYING", tone: "running" };
  if (task.status === "running") return { label: "RUNNING", tone: "running" };
  return { label: "QUEUED", tone: "running" };
}
