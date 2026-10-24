import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TaskEvent } from "../api/types";
import { useTaskStream } from "./useTaskStream";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  readonly url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emit(payload: unknown) {
    this.onmessage?.({
      data: JSON.stringify(payload),
    } as MessageEvent<string>);
  }
}

function event(seq: number, type: string): TaskEvent {
  return { seq, type, ts: "2026-10-24T06:00:00+00:00" };
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("useTaskStream", () => {
  it("opens after the initial sequence, dedupes and closes on terminal events", () => {
    const onEvent = vi.fn();
    const { result, unmount } = renderHook(() =>
      useTaskStream("p1", 4, onEvent, true),
    );

    const source = FakeEventSource.instances[0];
    expect(source?.url).toBe("/api/projects/p1/events?after=4");

    act(() => source?.onopen?.());
    expect(result.current).toBe("streaming");

    act(() => source?.emit(event(5, "thinking")));
    act(() => source?.emit(event(5, "thinking")));
    act(() => source?.emit(event(6, "verify")));
    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onEvent.mock.calls.map(([payload]) => payload.seq)).toEqual([5, 6]);

    act(() => source?.emit(event(7, "done")));
    expect(onEvent).toHaveBeenCalledTimes(3);
    expect(source?.closed).toBe(true);
    expect(result.current).toBe("closed");

    act(() => source?.onerror?.());
    expect(FakeEventSource.instances).toHaveLength(1);
    unmount();
  });

  it("reconnects from the latest sequence when the stream errors", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ authenticated: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    const onEvent = vi.fn();
    const { result, unmount } = renderHook(() =>
      useTaskStream("p1", 0, onEvent, true),
    );

    const source = FakeEventSource.instances[0];
    act(() => source?.emit(event(2, "thinking")));
    await act(async () => {
      source?.onerror?.();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(result.current).toBe("reconnecting");

    act(() => vi.advanceTimersByTime(1600));
    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.instances[1]?.url).toBe(
      "/api/projects/p1/events?after=2",
    );
    unmount();
  });

  it("stops reconnecting when the project no longer exists", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).startsWith("/api/projects/")) {
          return new Response("not found", { status: 404 });
        }
        return new Response(JSON.stringify({ authenticated: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
    const { result, unmount } = renderHook(() =>
      useTaskStream("p1", 0, vi.fn(), true),
    );

    const source = FakeEventSource.instances[0];
    await act(async () => {
      source?.onerror?.();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(result.current).toBe("error");

    act(() => vi.advanceTimersByTime(5000));
    expect(FakeEventSource.instances).toHaveLength(1);
    unmount();
  });

  it("does not open a stream when disabled", () => {
    renderHook(() => useTaskStream("p1", 0, vi.fn(), false));
    expect(FakeEventSource.instances).toHaveLength(0);
  });
});
