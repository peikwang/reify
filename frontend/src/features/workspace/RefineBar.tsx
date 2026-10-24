import { useState, type FormEvent } from "react";

import { api } from "../../api/client";
import type { Task } from "../../api/types";
import { useToast } from "../../layout/ToastProvider";

interface RefineBarProps {
  task: Task;
  running: boolean;
  onStarted: (task: Task) => void;
}

function hintFor(task: Task, running: boolean): string {
  if (running) return "Agent 正在处理，请稍候…";
  if (task.stack === "next") return "基于当前源码继续修改（会重新构建并切换运行时）";
  if (task.stack === "react") return "基于当前源码继续修改（会重新构建并部署）";
  return "基于当前成果继续修改";
}

export function RefineBar({ task, running, onStarted }: RefineBarProps) {
  const { showToast } = useToast();
  const [instruction, setInstruction] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const disabled = running || submitting;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = instruction.trim();
    if (!value || disabled) return;
    setSubmitting(true);
    try {
      const data = await api<{ task: Task }>(
        "/api/projects/" + encodeURIComponent(task.id) + "/refine",
        {
          method: "POST",
          body: JSON.stringify({ instruction: value }),
        },
      );
      setInstruction("");
      onStarted(data.task);
      showToast("修改已提交，Agent 开始处理");
    } catch (reason) {
      showToast(
        "修改提交失败：" + (reason instanceof Error ? reason.message : "未知错误"),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className={disabled ? "refine-form disabled" : "refine-form"} onSubmit={submit}>
      <div className="refine-head">
        <span>CONTINUE</span>
        <span>{hintFor(task, running)}</span>
      </div>
      <div className="refine-row">
        <input
          aria-label="修改指令"
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
          placeholder="继续描述要调整的内容…"
          disabled={disabled}
          maxLength={500}
        />
        <button type="submit" disabled={disabled}>
          发送修改
        </button>
      </div>
    </form>
  );
}
