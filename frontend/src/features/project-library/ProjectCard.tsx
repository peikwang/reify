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

  return (
    <Link
      className="project-card"
      to={"/projects/" + encodeURIComponent(task.id)}
      style={{ "--i": index } as CSSProperties}
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
            <i style={{ background: status.tone === "error" ? "var(--red)" : "var(--green)" }} />
            {status.label}
          </span>
        </div>
        <h3>{title}</h3>
        <p>{task.prompt}</p>
        <div className="project-card-foot">
          <span>{revisionLabel(task)}</span>
          <span>{info.short}</span>
        </div>
      </div>
    </Link>
  );
}
