import { describe, expect, it } from "vitest";
import {
  companionReducer,
  companionStageForEvent,
  type CompanionStage,
} from "./companion";

describe("companionStageForEvent", () => {
  it("maps planning events to plan", () => {
    expect(companionStageForEvent("plan")).toBe("plan");
    expect(companionStageForEvent("thinking")).toBe("plan");
    expect(companionStageForEvent("step_started")).toBe("plan");
  });

  it("maps file and media events to write", () => {
    expect(companionStageForEvent("file_diff")).toBe("write");
    expect(companionStageForEvent("media_progress")).toBe("write");
  });

  it("maps build and runtime build events to build", () => {
    expect(companionStageForEvent("build_log")).toBe("build");
    expect(companionStageForEvent("runtime_built")).toBe("build");
  });

  it("maps publish events to deploy and failures to error", () => {
    expect(companionStageForEvent("deployed")).toBe("deploy");
    expect(companionStageForEvent("runtime_ready")).toBe("deploy");
    expect(companionStageForEvent("build_failed")).toBe("error");
    expect(companionStageForEvent("interrupted")).toBe("error");
  });

  it("returns null for unknown events", () => {
    expect(companionStageForEvent("nope")).toBeNull();
  });
});

describe("companionReducer", () => {
  it("advances through a normal run", () => {
    const flow: Array<[string, CompanionStage]> = [
      ["task_started", "plan"],
      ["file_diff", "write"],
      ["build_started", "build"],
      ["deployed", "deploy"],
      ["done", "done"],
    ];
    let state: CompanionStage = "plan";
    for (const [type, expected] of flow) {
      state = companionReducer(state, { type: "event", eventType: type });
      expect(state).toBe(expected);
    }
  });

  it("recovers from an error when work resumes", () => {
    let state = companionReducer("plan", {
      type: "event",
      eventType: "build_failed",
    });
    expect(state).toBe("error");
    state = companionReducer(state, { type: "event", eventType: "build_log" });
    expect(state).toBe("build");
  });

  it("ignores unknown events and resets on demand", () => {
    const state = companionReducer("build", {
      type: "event",
      eventType: "mystery",
    });
    expect(state).toBe("build");
    expect(companionReducer("done", { type: "reset" })).toBe("plan");
  });
});
