import type { Capability, Task } from "../../api/types";

export interface CapabilityInfo {
  key: string;
  label: string;
  short: string;
}

export interface CapabilityFilter {
  key: string;
  label: string;
  count: number;
}

export type ProjectTone = "ok" | "error";

export interface ProjectStatusView {
  label: string;
  tone: ProjectTone;
}

const FALLBACK_CAPABILITIES: Record<string, CapabilityInfo> = {
  game: { key: "game", label: "小游戏", short: "GAME" },
  website: { key: "website", label: "网站", short: "WEB" },
  image: { key: "image", label: "图片", short: "IMAGE" },
  video: { key: "video", label: "视频", short: "VIDEO" },
  resume: { key: "resume", label: "简历", short: "CV" },
  travel: { key: "travel", label: "旅游攻略", short: "TRIP" },
  adapt: { key: "adapt", label: "适配制作", short: "ADAPT" },
  code: { key: "code", label: "编程", short: "CODE" },
};

export const CAPABILITY_ORDER = [
  "game",
  "website",
  "image",
  "video",
  "resume",
  "travel",
  "adapt",
  "code",
];

export const COVER_GLYPHS: Record<string, string> = {
  game: "▶",
  website: "Aa",
  image: "IMG",
  video: "VID",
  resume: "CV",
  travel: "↗",
  adapt: "▣",
  code: "</>",
};

export function capabilityInfo(key: string, capabilities: Capability[]): CapabilityInfo {
  const found = capabilities.find((item) => item.key === key);
  if (found) {
    return { key: found.key, label: found.label, short: found.short };
  }
  return FALLBACK_CAPABILITIES[key] ?? { key, label: key, short: key };
}

export function projectStatus(task: Task): ProjectStatusView {
  if (task.status === "done") return { label: "DEPLOYED", tone: "ok" };
  if (task.status === "error") return { label: "FAILED", tone: "error" };
  if (task.status === "interrupted") return { label: "INTERRUPTED", tone: "error" };
  return { label: "RUNNING", tone: "ok" };
}

export function projectStats(items: Task[]) {
  return {
    total: items.length,
    deployed: items.filter((task) => task.status === "done").length,
    revisions: items.reduce((sum, task) => sum + (task.revision || 0), 0),
  };
}

export function buildCapabilityFilters(
  items: Task[],
  capabilities: Capability[],
): CapabilityFilter[] {
  const available = CAPABILITY_ORDER.filter((key) =>
    items.some((task) => task.capability === key),
  );
  return [
    { key: "all", label: "全部", count: items.length },
    ...available.map((key) => ({
      key,
      label: capabilityInfo(key, capabilities).label,
      count: items.filter((task) => task.capability === key).length,
    })),
  ];
}

export function filterProjects(items: Task[], filter: string): Task[] {
  if (filter === "all") return items;
  return items.filter((task) => task.capability === filter);
}

export function revisionLabel(task: Task): string {
  return task.revision ? "REV " + task.revision : "V1";
}

export function relativeTime(iso: string, now = Date.now()): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return "";
  const minutes = Math.max(0, Math.floor((now - parsed) / 60_000));
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return minutes + " 分钟前";
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return hours + " 小时前";
  return Math.floor(hours / 24) + " 天前";
}
