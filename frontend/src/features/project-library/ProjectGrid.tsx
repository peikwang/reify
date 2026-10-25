import type { Capability, Task } from "../../api/types";
import { ProjectCard } from "./ProjectCard";

interface ProjectGridProps {
  items: Task[];
  capabilities: Capability[];
  empty: string;
  className?: string;
  onMutated?: () => void | Promise<void>;
}

export function ProjectGrid({
  items,
  capabilities,
  empty,
  className = "",
  onMutated,
}: ProjectGridProps) {
  if (!items.length) {
    return <div className="empty-state">{empty}</div>;
  }
  return (
    <div className={className ? "project-grid " + className : "project-grid"}>
      {items.map((task, index) => (
        <ProjectCard
          key={task.id}
          task={task}
          index={index}
          capabilities={capabilities}
          onMutated={onMutated}
        />
      ))}
    </div>
  );
}
