import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import type { Capability, Task } from "../api/types";
import { Composer } from "../features/composer/Composer";
import { TemplateGallery } from "../features/composer/TemplateGallery";
import { ProjectGrid } from "../features/project-library/ProjectGrid";
import { useCapabilities } from "../hooks/useCapabilities";
import { useProjects } from "../hooks/useProjects";
import { useToast } from "../layout/ToastProvider";

export function HomePage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { capabilities, error: capabilitiesError } = useCapabilities();
  const { items, loading, error: projectsError, reload } = useProjects();
  const [prompt, setPrompt] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<Capability | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recent = items.slice(0, 6);

  const activeTemplateKey =
    selectedTemplate && prompt.trim() === selectedTemplate.prompt.trim()
      ? selectedTemplate.key
      : null;

  function handleSelectTemplate(capability: Capability) {
    setSelectedTemplate(capability);
    setPrompt(capability.prompt);
    window.requestAnimationFrame(() => {
      const input = textareaRef.current;
      if (!input) return;
      input.focus({ preventScroll: true });
      input.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  function handleCreated(task: Task) {
    showToast("项目已创建，Agent 开始生成");
    navigate("/projects/" + task.id);
  }

  const recentCount = loading
    ? "加载中…"
    : items.length
      ? recent.length + " / " + items.length + " 个项目"
      : "还没有项目";
  const recentEmpty = loading
    ? "正在加载项目…"
    : projectsError
      ? "项目加载失败，请刷新重试。"
      : "还没有项目。从上面的一句话开始。";

  return (
    <section className="home-view view-enter">
      <div className="hero">
        <div className="hero-grid">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="pulse-dot" />
              REIFY / IDEA → REALITY
            </div>
            <h1>
              一句话，
              <br />
              <span className="gradient-text">从想法到上线。</span>
            </h1>
            <p className="hero-sub">
              从模板库找一个起点，或者直接描述你的想法。Agent 会规划、写代码、自检，并把成果部署成属于你的项目页面。
            </p>
          </div>

          <aside className="hero-showcase" aria-hidden="true">
            <div className="showcase-stage">
              <div className="show-card show-small">
                <div className="show-card-top">
                  <span className="show-dots">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span>CV / 03</span>
                </div>
                <div className="show-cover cover-resume">
                  <span className="cover-serif">林知夏</span>
                  <span className="cover-rule" />
                  <span className="cover-rule short" />
                </div>
                <div className="show-meta">PERSONAL RESUME</div>
              </div>
              <div className="show-card show-back">
                <div className="show-card-top">
                  <span className="show-dots">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span>GAME / 02</span>
                </div>
                <div className="show-cover cover-game">
                  <span className="cover-neon" />
                  <span className="cover-big">PLAY</span>
                </div>
                <div className="show-meta">NEON SNAKE · PLAYABLE</div>
              </div>
              <div className="show-card show-main">
                <div className="show-card-top">
                  <span className="show-dots">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span>WEB / 01</span>
                </div>
                <div className="show-cover cover-website">
                  <span className="cover-kicker">INDEPENDENT STUDIO</span>
                  <span className="cover-serif">
                    Make
                    <br />
                    it real.
                  </span>
                  <span className="cover-orb" />
                </div>
                <div className="show-lines">
                  <i />
                  <i />
                  <i className="short" />
                </div>
                <div className="show-meta">LUMEN STUDIO · LIVE</div>
              </div>
            </div>
            <div className="showcase-caption">
              <span className="live-dot" /> 每个项目，都是一个独立页面
            </div>
          </aside>
        </div>

        <div className="hero-composer">
          <Composer
            prompt={prompt}
            onPromptChange={setPrompt}
            selectedTemplate={selectedTemplate}
            onCreated={handleCreated}
            textareaRef={textareaRef}
          />
          {capabilitiesError ? (
            <div className="composer-error" role="alert">
              能力加载失败：{capabilitiesError}
            </div>
          ) : null}
        </div>
      </div>

      <TemplateGallery
        capabilities={capabilities}
        activeKey={activeTemplateKey}
        onSelect={handleSelectTemplate}
      />

      <section className="recent-section">
        <div className="section-label">
          <span>RECENT PROJECTS</span>
          <div className="section-actions">
            <b>{recentCount}</b>
            <Link to="/projects" className="section-link">
              全部项目 →
            </Link>
          </div>
        </div>
        <ProjectGrid
          items={recent}
          capabilities={capabilities}
          empty={recentEmpty}
          onMutated={reload}
        />
      </section>

      <footer className="home-footer">
        <span>REIFY / RUNS ON YOUR AGENT SERVER</span>
        <span>LOCAL PROJECTS · CODE SNAPSHOTS · AUTO DEPLOY</span>
      </footer>
    </section>
  );
}
