import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AdminUsersResponse, AuditResponse } from "../api/types";
import { ToastProvider } from "../layout/ToastProvider";
import { AdminPage } from "./AdminPage";

const users: AdminUsersResponse = {
  items: [
    {
      id: "u1",
      username: "admin",
      display_name: "管理员",
      email: null,
      role: "admin",
      created_at: "2026-10-01T00:00:00+00:00",
      disabled: false,
      last_login_at: "2026-10-24T05:00:00+00:00",
      projects: 3,
      storage_bytes: 2048,
    },
    {
      id: "u2",
      username: "alice",
      display_name: "Alice",
      email: "alice@example.test",
      role: "user",
      created_at: "2026-10-02T00:00:00+00:00",
      disabled: true,
      last_login_at: null,
      projects: 1,
      storage_bytes: 1024,
    },
  ],
};

const audit: AuditResponse = {
  items: [
    {
      id: 7,
      ts: "2026-10-24T06:00:00+00:00",
      user_id: "u1",
      action: "project.share",
      project_id: "p1",
      ip: null,
      detail: "static",
    },
  ],
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

describe("AdminPage", () => {
  it("renders users, audit and applies admin actions", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/admin/users") return jsonResponse(users);
      if (path === "/api/admin/audit?limit=100") return jsonResponse(audit);
      if (path.endsWith("/status")) return jsonResponse({ ok: true, disabled: true });
      if (path.endsWith("/revoke-sessions")) return jsonResponse({ ok: true });
      return new Response("not found", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter>
        <ToastProvider>
          <AdminPage />
        </ToastProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("管理员")).toBeInTheDocument();
    });
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("project.share")).toBeInTheDocument();
    expect(screen.getByText(/DISABLED/)).toBeInTheDocument();

    const disableButtons = screen.getAllByRole("button", { name: "禁用" });
    expect(disableButtons).toHaveLength(1);
    fireEvent.click(disableButtons[0]);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/admin/users/u1/status",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ disabled: true }),
        }),
      );
    });

    fireEvent.click(screen.getAllByRole("button", { name: "下线" })[0]);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/admin/users/u1/revoke-sessions",
        expect.objectContaining({ method: "POST" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "启用" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/admin/users/u2/status",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ disabled: false }),
        }),
      );
    });
  });

  it("shows a load error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("boom", { status: 500 })),
    );

    render(
      <MemoryRouter>
        <ToastProvider>
          <AdminPage />
        </ToastProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getAllByText(/管理数据加载失败/).length).toBeGreaterThan(0);
    });
  });
});
