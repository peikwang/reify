import { useState } from "react";
import { Link } from "react-router-dom";

import { ProjectGrid } from "../features/project-library/ProjectGrid";
import {
  buildCapabilityFilters,
  filterProjects,
  projectStats,
} from "../features/project-library/projectView";
import { useCapabilities } from "../hooks/useCapabilities";
import { useProjects } from "../hooks/useProjects";

export function ProjectsPage() {
  const { capabilities } = useCapabilities();
  const { items, loading, error, reload } = useProjects();
  const [filter, setFilter] = useState("all");

  const stats = projectStats(items);
  const filters = buildCapabilityFilters(items, capabilities);
  const effectiveFilter = filters.some((item) => item.key === filter)
    ? filter
    : "all";
  const visible = filterProjects(items, effectiveFilter);

  return (
    <section className="projects-view view-enter">
      <header className="projects-hero">
        <div className="eyebrow">
          <span className="pulse-dot" />
          PROJECT LIBRARY / LOCAL
        </div>
        <h1>
          每个想法，
          <br />
          <span className="gradient-text">都有自己的页面。</span>
        </h1>
        <p>
          项目会保留每次生成、每次修改和最终部署地址。打开一个项目，继续看过程或直接对话修改。
        </p>
      </header>

      <div className="project-stats">
        <span className="stat-pill">
          <b>{stats.total}</b> 个项目
        </span>
        <span className="stat-pill">
          <b>{stats.deployed}</b> 已部署
        </span>
        <span className="stat-pill">
          <b>{stats.revisions}</b> 次修改
        </span>
      </div>

      <div className="project-toolbar">
        <div className="filter-row">
          {filters.map((item) => (
            <button
              key={item.key}
              type="button"
              className={
                item.key === effectiveFilter ? "filter-chip active" : "filter-chip"
              }
              aria-pressed={item.key === effectiveFilter}
              onClick={() => setFilter(item.key)}
            >
              {item.label} · {item.count}
            </button>
          ))}
        </div>
        <Link className="primary-pill" to="/">
          ＋ 新建项目
        </Link>
      </div>

      {error ? (
        <div className="empty-state">
          {error}
          <button className="filter-chip" type="button" onClick={() => void reload()}>
            重试
          </button>
        </div>
      ) : (
        <ProjectGrid
          items={visible}
          capabilities={capabilities}
          empty={loading ? "正在加载项目…" : "还没有项目。回到工作台开始第一个。"}
          className="full"
        />
      )}

      <footer className="home-footer">
        <span>VIBEFORGE / PROJECT LIBRARY</span>
        <span>EACH PROJECT HAS ITS OWN PAGE</span>
      </footer>
    </section>
  );
}
