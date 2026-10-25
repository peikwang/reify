import { describe, expect, it } from "vitest";

import { safeNextPath } from "./nextPath";

const origin = "http://127.0.0.1:12888";

describe("safeNextPath", () => {
  it("keeps same-origin absolute paths", () => {
    expect(safeNextPath("/projects/abc123?tab=code", origin)).toBe(
      "/projects/abc123?tab=code",
    );
    expect(safeNextPath("/", origin)).toBe("/");
  });

  it("falls back for protocol-relative and absolute URLs", () => {
    expect(safeNextPath("//evil.example/path", origin)).toBe("/");
    expect(safeNextPath("https://evil.example/path", origin)).toBe("/");
    expect(safeNextPath("javascript:alert(1)", origin)).toBe("/");
  });

  it("rejects backslashes, control characters and relative paths", () => {
    expect(safeNextPath("/\\evil.example", origin)).toBe("/");
    expect(safeNextPath("/projects/\u0000abc", origin)).toBe("/");
    expect(safeNextPath("projects/abc", origin)).toBe("/");
    expect(safeNextPath("", origin)).toBe("/");
  });

  it("uses the provided fallback", () => {
    expect(safeNextPath("//evil.example", origin, "/projects")).toBe("/projects");
  });
});
