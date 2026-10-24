import { Link } from "react-router-dom";

export function ProjectsPage() {
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
        <p>项目卡片、筛选与统计将在 Phase 1 接入。</p>
      </header>
      <div className="empty-state">
        项目库脚手架已就绪。<Link to="/">回到工作台 →</Link>
      </div>
    </section>
  );
}
