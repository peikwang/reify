import { describe, expect, it } from "vitest";
import { suggestProjectTitle } from "./title";

describe("suggestProjectTitle", () => {
  it("extracts the object after a Chinese request verb", () => {
    expect(suggestProjectTitle("做一个贪吃蛇小游戏")).toBe("贪吃蛇小游戏");
    expect(suggestProjectTitle("帮我做一个可玩的俄罗斯方块")).toBe(
      "可玩的俄罗斯方块",
    );
  });

  it("combines a subject with its object", () => {
    expect(
      suggestProjectTitle("为一家独立设计工作室做一个有编辑感的官网。"),
    ).toBe("独立设计工作室官网");
  });

  it("drops quantifiers and descriptors", () => {
    expect(suggestProjectTitle("生成一段 5 秒的咖啡杯晨光慢镜头。")).toBe(
      "5 秒的咖啡杯晨光慢镜头",
    );
  });

  it("keeps English prompts short", () => {
    expect(suggestProjectTitle("make a neon snake game for my friends")).toBe(
      "make a neon snake game for",
    );
  });

  it("falls back to the capability label", () => {
    expect(suggestProjectTitle("   ", "小游戏")).toBe("小游戏");
    expect(suggestProjectTitle("做一个贪吃蛇小游戏", "小游戏")).toBe(
      "贪吃蛇小游戏",
    );
  });
});
