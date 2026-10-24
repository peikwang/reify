import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Task } from "../../api/types";
import { ToastProvider } from "../../layout/ToastProvider";
import { RefineBar } from "./RefineBar";

const task: Task = {
  id: "p1",
  prompt: "做一个作品集",
  capability: "website",
  status: "done",
  created_at: "2026-10-24T05:00:00+00:00",
  updated_at: "2026-10-24T06:00:00+00:00",
  result: null,
  error: null,
  source: "director",
  title: "作品集",
  revision: 1,
  stack: "static",
  url: "/p/p1/",
  shared: false,
  share_url: null,
  event_count: 0,
};

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RefineBar", () => {
  it("posts an instruction and reports the queued task", async () => {
    const updated = { ...task, status: "queued" as const };
    const fetchMock = vi.fn(async () => jsonResponse({ task: updated }));
    vi.stubGlobal("fetch", fetchMock);
    const onStarted = vi.fn();

    render(
      <ToastProvider>
        <RefineBar task={task} running={false} onStarted={onStarted} />
      </ToastProvider>,
    );

    const input = screen.getByLabelText("修改指令");
    fireEvent.change(input, { target: { value: "把标题改成静页" } });
    fireEvent.click(screen.getByRole("button", { name: "发送修改" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/p1/refine",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ instruction: "把标题改成静页" }),
        }),
      );
    });
    expect(onStarted).toHaveBeenCalledWith(expect.objectContaining({ status: "queued" }));
    expect(input).toHaveValue("");
  });

  it("disables the form while the agent is running", () => {
    render(
      <ToastProvider>
        <RefineBar task={task} running onStarted={() => {}} />
      </ToastProvider>,
    );

    expect(screen.getByLabelText("修改指令")).toBeDisabled();
    expect(screen.getByRole("button", { name: "发送修改" })).toBeDisabled();
    expect(screen.getByText("Agent 正在处理，请稍候…")).toBeInTheDocument();
  });

  it("does not submit an empty instruction", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(
      <ToastProvider>
        <RefineBar task={task} running={false} onStarted={() => {}} />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "发送修改" }));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
