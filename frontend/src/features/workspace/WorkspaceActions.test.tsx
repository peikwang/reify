import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RuntimeState, Task } from "../../api/types";
import { ToastProvider } from "../../layout/ToastProvider";
import { WorkspaceActions } from "./WorkspaceActions";

const baseTask: Task = {
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

beforeEach(() => {
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn(async () => undefined) },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("WorkspaceActions", () => {
  it("deploys, shares and exports a static project", async () => {
    const onTaskChange = vi.fn();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/deploy")) {
        return jsonResponse({ ok: true, url: "/p/p1/", manifest: { url: "/p/p1/" } });
      }
      if (path.endsWith("/share")) {
        return jsonResponse({ ok: true, share_token: "token", url: "/s/token/" });
      }
      return new Response("not found", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ToastProvider>
        <WorkspaceActions
          task={baseTask}
          running={false}
          runtime={null}
          onTaskChange={onTaskChange}
          onRuntimeChange={() => {}}
        />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "重新部署" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/p1/deploy",
        expect.objectContaining({ method: "POST" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "分享" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/p1/share",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(onTaskChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ share_url: "/s/token/", shared: true }),
    );
    expect(screen.getByRole("link", { name: /公开页/ })).toHaveAttribute(
      "href",
      "/s/token/",
    );
    expect(screen.getByRole("link", { name: "导出源码" })).toHaveAttribute(
      "href",
      "/api/projects/p1/bundle",
    );
  });

  it("removes an existing public link", async () => {
    const onTaskChange = vi.fn();
    const fetchMock = vi.fn(async () => jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ToastProvider>
        <WorkspaceActions
          task={{ ...baseTask, shared: true, share_url: "/s/token/" }}
          running={false}
          runtime={null}
          onTaskChange={onTaskChange}
          onRuntimeChange={() => {}}
        />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "取消分享" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/p1/share",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
    expect(onTaskChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ share_url: null, shared: false }),
    );
  });

  it("starts and stops the app runtime for a Next project", async () => {
    const nextTask: Task = { ...baseTask, stack: "next", url: "" };
    const onRuntimeChange = vi.fn();
    const runningState: RuntimeState = { status: "running", url: "https://example.test/apps/p1/" };
    const stoppedState: RuntimeState = { status: "stopped" };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/runtime/start")) {
        return jsonResponse({ ok: true, runtime: runningState });
      }
      return jsonResponse({ ok: true, runtime: stoppedState });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(
      <ToastProvider>
        <WorkspaceActions
          task={nextTask}
          running={false}
          runtime={stoppedState}
          onTaskChange={() => {}}
          onRuntimeChange={onRuntimeChange}
        />
      </ToastProvider>,
    );

    expect(screen.queryByRole("button", { name: "分享" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "重新部署" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "启动应用" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/p1/runtime/start",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(onRuntimeChange).toHaveBeenLastCalledWith(runningState);

    rerender(
      <ToastProvider>
        <WorkspaceActions
          task={nextTask}
          running={false}
          runtime={runningState}
          onTaskChange={() => {}}
          onRuntimeChange={onRuntimeChange}
        />
      </ToastProvider>,
    );
    expect(screen.getByText("APP RUNNING")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "停止应用" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/projects/p1/runtime/stop",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });
});
