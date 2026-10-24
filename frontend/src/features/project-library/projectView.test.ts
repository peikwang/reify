import { describe, expect, it } from "vitest";

import type { Task } from "../../api/types";
import {
  buildCapabilityFilters,
  capabilityInfo,
  filterProjects,
  projectStats,
  projectStatus,
  relativeTime,
  revisionLabel,
} from "./projectView";

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

describe("projectStats", () => {
  it("counts deployments and revisions", () => {
    const stats = projectStats([
      task({ id: "a", status: "done", revision: 2 }),
      task({ id: "b", status: "error", revision: 1 }),
      task({ id: "c", status: "done", revision: 3 }),
    ]);
    expect(stats).toEqual({ total: 3, deployed: 2, revisions: 6 });
  });
});

describe("project filters", () => {
  const capabilities = [
    { key: "game", label: "小游戏", short: "GAME" },
    { key: "website", label: "网站", short: "WEB" },
    { key: "image", label: "图片", short: "IMAGE" },
    { key: "resume", label: "简历", short: "CV" },
  ].map((item) => ({
    ...item,
    description: "",
    example: "",
    prompt: "",
  }));

  it("only exposes capabilities present in the project list", () => {
    const items = [
      task({ id: "a", capability: "image" }),
      task({ id: "b", capability: "website" }),
      task({ id: "c", capability: "website" }),
    ];
    expect(buildCapabilityFilters(items, capabilities)).toEqual([
      { key: "all", label: "全部", count: 3 },
      { key: "website", label: "网站", count: 2 },
      { key: "image", label: "图片", count: 1 },
    ]);
  });

  it("filters by capability and returns every item for all", () => {
    const items = [
      task({ id: "a", capability: "image" }),
      task({ id: "b", capability: "website" }),
    ];
    expect(filterProjects(items, "all")).toHaveLength(2);
    expect(filterProjects(items, "image").map((item) => item.id)).toEqual(["a"]);
  });

  it("falls back to the raw key when capabilities are unavailable", () => {
    expect(capabilityInfo("website", [])).toEqual({
      key: "website",
      label: "网站",
      short: "WEB",
    });
    expect(capabilityInfo("custom", [])).toEqual({
      key: "custom",
      label: "custom",
      short: "custom",
    });
  });
});

describe("project card view helpers", () => {
  it("maps task status to a label and tone", () => {
    expect(projectStatus(task({ status: "done" })).label).toBe("DEPLOYED");
    expect(projectStatus(task({ status: "error" }))).toEqual({
      label: "FAILED",
      tone: "error",
    });
    expect(projectStatus(task({ status: "interrupted" }))).toEqual({
      label: "INTERRUPTED",
      tone: "error",
    });
    expect(projectStatus(task({ status: "running" }))).toEqual({
      label: "RUNNING",
      tone: "ok",
    });
  });

  it("formats revision labels from capability-neutral task metadata", () => {
    expect(revisionLabel(task({ revision: 0 }))).toBe("V1");
    expect(revisionLabel(task({ revision: 3 }))).toBe("REV 3");
  });

  it("formats relative times", () => {
    const now = Date.parse("2026-10-24T12:00:00+00:00");
    expect(relativeTime("2026-10-24T11:59:30+00:00", now)).toBe("刚刚");
    expect(relativeTime("2026-10-24T11:55:00+00:00", now)).toBe("5 分钟前");
    expect(relativeTime("2026-10-24T10:00:00+00:00", now)).toBe("2 小时前");
    expect(relativeTime("2026-10-21T12:00:00+00:00", now)).toBe("3 天前");
  });
});
