import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

import { ApiError, api } from "../../api/client";
import type { Task } from "../../api/types";
import { useToast } from "../../layout/ToastProvider";

interface ProjectCardMenuProps {
  task: Task;
  onMutated?: () => void | Promise<void>;
}

export function ProjectCardMenu({ task, onMutated }: ProjectCardMenuProps) {
  const { showToast } = useToast();
  const rootRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [title, setTitle] = useState(task.title);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  const running = ["queued", "running", "deploying"].includes(task.status);
  const displayTitle = task.title || task.prompt || "未命名项目";

  useEffect(() => {
    setTitle(task.title);
  }, [task.title]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    if (!renameOpen) return;
    const frame = window.requestAnimationFrame(() => {
      titleRef.current?.focus();
      titleRef.current?.select();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [renameOpen]);

  function openRename() {
    setOpen(false);
    setTitle(task.title || task.prompt || "");
    setError("");
    setRenameOpen(true);
  }

  function openDelete() {
    setOpen(false);
    if (running) {
      showToast("任务运行中，完成后再删除");
      return;
    }
    setError("");
    setDeleteOpen(true);
  }

  async function saveTitle() {
    const clean = title.trim();
    if (!clean || saving) return;
    setSaving(true);
    setError("");
    try {
      await api<{ ok: boolean; task: Task }>(
        "/api/projects/" + encodeURIComponent(task.id),
        { method: "PATCH", body: JSON.stringify({ title: clean }) },
      );
      showToast("项目名称已更新");
      setRenameOpen(false);
      await onMutated?.();
    } catch (reason) {
      const message = reason instanceof ApiError ? reason.message : "保存失败";
      setError(message);
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (deleting) return;
    setDeleting(true);
    setError("");
    try {
      await api("/api/projects/" + encodeURIComponent(task.id), {
        method: "DELETE",
      });
      showToast("项目已删除");
      setDeleteOpen(false);
      await onMutated?.();
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 404) {
        showToast("项目已删除");
        setDeleteOpen(false);
        await onMutated?.();
      } else {
        setError(reason instanceof Error ? reason.message : "删除失败");
      }
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="card-menu" ref={rootRef}>
      <button
        className="card-menu-trigger"
        type="button"
        aria-label={"更多操作 " + displayTitle}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span />
        <span />
        <span />
      </button>

      {open ? (
        <div className="card-menu-list" role="menu">
          <button
            className="card-menu-item"
            type="button"
            role="menuitem"
            onClick={openRename}
          >
            重命名
          </button>
          <Link
            className="card-menu-item"
            role="menuitem"
            to={"/projects/" + encodeURIComponent(task.id) + "?tab=edit"}
            onClick={() => setOpen(false)}
          >
            编辑详情
          </Link>
          <button
            className="card-menu-item danger"
            type="button"
            role="menuitem"
            disabled={running}
            title={running ? "任务运行中，完成后再删除" : undefined}
            onClick={openDelete}
          >
            删除项目
          </button>
        </div>
      ) : null}

      {renameOpen
        ? createPortal(
            <div
              className="naming-backdrop"
              onMouseDown={() => {
                if (!saving) setRenameOpen(false);
              }}
            >
          <form
            className="naming-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={"rename-heading-" + task.id}
            onSubmit={(event) => {
              event.preventDefault();
              void saveTitle();
            }}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <p className="naming-kicker">RENAME PROJECT</p>
            <h2 id={"rename-heading-" + task.id}>修改项目名称</h2>
            <p className="naming-sub">名称会同步到项目库、工作台和分享页面。</p>
            <label htmlFor={"rename-title-" + task.id}>项目名称</label>
            <input
              id={"rename-title-" + task.id}
              ref={titleRef}
              value={title}
              maxLength={80}
              required
              onChange={(event) => {
                setTitle(event.target.value);
                setError("");
              }}
            />
            {error ? (
              <div className="naming-error" role="alert">
                {error}
              </div>
            ) : null}
            <div className="naming-actions">
              <button
                type="button"
                className="ghost-btn"
                disabled={saving}
                onClick={() => setRenameOpen(false)}
              >
                取消
              </button>
              <button
                type="submit"
                className="run-btn"
                disabled={saving || !title.trim() || title.trim() === task.title}
              >
                <span className="run-label">{saving ? "保存中…" : "保存名称"}</span>
                <span className="run-arrow">↗</span>
              </button>
            </div>
            </form>
          </div>,
          document.body,
        )
      : null}

      {deleteOpen
        ? createPortal(
            <div
              className="naming-backdrop"
              onMouseDown={() => {
                if (!deleting) setDeleteOpen(false);
              }}
            >
          <div
            className="naming-dialog danger-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={"delete-heading-" + task.id}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <p className="naming-kicker">DELETE PROJECT</p>
            <h2 id={"delete-heading-" + task.id}>删除这个项目？</h2>
            <p className="naming-sub">
              「{displayTitle}」的源码、产物、事件、运行时和公开链接都会永久删除。
            </p>
            {error ? (
              <div className="naming-error" role="alert">
                {error}
              </div>
            ) : null}
            <div className="naming-actions">
              <button
                type="button"
                className="ghost-btn"
                disabled={deleting}
                onClick={() => setDeleteOpen(false)}
              >
                取消
              </button>
              <button
                type="button"
                className="danger-confirm"
                disabled={deleting}
                onClick={() => void confirmDelete()}
              >
                {deleting ? "删除中…" : "确认删除"}
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )
      : null}
    </div>
  );
}
