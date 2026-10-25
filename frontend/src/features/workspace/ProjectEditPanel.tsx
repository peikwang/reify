import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../../api/client";
import type { Task } from "../../api/types";
import { useToast } from "../../layout/ToastProvider";

interface ProjectEditPanelProps {
  task: Task;
  running: boolean;
  deleting: boolean;
  onTaskChange: (task: Task) => void;
  onDelete: () => void;
}

export function ProjectEditPanel({
  task,
  running,
  deleting,
  onTaskChange,
  onDelete,
}: ProjectEditPanelProps) {
  const { showToast } = useToast();
  const [title, setTitle] = useState(task.title);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [armed, setArmed] = useState(false);
  const disarmTimer = useRef<number | null>(null);

  useEffect(() => {
    setTitle(task.title);
    setError("");
    setArmed(false);
  }, [task.id, task.title]);

  useEffect(
    () => () => {
      if (disarmTimer.current !== null) window.clearTimeout(disarmTimer.current);
    },
    [],
  );

  async function saveTitle() {
    const clean = title.trim();
    if (!clean || clean === task.title || saving) return;
    setSaving(true);
    setError("");
    try {
      const data = await api<{ ok: boolean; task: Task }>(
        "/api/projects/" + encodeURIComponent(task.id),
        { method: "PATCH", body: JSON.stringify({ title: clean }) },
      );
      onTaskChange(data.task);
      showToast("项目名称已更新");
    } catch (reason) {
      const message = reason instanceof ApiError ? reason.message : "保存失败";
      setError(message);
      showToast("保存失败：" + message);
    } finally {
      setSaving(false);
    }
  }

  function handleDelete() {
    if (running) {
      showToast("任务运行中，完成后再删除");
      return;
    }
    if (!armed) {
      setArmed(true);
      if (disarmTimer.current !== null) window.clearTimeout(disarmTimer.current);
      disarmTimer.current = window.setTimeout(() => setArmed(false), 4000);
      return;
    }
    if (disarmTimer.current !== null) window.clearTimeout(disarmTimer.current);
    setArmed(false);
    onDelete();
  }

  return (
    <div className="edit-panel">
      <section className="edit-card">
        <p className="edit-kicker">PROJECT NAME</p>
        <h3>项目名称</h3>
        <p className="edit-hint">这个名字会显示在项目库、工作台和分享页面。</p>
        <form
          className="edit-form"
          onSubmit={(event) => {
            event.preventDefault();
            void saveTitle();
          }}
        >
          <label htmlFor="edit-title">名称</label>
          <input
            id="edit-title"
            value={title}
            maxLength={80}
            onChange={(event) => {
              setTitle(event.target.value);
              setError("");
            }}
          />
          <button
            className="primary-btn"
            type="submit"
            disabled={saving || !title.trim() || title.trim() === task.title}
          >
            {saving ? "保存中…" : "保存名称"}
          </button>
        </form>
        {error ? (
          <div className="edit-error" role="alert">
            {error}
          </div>
        ) : null}
      </section>

      <section className="edit-card">
        <p className="edit-kicker">PROJECT INFO</p>
        <h3>项目信息</h3>
        <dl className="edit-info">
          <div><dt>类型</dt><dd>{task.capability}</dd></div>
          <div><dt>技术栈</dt><dd>{task.stack}</dd></div>
          <div><dt>创建时间</dt><dd>{task.created_at.slice(0, 10)}</dd></div>
          <div><dt>修订</dt><dd>v{task.revision}</dd></div>
        </dl>
        <p className="edit-prompt">{task.prompt}</p>
      </section>

      <section className="edit-card danger-zone">
        <p className="edit-kicker">DANGER ZONE</p>
        <h3>删除项目</h3>
        <p className="edit-hint">
          会同时清理源码、产物、事件、运行时和公开链接，且无法恢复。
        </p>
        <button
          className="ghost-btn danger-btn"
          type="button"
          disabled={running || deleting}
          onClick={handleDelete}
        >
          {deleting
            ? "删除中…"
            : armed
              ? "再次点击确认删除"
              : "删除项目"}
        </button>
      </section>
    </div>
  );
}
