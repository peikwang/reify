import { useEffect, useMemo, useRef } from "react";

import type { Task } from "../../api/types";
import { computeLineDiff } from "./diff";
import type { FileSnapshot, TerminalLine } from "./eventView";
import { previewSandbox } from "./ssrPreview";

interface CodingPaneProps {
  task: Task;
  files: FileSnapshot[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  activeFile: FileSnapshot | null;
  terminal: TerminalLine[];
  previewUrl: string | null;
  onCopy: () => void;
}

function fileExt(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  return (
    {
      html: "<>",
      py: "PY",
      json: "{}",
      md: "MD",
      css: "#",
      js: "JS",
      jsx: "JSX",
      ts: "TS",
      tsx: "TSX",
    }[ext] || "·"
  );
}

export function CodingPane({
  task,
  files,
  selectedPath,
  onSelect,
  activeFile,
  terminal,
  previewUrl,
  onCopy,
}: CodingPaneProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const diff = useMemo(
    () =>
      activeFile
        ? computeLineDiff(activeFile.before, activeFile.after)
        : { lines: [], additions: 0, deletions: 0 },
    [activeFile],
  );

  useEffect(() => {
    const element = terminalRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [terminal.length]);

  return (
    <div className="coding-view">
      <div className="code-layout">
        <aside className="file-sidebar">
          <div className="sidebar-label">
            FILES <span>{files.length}</span>
          </div>
          <div className="file-tree">
            {files.length ? (
              files.map((file) => (
                <button
                  key={file.path}
                  type="button"
                  className={
                    "file-row" + (file.path === selectedPath ? " active" : "")
                  }
                  onClick={() => onSelect(file.path)}
                >
                  <span className="file-icon">{fileExt(file.path)}</span>
                  <span>{file.path}</span>
                  <span className="file-badge">
                    {file.created ? "NEW" : ""}
                  </span>
                </button>
              ))
            ) : (
              <div className="empty-state small">等待 Agent 写入文件…</div>
            )}
          </div>
          <div className="code-note">
            每个 Agent 步骤都会留下一次文件快照。选择文件查看 Diff。
          </div>
        </aside>

        <div className="diff-pane">
          <div className="diff-head">
            <div>
              <span id="diffPath">{activeFile?.path || "index.html"}</span>
              <small id="diffLanguage">
                {(activeFile?.language || "text").toUpperCase()}
              </small>
            </div>
            <div className="diff-tools">
              <span id="diffStats">
                +{diff.additions} −{diff.deletions}
              </span>
              {activeFile ? (
                <button className="mini-btn" type="button" onClick={onCopy}>
                  复制
                </button>
              ) : null}
            </div>
          </div>
          <div className="diff-scroll">
            {activeFile && diff.lines.length ? (
              diff.lines.map((line, index) => (
                <div
                  className={"diff-line " + line.type}
                  key={`${index}-${line.type}-${line.oldNo ?? ""}-${line.newNo ?? ""}`}
                >
                  <span className="ln">
                    {line.type === "add" ? line.newNo : line.oldNo}
                  </span>
                  <span className="sign">
                    {line.type === "add" ? "+" : line.type === "del" ? "−" : " "}
                  </span>
                  <span className="code">{line.line || " "}</span>
                </div>
              ))
            ) : (
              <div className="diff-empty">
                <div className="empty-icon">⌘</div>
                <b>代码会在这里逐行出现</b>
                <span>Agent 写入文件后，你可以看到每一次新增与修改。</span>
              </div>
            )}
          </div>
          <div className="terminal-pane">
            <div className="terminal-head">
              <span>TERMINAL</span>
              <span id="termStatus">{terminal.length > 1 ? "LOG" : "IDLE"}</span>
            </div>
            <div className="terminal-body" ref={terminalRef}>
              {terminal.map((line, index) => (
                <div
                  className={"term-line" + (line.kind ? " " + line.kind : "")}
                  key={`${index}-${line.text}`}
                >
                  {line.text || " "}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mini-preview">
          <div className="mini-head">
            <span>LIVE</span>
            <span id="miniState">{previewUrl ? "READY" : "WAITING"}</span>
          </div>
          {previewUrl ? (
            <iframe
              title="代码模式实时预览"
              src={previewUrl}
              sandbox={previewSandbox(task.stack)}
            />
          ) : (
            <div className="empty-state small">
              {task.stack === "next" ? "应用运行时未启动" : "预览将在页面就绪后出现"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
