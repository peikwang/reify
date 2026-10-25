import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ForgeCompanion } from "./ForgeCompanion";

describe("ForgeCompanion", () => {
  it("reflects the current stage on its wrapper", () => {
    const { container, rerender } = render(<ForgeCompanion stage="plan" />);
    const box = container.querySelector(".companion");
    expect(box).toHaveAttribute("data-stage", "plan");
    rerender(<ForgeCompanion stage="build" />);
    expect(box).toHaveAttribute("data-stage", "build");
  });

  it("shows the stage copy and an accessible name", () => {
    render(<ForgeCompanion stage="deploy" />);
    expect(screen.getByText("部署完成，给你！")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /锻兽/ })).toBeInTheDocument();
  });
});
