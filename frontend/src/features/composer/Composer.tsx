import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { ApiError, api } from "../../api/client";
import type { Capability, CreateProjectResponse, Task } from "../../api/types";
import { useToast } from "../../layout/ToastProvider";

interface ComposerProps {
  capabilities: Capability[];
  onCreated: (task: Task) => void;
}

export function Composer({ capabilities, onCreated }: ComposerProps) {
  const { showToast } = useToast();
  const formRef = useRef<HTMLFormElement>(null);
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const [capability, setCapability] = useState<string | null>(null);
  const [templatePrompt, setTemplatePrompt] = useState("");
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const selected = capability
    ? capabilities.find((item) => item.key === capability) ?? null
    : null;
  const templateUnchanged = selected !== null && prompt.trim() === templatePrompt.trim();

  const note = !selected
    ? "选择一个模板，专用提示词会自动填入；也可以直接描述你的想法。"
    : templateUnchanged
      ? selected.label + " · 已填入专用提示词，可直接生成或修改"
      : "已修改模板提示词，提交时会根据内容自动识别能力。";

  function chooseTemplate(item: Capability) {
    setCapability(item.key);
    setTemplatePrompt(item.prompt);
    setPrompt(item.prompt);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = prompt.trim();
    if (!text) {
      showToast("先写一句你想做的东西");
      promptRef.current?.focus();
      return;
    }
    if (submitting) return;

    const requestedCapability = templateUnchanged ? capability : null;

    setSubmitting(true);
    setError("");
    try {
      const data = await api<CreateProjectResponse>("/api/projects", {
        method: "POST",
        body: JSON.stringify({
          prompt: text,
          capability: requestedCapability,
        }),
      });
      onCreated(data.task);
    } catch (reason) {
      const message = reason instanceof ApiError ? reason.message : "任务创建失败";
      setError(message);
      showToast("任务创建失败：" + message);
    } finally {
      setSubmitting(false);
    }
  }

  function handlePromptKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  return (
    <>
      <form className="composer" ref={formRef} onSubmit={handleSubmit}>
        <div className="composer-head">
          <div className="picker-wrap">
            <span className="picker-label">模板</span>
            <div className="cap-picker" role="group" aria-label="模板选择">
              {capabilities.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={item.key === capability ? "cap-chip active" : "cap-chip"}
                  aria-pressed={item.key === capability}
                  onClick={() => chooseTemplate(item)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
          <div className="composer-meta">
            <span className="auto-pill">可直接修改</span>
          </div>
        </div>
        <textarea
          ref={promptRef}
          rows={3}
          maxLength={2000}
          placeholder="选一个模板会填入专用提示词，也可以直接描述你想做的东西…"
          value={prompt}
          onChange={(event) => {
            setPrompt(event.target.value);
            setError("");
          }}
          onKeyDown={handlePromptKeyDown}
        />
        <div className="composer-foot">
          <div className="composer-hint">
            <span className="kbd">⌘</span>
            <span className="kbd">↵</span> 发送 · 自动规划 / 写代码 / 自检 / 部署
          </div>
          <button className="run-btn" type="submit" disabled={submitting}>
            <span className="run-label">{submitting ? "生成中…" : "开始生成"}</span>
            <span className="run-arrow">↗</span>
          </button>
        </div>
      </form>
      <div className={templateUnchanged ? "template-note active" : "template-note"}>
        {note}
      </div>
      {error ? (
        <div className="composer-error" role="alert">
          {error}
        </div>
      ) : null}
    </>
  );
}
