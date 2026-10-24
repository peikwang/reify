import type { Task, TaskCheck } from "../../api/types";
import { previewSandbox } from "./ssrPreview";

interface DailyOutputProps {
  task: Task;
  outcomeTitle: string;
  outcomeText: string;
  checks: TaskCheck[];
  running: boolean;
  previewUrl: string | null;
  previewMessage: string;
}

export function DailyOutput({
  task,
  outcomeTitle,
  outcomeText,
  checks,
  running,
  previewUrl,
  previewMessage,
}: DailyOutputProps) {
  const displayUrl =
    previewUrl ||
    (task.stack === "next" ? "APP RUNTIME" : task.url);

  return (
    <div className="daily-view">
      <div className="outcome-card">
        <div className="outcome-copy">
          <span className="outcome-kicker">PROJECT OUTPUT</span>
          <h2>{outcomeTitle}</h2>
          <p>{outcomeText}</p>
        </div>
        <div className="outcome-checks">
          {checks.length ? (
            checks.map((check) => (
              <div
                className={check.ok ? "check-item" : "check-item fail"}
                key={check.name}
                title={check.detail}
              >
                <i />
                {check.name}
              </div>
            ))
          ) : running ? (
            <>
              <div className="check-skeleton" />
              <div className="check-skeleton" />
              <div className="check-skeleton" />
            </>
          ) : null}
        </div>
      </div>
      <div className="browser-frame">
        <div className="browser-bar">
          <div className="browser-dots">
            <i />
            <i />
            <i />
          </div>
          <div className="browser-url">{displayUrl}</div>
          <div className="browser-tag">
            {task.stack === "next" ? "APP" : "LOCAL"}
          </div>
        </div>
        <div className="preview-stage">
          {previewUrl ? (
            <iframe
              title="生成结果预览"
              src={previewUrl}
              sandbox={previewSandbox(task.stack)}
            />
          ) : (
            <div className="preview-empty">
              <div className="loader" />
              <span>{previewMessage}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
