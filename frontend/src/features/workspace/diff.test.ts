import { describe, expect, it } from "vitest";

import { computeLineDiff } from "./diff";

describe("computeLineDiff", () => {
  it("returns an empty diff for empty inputs", () => {
    expect(computeLineDiff("", "")).toEqual({
      lines: [],
      additions: 0,
      deletions: 0,
    });
  });

  it("marks every line as added for a created file", () => {
    const result = computeLineDiff("", "a\nb");
    expect(result.additions).toBe(2);
    expect(result.deletions).toBe(0);
    expect(result.lines.map((line) => [line.type, line.newNo])).toEqual([
      ["add", 1],
      ["add", 2],
    ]);
  });

  it("keeps unchanged lines as context", () => {
    const result = computeLineDiff("a\nb\nc", "a\nb\nc");
    expect(result.additions).toBe(0);
    expect(result.deletions).toBe(0);
    expect(result.lines.every((line) => line.type === "same")).toBe(true);
    expect(result.lines[1]).toMatchObject({ oldNo: 2, newNo: 2, line: "b" });
  });

  it("shows mixed additions and deletions", () => {
    const result = computeLineDiff("a\nb\nc", "a\nB\nc\nd");
    expect(result.additions).toBe(2);
    expect(result.deletions).toBe(1);
    expect(result.lines.some((line) => line.type === "del" && line.line === "b")).toBe(true);
    expect(result.lines.some((line) => line.type === "add" && line.line === "B")).toBe(true);
    expect(result.lines.some((line) => line.type === "add" && line.line === "d")).toBe(true);
  });

  it("marks every old line as deleted when the file is removed", () => {
    const result = computeLineDiff("a\nb", "");
    expect(result.lines.map((line) => line.type)).toEqual(["del", "del"]);
    expect(result.deletions).toBe(2);
  });
});
