import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { Capability, Task } from "../../api/types";
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

function renderCard(item: Task) {
  render(
    <MemoryRouter>
      <ProjectCard task={item} index={0} capabilities={capabilities} />
    </MemoryRouter>,
  );
}

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

  it("keeps capability labels without exposing implementation stacks", () => {
    renderCard(task({ status: "done", share_url: null, stack: "react" }));
    expect(screen.getAllByText("WEB").length).toBeGreaterThan(0);
    expect(screen.queryByText("REACT")).not.toBeInTheDocument();
    expect(screen.queryByText("NEXT")).not.toBeInTheDocument();
  });
});
