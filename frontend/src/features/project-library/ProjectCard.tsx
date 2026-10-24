import type { CSSProperties } from "react";
import { Link } from "react-router-dom";

import type { Capability, Task } from "../../api/types";
import {
  COVER_GLYPHS,
  capabilityInfo,
  projectStatus,
  relativeTime,
  revisionLabel,
} from "./projectView";

interface ProjectCardProps {
  task: Task;
  index: number;
  capabilities: Capability[];
}

export function ProjectCard({ task, index, capabilities }: ProjectCardProps) {
  const info = capabilityInfo(task.capability, capabilities);
  const status = projectStatus(task);
  const title = task.title || task.prompt || "未命名项目";
  const publicUrl = task.status === "done" ? task.share_url : null;

  return (
    <article
      className="project-card"
      style={{ "--i": index } as CSSProperties}
    >
      <Link
        className="project-card-main"
        to={"/projects/" + encodeURIComponent(task.id)}
      >
        <div className={"project-cover cover-" + info.key}>
          <span className="cover-label">{info.short}</span>
          <span className="cover-index">{String(index + 1).padStart(2, "0")}</span>
          <span className="cover-glyph">{COVER_GLYPHS[task.capability] ?? "·"}</span>
        </div>
        <div className="project-card-body">
          <div className="project-card-top">
            <span>
              {info.label} / {relativeTime(task.created_at)}
            </span>
            <span className="project-status">
              <i
                style={{
                  background: status.tone === "error" ? "var(--red)" : "var(--green)",
                }}
              />
              {status.label}
            </span>
          </div>
          <h3>{title}</h3>
          <p>{task.prompt}</p>
        </div>
      </Link>
      <div className="project-card-foot">
        <span>{revisionLabel(task)}</span>
        <span className="project-card-foot-right">
          <span>{info.short}</span>
          {publicUrl ? (
            <a
              className="project-public-link"
              href={publicUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="打开免登录公开页面"
            >
              公开页 ↗
            </a>
          ) : null}
        </span>
      </div>
    </article>
  );
}
