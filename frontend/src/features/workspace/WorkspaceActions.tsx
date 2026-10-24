import { useEffect, useState } from "react";

import { api } from "../../api/client";
import type { RuntimeState, Task } from "../../api/types";
import { useToast } from "../../layout/ToastProvider";
import { absolutePublicUrl } from "../project-library/publicLink";

interface WorkspaceActionsProps {
  task: Task;
  running: boolean;
  runtime: RuntimeState | null;
  onTaskChange: (task: Task) => void;
  onRuntimeChange: (runtime: RuntimeState) => void;
}

function runtimeLabel(runtime: RuntimeState | null): string {
  const status = runtime?.status ?? "stopped";
  if (status === "running") return "APP RUNNING";
  if (status === "starting") return "APP STARTING";
  if (status === "error") return "APP ERROR";
  return "APP STOPPED";
}

export function WorkspaceActions({
  task,
  running,
  runtime,
  onTaskChange,
  onRuntimeChange,
}: WorkspaceActionsProps) {
  const { showToast } = useToast();
  const [busy, setBusy] = useState<"deploy" | "share" | "runtime" | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(task.share_url);
  const isNext = task.stack === "next";

  useEffect(() => {
    setShareUrl(task.share_url);
  }, [task.share_url]);

  async function copyPublicLink() {
    if (!shareUrl) return;
    const absolute = absolutePublicUrl(shareUrl, window.location.origin);
    try {
      await navigator.clipboard.writeText(absolute);
      showToast("公开链接已复制");
    } catch {
      showToast("复制失败，请手动复制链接");
    }
  }

  async function deploy() {
    setBusy("deploy");
    try {
      const data = await api<{ ok: boolean; url: string }>(
        "/api/projects/" + encodeURIComponent(task.id) + "/deploy",
        { method: "POST" },
      );
      onTaskChange({ ...task, url: data.url, status: "done" });
      showToast("项目已重新部署");
    } catch (reason) {
      showToast(
        "部署失败：" + (reason instanceof Error ? reason.message : "未知错误"),
      );
    } finally {
      setBusy(null);
    }
  }

  async function toggleShare() {
    setBusy("share");
    try {
      if (shareUrl) {
        await api("/api/projects/" + encodeURIComponent(task.id) + "/share", {
          method: "DELETE",
        });
        setShareUrl(null);
        onTaskChange({ ...task, shared: false, share_url: null });
        showToast("已关闭分享");
      } else {
        const data = await api<{ ok: boolean; url: string }>(
          "/api/projects/" + encodeURIComponent(task.id) + "/share",
          { method: "POST" },
        );
        setShareUrl(data.url);
        onTaskChange({ ...task, shared: true, share_url: data.url });
        const absolute = absolutePublicUrl(data.url, window.location.origin);
        try {
          await navigator.clipboard.writeText(absolute);
          showToast("分享链接已复制");
        } catch {
          showToast("分享已开启，请复制公开链接");
        }
      }
    } catch (reason) {
      showToast(
        "分享操作失败：" + (reason instanceof Error ? reason.message : "未知错误"),
      );
    } finally {
      setBusy(null);
    }
  }

  async function toggleRuntime() {
    const status = runtime?.status ?? "stopped";
    const action = status === "running" ? "stop" : "start";
    setBusy("runtime");
    try {
      const data = await api<{ ok: boolean; runtime: RuntimeState }>(
        "/api/projects/" + encodeURIComponent(task.id) + "/runtime/" + action,
        { method: "POST" },
      );
      onRuntimeChange(data.runtime);
      showToast(
        data.runtime.status === "running" ? "应用运行时已启动" : "应用运行时已停止",
      );
    } catch (reason) {
      showToast(
        "应用操作失败：" + (reason instanceof Error ? reason.message : "未知错误"),
      );
    } finally {
      setBusy(null);
    }
  }

  const runtimeStatus = runtime?.status ?? "stopped";
  const runtimeBusy = busy === "runtime" || runtimeStatus === "starting";

  return (
    <>
      {shareUrl ? (
        <>
          <a
            className="ghost-btn"
            href={shareUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            公开页 ↗
          </a>
          <button className="ghost-btn" type="button" onClick={() => void copyPublicLink()}>
            复制链接
          </button>
        </>
      ) : null}
      {isNext ? (
        <>
          <span
            className={
              runtimeStatus === "running"
                ? "runtime-state on"
                : runtimeStatus === "error"
                  ? "runtime-state error"
                  : "runtime-state"
            }
          >
            <i />
            {runtimeLabel(runtime)}
          </span>
          <button
            className="ghost-btn"
            type="button"
            disabled={running || runtimeBusy}
            onClick={() => void toggleRuntime()}
          >
            {runtimeStatus === "running"
              ? "停止应用"
              : runtimeStatus === "starting"
                ? "启动中…"
                : runtimeStatus === "error"
                  ? "重试启动"
                  : "启动应用"}
          </button>
        </>
      ) : (
        <>
          <button
            className="ghost-btn"
            type="button"
            disabled={running || busy !== null}
            onClick={() => void deploy()}
          >
            {busy === "deploy" ? "部署中…" : "重新部署"}
          </button>
          <button
            className="ghost-btn"
            type="button"
            disabled={running || busy !== null}
            onClick={() => void toggleShare()}
          >
            {busy === "share" ? "处理中…" : shareUrl ? "取消分享" : "分享"}
          </button>
        </>
      )}
      <a
        className="ghost-btn"
        href={"/api/projects/" + encodeURIComponent(task.id) + "/bundle"}
        download
      >
        导出源码
      </a>
    </>
  );
}
