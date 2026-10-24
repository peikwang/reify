import { describe, expect, it } from "vitest";

import { buildSsrPreviewUrl, previewSandbox } from "./ssrPreview";

describe("buildSsrPreviewUrl", () => {
  it("moves the app path to the SSR origin port", () => {
    expect(
      buildSsrPreviewUrl(
        "/apps/p1/",
        true,
        12889,
        "https://117.148.166.55:12888",
      ),
    ).toBe("https://117.148.166.55:12889/apps/p1/");
  });

  it("keeps the current origin when the SSR port is already active", () => {
    expect(
      buildSsrPreviewUrl("/apps/p1/", true, 12889, "https://example.test:12889"),
    ).toBe("https://example.test:12889/apps/p1/");
  });

  it("returns null when preview or the runtime URL is unavailable", () => {
    expect(buildSsrPreviewUrl("/apps/p1/", false, 12889, "https://x.test")).toBeNull();
    expect(buildSsrPreviewUrl(null, true, 12889, "https://x.test")).toBeNull();
  });
});

describe("previewSandbox", () => {
  it("allows same-origin only for the separate SSR origin", () => {
    expect(previewSandbox("next")).toContain("allow-same-origin");
    expect(previewSandbox("static")).not.toContain("allow-same-origin");
    expect(previewSandbox("react")).not.toContain("allow-same-origin");
  });
});
