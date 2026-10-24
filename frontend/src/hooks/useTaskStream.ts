import { useEffect, useRef, useState } from "react";

import { loginRedirectPath } from "../auth/nextPath";
import type { TaskEvent } from "../api/types";

export type StreamConnection =
  | "idle"
  | "connecting"
  | "streaming"
  | "reconnecting"
  | "closed"
  | "error";

const TERMINAL_EVENTS = new Set(["done", "error", "interrupted"]);
const RECONNECT_DELAY_MS = 1600;

export function useTaskStream(
  taskId: string | undefined,
  initialAfter: number,
  onEvent: (event: TaskEvent) => void,
  enabled: boolean,
): StreamConnection {
  const [connection, setConnection] = useState<StreamConnection>(
    enabled && taskId ? "connecting" : "closed",
  );
  const lastSeqRef = useRef(initialAfter);
  const terminalRef = useRef(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    lastSeqRef.current = initialAfter;
    terminalRef.current = false;
    if (!taskId || !enabled) {
      setConnection("closed");
      return;
    }
    const projectId = taskId;

    let disposed = false;
    let source: EventSource | null = null;
    let timer: number | null = null;

    function closeSource() {
      if (source) {
        source.onopen = null;
        source.onmessage = null;
        source.onerror = null;
        source.close();
        source = null;
      }
    }

    function scheduleReconnect() {
      if (disposed || terminalRef.current || timer !== null) return;
      timer = window.setTimeout(() => {
        timer = null;
        connect();
      }, RECONNECT_DELAY_MS);
    }

    async function checkSessionAndReconnect() {
      try {
        const [authResponse, projectResponse] = await Promise.all([
          fetch("/api/auth/me", {
            headers: { "Content-Type": "application/json" },
          }),
          fetch("/api/projects/" + encodeURIComponent(projectId), {
            headers: { "Content-Type": "application/json" },
          }),
        ]);
        if (authResponse.status === 401) {
          location.replace(loginRedirectPath());
          return;
        }
        if (projectResponse.status === 404 || projectResponse.status === 403) {
          terminalRef.current = true;
          closeSource();
          setConnection("error");
          return;
        }
        const data = (await authResponse.json().catch(() => ({}))) as {
          authenticated?: boolean;
        };
        if (data.authenticated === false) {
          location.replace(loginRedirectPath());
          return;
        }
        scheduleReconnect();
      } catch {
        scheduleReconnect();
      }
    }

    function connect() {
      if (disposed || terminalRef.current) return;
      closeSource();
      setConnection((current) =>
        current === "idle" || current === "closed" ? "connecting" : "reconnecting",
      );
      const events = new EventSource(
        "/api/projects/" +
          encodeURIComponent(projectId) +
          "/events?after=" +
          lastSeqRef.current,
      );
      source = events;
      events.onopen = () => {
        if (disposed) return;
        setConnection("streaming");
        if (timer !== null) {
          window.clearTimeout(timer);
          timer = null;
        }
      };
      events.onmessage = (message: MessageEvent<string>) => {
        if (disposed) return;
        let payload: TaskEvent;
        try {
          payload = JSON.parse(message.data) as TaskEvent;
        } catch {
          return;
        }
        if (
          !payload ||
          typeof payload.seq !== "number" ||
          payload.seq <= lastSeqRef.current
        ) {
          return;
        }
        lastSeqRef.current = payload.seq;
        onEventRef.current(payload);
        if (TERMINAL_EVENTS.has(payload.type)) {
          terminalRef.current = true;
          closeSource();
          setConnection("closed");
        }
      };
      events.onerror = () => {
        if (disposed || terminalRef.current) return;
        closeSource();
        setConnection("reconnecting");
        void checkSessionAndReconnect();
      };
    }

    connect();
    return () => {
      disposed = true;
      closeSource();
      if (timer !== null) window.clearTimeout(timer);
    };
  }, [taskId, initialAfter, enabled]);

  return connection;
}
