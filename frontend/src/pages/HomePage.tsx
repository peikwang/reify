import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <section className="home-view view-enter">
      <div className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="pulse-dot" />
            VIBEFORGE / PERSONAL DESIGN AGENT
          </div>
          <h1>
            一句话，
            <br />
            <span className="gradient-text">从想法到上线。</span>
          </h1>
          <p className="hero-sub">
            选一个模板，或者直接描述你的想法。Agent 会规划、写代码、自检，并把成果部署成属于你的项目页面。
          </p>
          <div className="empty-state">
            React 工作台脚手架已就绪，Composer 与最近项目将在 Phase 1 接入。
          </div>
          <div className="template-note active">
            <Link to="/projects">先看看项目库 →</Link>
          </div>
        </div>
      </div>
    </section>
  );
}
