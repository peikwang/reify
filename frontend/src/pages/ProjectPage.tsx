import { Link, useParams } from "react-router-dom";

export function ProjectPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <section className="projects-view view-enter">
      <header className="projects-hero">
        <div className="eyebrow">
          <span className="pulse-dot" />
          PROJECT / {id ?? "--"}
        </div>
        <h1>
          项目工作区
          <br />
          <span className="gradient-text">即将到来。</span>
        </h1>
        <p>项目页只读视图与 SSE 事件流将在 Phase 2 接入。</p>
      </header>
      <div className="empty-state">
        当前项目 ID：{id ?? "未知"}。<Link to="/projects">返回项目库 →</Link>
      </div>
    </section>
  );
}
