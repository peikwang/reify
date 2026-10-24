import { describe, expect, it } from "vitest";

import type { RuntimeState, Task, TaskEvent } from "../../api/types";
import {
  applyProjectEvent,
  buildProjectView,
  initialProjectView,
  projectPageStatus,
  type ProjectViewState,
} from "./eventView";

function event(seq: number, type: string, extra: Partial<TaskEvent> = {}): TaskEvent {
  return { seq, type, ts: "2026-10-24T06:00:00+00:00", ...extra };
}

function applyAll(events: TaskEvent[]): ProjectViewState {
  return events.reduce(applyProjectEvent, initialProjectView);
}

function task(overrides: Partial<Task> = {}): Task {
  return {
    id: "p1",
    prompt: "做一个网站",
    capability: "website",
    status: "done",
    created_at: "2026-10-24T05:00:00+00:00",
    updated_at: "2026-10-24T06:00:00+00:00",
    result: null,
    error: null,
    source: "director",
    title: "测试项目",
    revision: 0,
    stack: "static",
    url: "/p/p1/",
    shared: false,
    share_url: null,
    event_count: 0,
    ...overrides,
  };
}

describe("applyProjectEvent", () => {
  it("builds plan steps and updates their status", () => {
    const state = applyAll([
      event(1, "plan", { steps: ["规划", "生成", "发布"] }),
      event(2, "step_started", { index: 0, title: "规划" }),
      event(3, "step_done", { index: 0, summary: "方向已确定" }),
    ]);
    expect(state.plan).toEqual(["规划", "生成", "发布"]);
    expect(state.planStatus).toEqual(["done", "pending", "pending"]);
    expect(state.currentStep).toBe(0);
    const step = state.timeline.find((item) => item.kind === "step");
    expect(step?.chip).toBe("方向已确定");
  });

  it("deduplicates events by sequence", () => {
    const first = applyProjectEvent(
      initialProjectView,
      event(1, "thinking", { summary: "a" }),
    );
    const duplicate = applyProjectEvent(
      first,
      event(1, "thinking", { summary: "duplicate" }),
    );
    expect(duplicate).toBe(first);
    const next = applyProjectEvent(
      first,
      event(2, "thinking", { summary: "b" }),
    );
    expect(next.timeline).toHaveLength(2);
  });

  it("upserts verify checks by name", () => {
    const state = applyAll([
      event(1, "verify", { name: "结构完整", ok: false, detail: "missing" }),
      event(2, "verify", { name: "结构完整", ok: true, detail: "ok" }),
      event(3, "verify", { name: "移动端适配", ok: true, detail: "ok" }),
    ]);
    expect(state.checks).toEqual([
      { name: "结构完整", ok: true, detail: "ok" },
      { name: "移动端适配", ok: true, detail: "ok" },
    ]);
  });

  it("collects build logs in the terminal without bloating the timeline", () => {
    const before = applyProjectEvent(
      initialProjectView,
      event(1, "build_started", { files: 4, image: "node:24" }),
    );
    const after = applyProjectEvent(
      before,
      event(2, "build_log", { line: "vite build" }),
    );
    expect(after.timeline).toHaveLength(before.timeline.length);
    expect(after.terminalLines).toHaveLength(before.terminalLines.length + 1);
    expect(after.terminalLines.at(-1)?.text).toBe("vite build");
    expect(after.lastSeq).toBe(2);
  });

  it("summarizes file diffs without storing their content", () => {
    const state = applyProjectEvent(
      initialProjectView,
      event(1, "file_diff", {
        path: "src/App.tsx",
        before: "a\nb",
        after: "a\nb\nc",
        created: false,
        reason: "添加区块",
      }),
    );
    expect(state.timeline[0]?.summary).toContain("+1 行");
    expect(state.timeline[0]?.detail).toBe("添加区块");
    expect(state.files["src/App.tsx"]?.content).toBe("a\nb\nc");
    expect(state.files["src/App.tsx"]?.before).toBe("a\nb");
    expect(state.terminalLines.at(-1)?.text).toContain("src/App.tsx");
  });

  it("closes the view on done with checks and outcome", () => {
    const state = applyAll([
      event(1, "plan", { steps: ["规划"] }),
      event(2, "deployed", { url: "/p/p1/" }),
      event(3, "done", {
        title: "测试项目",
        summary: "已完成",
        revision: 2,
        checks: [{ name: "结构完整", ok: true, detail: "ok" }],
      }),
    ]);
    expect(state.terminal).toBe("done");
    expect(state.previewReady).toBe(true);
    expect(state.planStatus).toEqual(["done"]);
    expect(state.outcome).toEqual({ title: "测试项目", text: "已完成" });
    expect(state.checks).toEqual([{ name: "结构完整", ok: true, detail: "ok" }]);
  });

  it("clears a previous terminal state when a refine starts", () => {
    const state = applyAll([
      event(1, "plan", { steps: ["规划", "生成"] }),
      event(2, "done", {
        title: "旧版本",
        summary: "已完成",
        checks: [{ name: "结构完整", ok: true, detail: "ok" }],
      }),
      event(3, "refine_started", { instruction: "换个标题" }),
    ]);
    expect(state.terminal).toBeNull();
    expect(state.previewReady).toBe(false);
    expect(state.plan).toEqual(["理解修改要求", "应用修改并重建", "验证并发布"]);
    expect(state.planStatus).toEqual(["active", "pending", "pending"]);
    expect(state.checks).toEqual([]);
    expect(state.currentStep).toBe(0);
    expect(state.outcome?.title).toBe("正在修改");
  });

  it("replays a unique event list deterministically", () => {    const events = [
      event(2, "done", { title: "完成" }),
      event(1, "plan", { steps: ["规划"] }),
    ];
    const first = buildProjectView(events);
    const second = buildProjectView(events);
    expect(first.plan).toEqual(["规划"]);
    expect(first.terminal).toBe("done");
    expect(second).toEqual(first);
    expect(first.timeline.map((item) => item.key)).toEqual(
      Array.from(new Set(first.timeline.map((item) => item.key))),
    );
  });

  it("marks error and interrupted terminals", () => {
    const failed = applyProjectEvent(
      initialProjectView,
      event(1, "error", { message: "构建失败" }),
    );
    expect(failed.terminal).toBe("error");
    expect(failed.outcome?.text).toBe("构建失败");
    const interrupted = applyProjectEvent(
      initialProjectView,
      event(1, "interrupted", { message: "服务重启" }),
    );
    expect(interrupted.terminal).toBe("interrupted");
  });
});

describe("projectPageStatus", () => {
  const runningRuntime: RuntimeState = { status: "running", url: "/apps/p1/" };

  it("uses product-facing status labels", () => {
    expect(projectPageStatus(task(), initialProjectView, null)).toEqual({
      label: "DEPLOYED",
      tone: "done",
    });
    expect(
      projectPageStatus(
        task({ stack: "next" }),
        initialProjectView,
        runningRuntime,
      ),
    ).toEqual({ label: "APP RUNNING", tone: "done" });
    expect(
      projectPageStatus(task({ stack: "next" }), initialProjectView, {
        status: "stopped",
      }),
    ).toEqual({ label: "BUILT", tone: "done" });
    expect(
      projectPageStatus(task({ status: "error" }), initialProjectView, null),
    ).toEqual({ label: "FAILED", tone: "error" });
  });
});
