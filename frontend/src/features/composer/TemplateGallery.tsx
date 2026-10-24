import type { CSSProperties } from "react";

import type { Capability } from "../../api/types";
import { TemplateArt } from "./TemplateArt";

interface TemplateGalleryProps {
  capabilities: Capability[];
  activeKey: string | null;
  onSelect: (capability: Capability) => void;
}

export function TemplateGallery({
  capabilities,
  activeKey,
  onSelect,
}: TemplateGalleryProps) {
  if (!capabilities.length) return null;

  return (
    <section className="template-library" aria-label="模板库">
      <div className="section-label">
        <span>TEMPLATE LIBRARY</span>
        <div className="section-actions">
          <b>从一个模板开始</b>
          <span className="template-hint">点击会填入输入框，可继续修改</span>
        </div>
      </div>
      <div className="template-grid">
        {capabilities.map((capability, index) => {
          const active = capability.key === activeKey;
          return (
            <button
              key={capability.key}
              type="button"
              className={active ? "template-card active" : "template-card"}
              aria-pressed={active}
              style={{ "--i": index } as CSSProperties}
              onClick={() => onSelect(capability)}
            >
              <span className="template-card-art">
                <TemplateArt capability={capability.key} />
              </span>
              <span className="template-card-body">
                <span className="template-card-head">
                  <b>{capability.label}</b>
                  <span>{capability.short}</span>
                </span>
                <span className="template-card-desc">{capability.description}</span>
                {active ? <span className="template-card-badge">已填入</span> : null}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
