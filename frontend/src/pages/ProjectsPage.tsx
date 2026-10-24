import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { absolutePublicUrl } from "../features/project-library/publicLink";
import { ProjectGrid } from "../features/project-library/ProjectGrid";
import {
  buildCapabilityFilters,
  filterProjects,
  projectStats,
} from "../features/project-library/projectView";
import { useCapabilities } from "../hooks/useCapabilities";
import { useProjects } from "../hooks/useProjects";
import { useToast } from "../layout/ToastProvider";

interface ProjectsLocationState {
  createdId?: string;
}

export function ProjectsPage() {
  const { capabilities } = useCapabilities();
  const { items, loading, error, reload } = useProjects();
  const [filter, setFilter] = useState("all");
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const createdId = (location.state as ProjectsLocationState | null)?.createdId;
  const created = createdId
    ? items.find((item) => item.id === createdId)
    : undefined;
  const createdRunning = created
    ? ["queued", "running", "deploying"].includes(created.status)
    : false;
  const createdUrl =
    created && created.status === "done" && created.share_url
      ? absolutePublicUrl(created.share_url, window.location.origin)
      : null;

  const stats = projectStats(items);
  const filters = buildCapabilityFilters(items, capabilities);
  const effectiveFilter = filters.some((item) => item.key === filter)
    ? filter
    : "all";
  const visible = filterProjects(items, effectiveFilter);

  function dismissCreated() {
    navigate(location.pathname, { replace: true, state: null });
  }

  async function copyCreatedLink() {
    if (!createdUrl) return;
    try {
      await navigator.clipboard.writeText(createdUrl);
      showToast("公开链接已复制");
    } catch {
      showToast("复制失败，请手动复制链接");
    }
  }

  function createdMessage(): string {
    if (!created) return "";
    if (createdUrl) return "公开链接已生成，持有链接的人无需登录即可打开。";
    if (createdRunning) return "正在生成；完成后项目卡片会出现免登录公开链接。";
    if (created.stack === "next") {
      return "应用运行时项目的免登录链接将在运行时阶段开放。";
    }
    return "项目生成未完成，暂无公开链接。";
  }

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

      {created ? (
        <div className="public-link-banner">
          <div className="public-link-copy">
            <span className="public-link-kicker">PROJECT CREATED</span>
            <strong>{created.title || "新项目"} 已创建</strong>
            <p>{createdMessage()}</p>
            {createdUrl ? <code>{createdUrl}</code> : null}
          </div>
          <div className="public-link-actions">
            {createdUrl ? (
              <>
                <a
                  className="primary-pill"
                  href={createdUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  打开公开页 ↗
                </a>
                <button
                  className="filter-chip"
                  type="button"
                  onClick={() => void copyCreatedLink()}
                >
                  复制链接
                </button>
              </>
            ) : createdRunning ? (
              <button
                className="filter-chip"
                type="button"
                onClick={() => void reload()}
              >
                刷新状态
              </button>
            ) : null}
            <button className="mini-btn" type="button" onClick={dismissCreated}>
              关闭
            </button>
          </div>
        </div>
      ) : null}

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
        <span>REIFY / PROJECT LIBRARY</span>
        <span>EACH PROJECT HAS ITS OWN PAGE</span>
      </footer>
    </section>
  );
}
