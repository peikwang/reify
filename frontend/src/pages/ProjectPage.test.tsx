import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  CapabilitiesResponse,
  ProjectDetailResponse,
  Task,
  TaskEvent,
} from "../api/types";
import { ToastProvider } from "../layout/ToastProvider";
import { ProjectPage } from "./ProjectPage";

const capabilities: CapabilitiesResponse = {
  items: [
    {
      key: "website",
      label: "网站",
      short: "WEB",
      description: "网站",
      example: "",
      prompt: "",
    },
  ],
  sandbox: { backend: "off", image: null },
  ssr_preview: false,
  ssr_port: null,
};

const task: Task = {
  id: "p1",
  prompt: "做一个安静的摄影作品集",
  capability: "website",
  status: "done",
  created_at: "2026-10-24T05:00:00+00:00",
  updated_at: "2026-10-24T06:00:00+00:00",
  result: null,
  error: null,
  source: "director",
  title: "测试项目",
  revision: 1,
  stack: "static",
  url: "/p/p1/",
  shared: true,
  share_url: "/s/public-token/",
  event_count: 0,
};

const events: TaskEvent[] = [
  { seq: 1, type: "plan", ts: "2026-10-24T06:00:01+00:00", steps: ["规划", "生成", "发布"] },
  { seq: 2, type: "step_started", ts: "2026-10-24T06:00:02+00:00", index: 0, title: "规划" },
  {
    seq: 3,
    type: "file_diff",
    ts: "2026-10-24T06:00:03+00:00",
    path: "src/App.jsx",
    before: "",
    after: "const title = 'hello';\n",
    created: true,
    language: "jsx",
    reason: "生成页面",
  },
  { seq: 4, type: "step_done", ts: "2026-10-24T06:00:04+00:00", index: 0, summary: "完成" },
  { seq: 5, type: "verify", ts: "2026-10-24T06:00:05+00:00", name: "结构完整", ok: true, detail: "ok" },
  { seq: 6, type: "deployed", ts: "2026-10-24T06:00:06+00:00", url: "/p/p1/" },
  {
    seq: 7,
    type: "done",
    ts: "2026-10-24T06:00:07+00:00",
    title: "测试项目",
    summary: "已完成",
    revision: 1,
    checks: [{ name: "结构完整", ok: true, detail: "ok" }],
  },
];

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  const detail: ProjectDetailResponse = { task, events };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/capabilities") return jsonResponse(capabilities);
      if (path === "/api/projects/p1") return jsonResponse(detail);
      return new Response("not found", { status: 404 });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProjectPage", () => {
  it("renders a read-only project with plan, checks, preview and public link", async () => {
    render(
      <MemoryRouter initialEntries={["/projects/p1"]}>
        <ToastProvider>
          <Routes>
            <Route path="/projects/:id" element={<ProjectPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getAllByText("测试项目").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("DEPLOYED").length).toBeGreaterThan(0);
    expect(screen.getAllByText("规划").length).toBeGreaterThan(0);
    expect(screen.getAllByText("结构完整").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /公开页/ })).toHaveAttribute(
      "href",
      "/s/public-token/",
    );
    expect(screen.getByLabelText("修改指令")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重新部署" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "取消分享" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "导出源码" })).toHaveAttribute(
      "href",
      "/api/projects/p1/bundle",
    );
    const iframe = document.querySelector("iframe");
    expect(iframe).not.toBeNull();
    expect(iframe?.getAttribute("src")).toBe("/p/p1/");

    fireEvent.click(screen.getByRole("tab", { name: "编程" }));
    await waitFor(() => {
      expect(document.querySelector("#diffPath")?.textContent).toBe("src/App.jsx");
    });
    expect(document.querySelectorAll(".diff-line.add").length).toBeGreaterThan(0);
    expect(screen.getByText("TERMINAL")).toBeInTheDocument();
    expect(document.querySelector("#miniState")?.textContent).toBe("READY");
  });
});
