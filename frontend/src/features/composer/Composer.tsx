import {
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
} from "react";

import { ApiError, api } from "../../api/client";
import type { Capability, CreateProjectResponse, Task } from "../../api/types";
import { useToast } from "../../layout/ToastProvider";

interface ComposerProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  selectedTemplate: Capability | null;
  onCreated: (task: Task) => void;
  textareaRef?: RefObject<HTMLTextAreaElement | null>;
}

export function Composer({
  prompt,
  onPromptChange,
  selectedTemplate,
  onCreated,
  textareaRef,
}: ComposerProps) {
  const { showToast } = useToast();
  const formRef = useRef<HTMLFormElement>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const templateUnchanged =
    selectedTemplate !== null && prompt.trim() === selectedTemplate.prompt.trim();

  const note = !selectedTemplate
    ? "直接从一句话开始，或从下方模板库选择一个起点。"
    : templateUnchanged
      ? selectedTemplate.label + " · 已填入专用提示词，可直接发送或修改。"
      : "提示词已修改，提交时会根据内容自动识别模板。";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = prompt.trim();
    if (!text) {
      showToast("先写一句你想做的东西");
      textareaRef?.current?.focus();
      return;
    }
    if (submitting) return;

    setSubmitting(true);
    setError("");
    try {
      const data = await api<CreateProjectResponse>("/api/projects", {
        method: "POST",
        body: JSON.stringify({
          prompt: text,
          capability: templateUnchanged ? selectedTemplate.key : null,
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
      <form className="composer generic-composer" ref={formRef} onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          rows={4}
          maxLength={2000}
          aria-label="项目需求"
          placeholder="描述你想做的东西；也可以从下方模板库选择一个起点…"
          value={prompt}
          onChange={(event) => {
            onPromptChange(event.target.value);
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
