import { Link } from "react-router-dom";

export function AdminPage() {
  return (
    <section className="projects-view view-enter">
      <header className="projects-hero">
        <div className="eyebrow">
          <span className="pulse-dot" />
          ADMIN / LOCAL
        </div>
        <h1>
          用户与
          <br />
          <span className="gradient-text">审计。</span>
        </h1>
        <p>管理员用户表、禁用/下线与审计日志将在 Phase 4 接入。</p>
      </header>
      <div className="empty-state">
        管理员脚手架已就绪。<Link to="/">回到工作台 →</Link>
      </div>
    </section>
  );
}
