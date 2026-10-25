import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Task } from "../../api/types";
import { ToastProvider } from "../../layout/ToastProvider";
import { ProjectEditPanel } from "./ProjectEditPanel";

const task: Task = {
  id: "abc123",
  prompt: "做一个贪吃蛇小游戏",
  capability: "game",
  status: "done",
  created_at: "2026-10-25T03:00:00+00:00",
  updated_at: "2026-10-25T03:00:00+00:00",
  result: null,
  error: null,
  source: "director",
  title: "贪吃蛇",
  revision: 0,
  stack: "static",
  url: "/p/abc123/",
  shared: true,
  share_url: "/s/token/",
  event_count: 1,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProjectEditPanel", () => {
  it("renames the project through PATCH", async () => {
    const updated = { ...task, title: "新的名字" };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, task: updated }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const onTaskChange = vi.fn();

    render(
      <ToastProvider>
        <ProjectEditPanel
          task={task}
          running={false}
          deleting={false}
          onTaskChange={onTaskChange}
          onDelete={vi.fn()}
        />
      </ToastProvider>,
    );

    fireEvent.change(screen.getByLabelText("名称"), {
      target: { value: "新的名字" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存名称" }));

    await waitFor(() => expect(onTaskChange).toHaveBeenCalledWith(updated));
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/projects/abc123");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toEqual({ title: "新的名字" });
  });

  it("requires a second click before deleting", () => {
    const onDelete = vi.fn();
    render(
      <ToastProvider>
        <ProjectEditPanel
          task={task}
          running={false}
          deleting={false}
          onTaskChange={vi.fn()}
          onDelete={onDelete}
        />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "删除项目" }));
    expect(onDelete).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "再次点击确认删除" }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});
