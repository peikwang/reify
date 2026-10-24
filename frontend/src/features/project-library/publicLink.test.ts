import { describe, expect, it } from "vitest";

import { absolutePublicUrl } from "./publicLink";

describe("absolutePublicUrl", () => {
  it("resolves the unlisted share path against the platform origin", () => {
    expect(absolutePublicUrl("/s/public-token/", "https://vf.example")).toBe(
      "https://vf.example/s/public-token/",
    );
    expect(
      absolutePublicUrl("/s/public-token/", "http://127.0.0.1:12888"),
    ).toBe("http://127.0.0.1:12888/s/public-token/");
  });
});
