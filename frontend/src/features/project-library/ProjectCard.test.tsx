import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Capability, Task } from "../../api/types";
import { ToastProvider } from "../../layout/ToastProvider";
import { ProjectCard } from "./ProjectCard";

const capabilities: Capability[] = [
  {
    key: "website",
    label: "网站",
    short: "WEB",
    description: "",
    example: "",
    prompt: "",
  },
];

function task(overrides: Partial<Task>): Task {
  return {
    id: "p1",
    prompt: "做一个官网",
    capability: "website",
    status: "done",
    created_at: "2026-10-24T05:00:00+00:00",
    updated_at: "2026-10-24T05:00:00+00:00",
    result: null,
    error: null,
    source: "director",
    title: "Lumen Studio",
    revision: 0,
    stack: "static",
    url: "/p/p1/",
    shared: false,
    share_url: null,
    event_count: 0,
    ...overrides,
  };
}

function renderCard(
  item: Task,
  onMutated?: () => void | Promise<void>,
) {
  render(
    <MemoryRouter>
      <ToastProvider>
        <ProjectCard
          task={item}
          index={0}
          capabilities={capabilities}
          onMutated={onMutated}
        />
      </ToastProvider>
    </MemoryRouter>,
  );
}

function openMenu(item = task({ status: "done" })) {
  fireEvent.click(
    screen.getByRole("button", {
      name: "更多操作 " + (item.title || item.prompt),
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProjectCard", () => {
  it("links completed projects to their unlisted public page", () => {
    renderCard(task({ status: "done", share_url: "/s/public-token/" }));

    const link = screen.getByRole("link", { name: /公开页/ });
    expect(link).toHaveAttribute("href", "/s/public-token/");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
  });

  it("hides the public link while the project is still running", () => {
    renderCard(task({ status: "running", share_url: "/s/public-token/" }));
    expect(screen.queryByRole("link", { name: /公开页/ })).not.toBeInTheDocument();
  });

  it("opens a quick menu with rename, edit and delete actions", () => {
    renderCard(task({ status: "done" }));
    openMenu();

    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "重命名" })).toBeInTheDocument();
    const edit = screen.getByRole("menuitem", { name: "编辑详情" });
    expect(edit).toHaveAttribute("href", "/projects/p1?tab=edit");
    expect(screen.getByRole("menuitem", { name: "删除项目" })).toBeInTheDocument();
  });

  it("renames the project from the quick menu", async () => {
    const onMutated = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, task: task({ title: "新名字" }) }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderCard(task({ status: "done" }), onMutated);

    openMenu();
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));
    fireEvent.change(screen.getByLabelText("项目名称"), {
      target: { value: "新名字" },
    });
    fireEvent.click(screen.getByRole("button", { name: /保存名称/ }));

    await waitFor(() => expect(onMutated).toHaveBeenCalledTimes(1));
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/projects/p1");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body))).toEqual({ title: "新名字" });
  });

  it("deletes the project after confirmation", async () => {
    const onMutated = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderCard(task({ status: "done" }), onMutated);

    openMenu();
    fireEvent.click(screen.getByRole("menuitem", { name: "删除项目" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => expect(onMutated).toHaveBeenCalledTimes(1));
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/projects/p1");
    expect(init.method).toBe("DELETE");
  });

  it("disables delete while the project is still running", () => {
    renderCard(task({ status: "running" }));
    openMenu(task({ status: "running" }));
    expect(screen.getByRole("menuitem", { name: "删除项目" })).toBeDisabled();
  });

  it("keeps capability labels without exposing implementation stacks", () => {
    renderCard(task({ status: "done", share_url: null, stack: "react" }));
    expect(screen.getAllByText("WEB").length).toBeGreaterThan(0);
    expect(screen.queryByText("REACT")).not.toBeInTheDocument();
    expect(screen.queryByText("NEXT")).not.toBeInTheDocument();
  });
});
