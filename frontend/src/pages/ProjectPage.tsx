import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, api } from "../api/client";
import type {
  ProjectDetailResponse,
  RuntimeResponse,
  RuntimeState,
  Task,
  TaskEvent,
} from "../api/types";
import { capabilityInfo } from "../features/project-library/projectView";
import { CodingPane } from "../features/workspace/CodingPane";
import { DailyOutput } from "../features/workspace/DailyOutput";
import {
  applyProjectEvent,
  initialProjectView,
  projectPageStatus,
  type ProjectViewState,
  type TimelineItem,
} from "../features/workspace/eventView";
import { RefineBar } from "../features/workspace/RefineBar";
import { buildSsrPreviewUrl } from "../features/workspace/ssrPreview";
import { WorkspaceActions } from "../features/workspace/WorkspaceActions";
import { useCapabilities } from "../hooks/useCapabilities";
import { useTaskStream, type StreamConnection } from "../hooks/useTaskStream";
import { useToast } from "../layout/ToastProvider";

type ViewAction = { type: "reset" } | { type: "event"; event: TaskEvent };
type ViewMode = "daily" | "coding";

function viewReducer(
  state: ProjectViewState,
  action: ViewAction,
): ProjectViewState {
  if (action.type === "reset") return initialProjectView;
  return applyProjectEvent(state, action.event);
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString("zh-CN", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function connectionLabel(connection: StreamConnection): {
  text: string;
  className: string;
} {
  if (connection === "streaming") return { text: "STREAMING", className: "live" };
  if (connection === "reconnecting") return { text: "RECONNECTING", className: "error" };
  if (connection === "connecting") return { text: "CONNECTING", className: "" };
  if (connection === "error") return { text: "OFFLINE", className: "error" };
  return { text: "LOCAL", className: "" };
}

function TimelineRow({ item }: { item: TimelineItem }) {
  const chipClass =
    item.chipTone === "fail"
      ? "tl-verify fail"
      : item.chipTone === "tool"
        ? "tl-tool"
        : "tl-verify";
  return (
    <div className={"tl-item " + item.kind}>
      <div className="tl-head">
        <span className="tl-title">{item.title}</span>
        <span className="tl-time">{formatTime(item.ts)}</span>
      </div>
      <div className="tl-summary">{item.summary}</div>
      {item.detail ? <div className="tl-summary tl-detail">{item.detail}</div> : null}
      {item.chip ? <span className={chipClass}>{item.chip}</span> : null}
    </div>
  );
}

export function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { capabilities, ssrPreview, ssrPort } = useCapabilities();
  const [task, setTask] = useState<Task | null>(null);
  const [runtime, setRuntime] = useState<RuntimeState | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialSeq, setInitialSeq] = useState(0);
  const [mode, setMode] = useState<ViewMode>(() => {
    try {
      return localStorage.getItem("vf-react-mode") === "coding" ? "coding" : "daily";
    } catch {
      return "daily";
    }
  });
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [view, dispatch] = useReducer(viewReducer, initialProjectView);
  const timelineRef = useRef<HTMLDivElement>(null);
  const replayTimerRef = useRef<number | null>(null);
  const eventsRef = useRef<TaskEvent[]>([]);

  const files = useMemo(
    () =>
      Object.values(view.files).sort((a, b) => {
        if (a.path === "index.html") return -1;
        if (b.path === "index.html") return 1;
        return a.path.localeCompare(b.path);
      }),
    [view.files],
  );
  const activeFile = selectedFile ? view.files[selectedFile] ?? null : null;

  const refreshRuntime = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api<RuntimeResponse>(
        "/api/projects/" + encodeURIComponent(id) + "/runtime",
      );
      setRuntime(data.runtime);
    } catch {
      // A Next project without a runtime record is still a valid built project.
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    eventsRef.current = [];
    setLoaded(false);
    setError(null);
    setTask(null);
    setRuntime(null);
    setInitialSeq(0);
    setSelectedFile(null);
    setReplaying(false);
    dispatch({ type: "reset" });

    api<ProjectDetailResponse>("/api/projects/" + encodeURIComponent(id ?? ""))
      .then((data) => {
        if (!active) return;
        setTask(data.task);
        eventsRef.current = [...data.events].sort((a, b) => a.seq - b.seq);
        const lastSeq = data.events.reduce(
          (max, event) => Math.max(max, event.seq),
          0,
        );
        setInitialSeq(lastSeq);
        for (const event of data.events) {
          dispatch({ type: "event", event });
        }
        setLoaded(true);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "项目加载失败");
        setLoaded(true);
      });

    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    if (!files.length) {
      if (selectedFile) setSelectedFile(null);
      return;
    }
    if (selectedFile && view.files[selectedFile]) return;
    setSelectedFile(view.files["index.html"] ? "index.html" : files[0]?.path ?? null);
  }, [files, view.files, selectedFile]);

  useEffect(
    () => () => {
      if (replayTimerRef.current !== null) {
        window.clearTimeout(replayTimerRef.current);
        replayTimerRef.current = null;
      }
    },
    [id],
  );

  useEffect(() => {
    if (task?.stack === "next") void refreshRuntime();
  }, [task?.stack, refreshRuntime]);

  useEffect(() => {
    if (!id || !view.terminal) return;
    if (!task || !["queued", "running", "deploying"].includes(task.status)) return;
    let active = true;
    const terminal = view.terminal;
    api<ProjectDetailResponse>("/api/projects/" + encodeURIComponent(id))
      .then((data) => {
        if (active) setTask(data.task);
      })
      .catch(() => {
        if (!active) return;
        setTask((current) =>
          current
            ? {
                ...current,
                status:
                  terminal === "done"
                    ? "done"
                    : terminal === "interrupted"
                      ? "interrupted"
                      : "error",
              }
            : current,
        );
      });
    return () => {
      active = false;
    };
  }, [id, view.terminal, task?.status]);

  const handleEvent = useCallback(
    (event: TaskEvent) => {
      if (!eventsRef.current.some((item) => item.seq === event.seq)) {
        eventsRef.current.push(event);
      }
      dispatch({ type: "event", event });
      if (event.type.startsWith("runtime_") && task?.stack === "next") {
        void refreshRuntime();
      }
    },
    [task?.stack, refreshRuntime],
  );

  const running = Boolean(
    task &&
      ["queued", "running", "deploying"].includes(task.status) &&
      view.terminal === null,
  );
  const streamEnabled = Boolean(task && running);
  const connection = useTaskStream(
    task?.id,
    initialSeq,
    handleEvent,
    streamEnabled,
  );

  useEffect(() => {
    const element = timelineRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [view.timeline.length]);

  if (!loaded) {
    return (
      <div className="auth-loading">
        <div className="loader" />
        <span>LOADING PROJECT</span>
      </div>
    );
  }

  if (error || !task) {
    return (
      <section className="projects-view view-enter">
        <div className="empty-state">
          项目加载失败：{error || "project not found"}。
          <Link to="/projects">返回项目库 →</Link>
        </div>
      </section>
    );
  }

  const info = capabilityInfo(task.capability, capabilities);
  const status = projectPageStatus(task, view, runtime);
  const connectionView = connectionLabel(connection);
  const staticReady =
    task.stack !== "next" &&
    (view.previewReady || task.status === "done" || task.status === "deploying");
  const runtimeReady = task.stack === "next" && runtime?.status === "running";
  const ssrPreviewUrl = runtimeReady
    ? buildSsrPreviewUrl(
        runtime?.url || "/apps/" + encodeURIComponent(task.id) + "/",
        ssrPreview,
        ssrPort,
        window.location.origin,
      )
    : null;
  const previewUrl =
    task.stack === "next" ? ssrPreviewUrl : staticReady ? task.url : null;
  const previewMessage = previewUrl
    ? ""
    : task.stack === "next" && (task.status === "done" || view.terminal === "done")
      ? runtimeReady
        ? "应用正在运行；当前部署未开放 12889 预览入口。"
        : "应用运行时未启动；点击顶部「启动应用」。"
      : view.terminal === "error" || task.status === "error"
        ? "生成失败，暂无预览。"
        : "AGENT IS BUILDING";
  const flowTitle =
    view.currentStep !== null && view.plan[view.currentStep]
      ? view.plan[view.currentStep]
      : view.terminal === "done" || task.status === "done"
        ? "交付完成"
        : view.terminal === "error" || task.status === "error"
          ? "生成失败"
          : "正在拆解任务";
  const outcomeTitle = view.outcome?.title || task.title || "正在生成…";
  const outcomeText =
    view.outcome?.text ||
    task.error ||
    (running
      ? "Agent 正在规划、写文件并验证结果。"
      : "等待 Agent 输出…");

  async function copyCode() {
    if (!activeFile) return;
    try {
      await navigator.clipboard.writeText(activeFile.content);
      showToast("代码已复制");
    } catch {
      showToast("复制失败，请手动复制");
    }
  }

  function openPreview() {
    if (previewUrl) window.open(previewUrl, "_blank", "noopener,noreferrer");
  }

  async function deleteProject() {
    if (!task || running || deleting) return;
    if (!window.confirm("删除当前项目？源码、产物、事件和公开链接都会被永久删除。")) {
      return;
    }
    setDeleting(true);
    try {
      await api("/api/projects/" + encodeURIComponent(task.id), { method: "DELETE" });
      showToast("项目已删除");
      navigate("/projects", { replace: true });
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 404) {
        showToast("项目已删除");
        navigate("/projects", { replace: true });
      } else {
        showToast(
          "删除失败：" + (reason instanceof Error ? reason.message : "未知错误"),
        );
      }
    } finally {
      setDeleting(false);
    }
  }

  function handleRefineStarted(updated: Task) {
    const lastSeq = eventsRef.current.reduce(
      (max, event) => Math.max(max, event.seq),
      0,
    );
    if (replayTimerRef.current !== null) {
      window.clearTimeout(replayTimerRef.current);
      replayTimerRef.current = null;
    }
    eventsRef.current = [];
    setReplaying(false);
    dispatch({ type: "reset" });
    setInitialSeq(lastSeq);
    setSelectedFile(null);
    setTask(updated);
  }

  function changeMode(next: ViewMode) {
    setMode(next);
    try {
      localStorage.setItem("vf-react-mode", next);
    } catch {
      // Private browsing may reject storage; the in-memory mode still works.
    }
  }

  function replay() {
    if (running || replaying) return;
    const events = [...eventsRef.current].sort((a, b) => a.seq - b.seq);
    if (!events.length) return;
    if (replayTimerRef.current !== null) {
      window.clearTimeout(replayTimerRef.current);
      replayTimerRef.current = null;
    }
    setReplaying(true);
    dispatch({ type: "reset" });
    let index = 0;
    const step = () => {
      if (index >= events.length) {
        replayTimerRef.current = null;
        setReplaying(false);
        return;
      }
      dispatch({ type: "event", event: events[index] });
      index += 1;
      replayTimerRef.current = window.setTimeout(step, 18);
    };
    step();
  }

  const agentOrbClass = running
    ? "agent-orb running"
    : view.terminal === "done" || task.status === "done"
      ? "agent-orb done"
      : "agent-orb";

  return (
    <section className="workspace-view view-enter">
      <div className="workspace-head">
        <div className="task-identity">
          <button
            className="back-btn"
            type="button"
            title="返回项目库"
            aria-label="返回项目库"
            onClick={() => navigate("/projects")}
          >
            ←
          </button>
          <div>
            <div className="task-eyebrow">
              {info.short} / {task.id.toUpperCase()}
              {task.revision ? " / REV " + task.revision : ""}
            </div>
            <h2>{task.title || task.prompt || "未命名项目"}</h2>
          </div>
        </div>
        <div className="workspace-actions">
          <div
            className="mode-switch"
            data-mode={mode}
            role="tablist"
            aria-label="展示模式"
          >
            <span className="mode-slider" aria-hidden="true" />
            <button
              type="button"
              role="tab"
              aria-selected={mode === "daily"}
              className={mode === "daily" ? "mode-btn active" : "mode-btn"}
              onClick={() => changeMode("daily")}
            >
              交付
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "coding"}
              className={mode === "coding" ? "mode-btn active" : "mode-btn"}
              onClick={() => changeMode("coding")}
            >
              编程
            </button>
          </div>
          <div className={"conn " + connectionView.className}>
            <i />
            <span>{connectionView.text}</span>
          </div>
          <WorkspaceActions
            task={task}
            running={running}
            runtime={runtime}
            onTaskChange={setTask}
            onRuntimeChange={setRuntime}
          />
          <button
            className="ghost-btn danger-btn"
            type="button"
            disabled={running || deleting}
            onClick={() => void deleteProject()}
          >
            {deleting ? "删除中…" : "删除项目"}
          </button>
          <span className={"status-pill " + status.tone}>
            <i />
            <span>{status.label}</span>
          </span>
        </div>
      </div>

      <div className="workspace-grid">
        <aside className="flow-panel">
          <div className="flow-head">
            <div>
              <span className="panel-kicker">AGENT FLOW</span>
              <h3>{flowTitle}</h3>
            </div>
            <button
              className="mini-btn"
              type="button"
              onClick={replay}
              disabled={running || replaying || eventsRef.current.length === 0}
            >
              ↻ {replaying ? "重播中" : "重播"}
            </button>
          </div>
          <div className={agentOrbClass}>
            <span />
            <span />
            <span />
            <i />
          </div>
          <div className="plan-steps">
            {view.plan.length ? (
              view.plan.map((step, index) => (
                <div
                  className={
                    "plan-step " + (view.planStatus[index] || "pending")
                  }
                  key={index}
                  style={{ "--i": index } as CSSProperties}
                >
                  <span className="plan-index">0{index + 1}</span>
                  <span className="plan-name">{step}</span>
                  <span className="plan-state" />
                </div>
              ))
            ) : (
              <div className="empty-state small">等待 Agent 规划…</div>
            )}
          </div>
          <div className="timeline" ref={timelineRef}>
            {view.timeline.length ? (
              view.timeline.map((item) => <TimelineRow item={item} key={item.key} />)
            ) : (
              <div className="empty-state small">等待事件流…</div>
            )}
          </div>
          <div className="prompt-card">
            <b>YOUR PROMPT</b>
            {task.prompt}
          </div>
          {task.status === "done" ? (
            <RefineBar
              task={task}
              running={running}
              onStarted={handleRefineStarted}
            />
          ) : null}
        </aside>

        <section className="stage-panel">
          <div className="stage-head">
            <div className="stage-head-left">
              <span className="stage-dot" />
              <span>
                {mode === "coding"
                  ? "CODE CHANGES"
                  : task.stack === "next"
                    ? "APP OUTPUT"
                    : "DAILY OUTPUT"}
              </span>
            </div>
            <div className="stage-head-right">
              <span>
                {mode === "coding"
                  ? "GIT SNAPSHOT"
                  : previewUrl
                    ? task.stack === "next"
                      ? "APP PREVIEW"
                      : "LIVE PREVIEW"
                    : "WAITING"}
              </span>
              {previewUrl ? (
                <button className="mini-btn" type="button" onClick={openPreview}>
                  ↗ 新窗口
                </button>
              ) : null}
            </div>
          </div>
          <div className="stage-body">
            {mode === "coding" ? (
              <CodingPane
                task={task}
                files={files}
                selectedPath={selectedFile}
                onSelect={setSelectedFile}
                activeFile={activeFile}
                terminal={view.terminalLines}
                previewUrl={previewUrl}
                onCopy={() => void copyCode()}
              />
            ) : (
              <DailyOutput
                task={task}
                outcomeTitle={outcomeTitle}
                outcomeText={outcomeText}
                checks={view.checks}
                running={running}
                previewUrl={previewUrl}
                previewMessage={previewMessage}
              />
            )}
          </div>
        </section>
      </div>
    </section>
  );
}
