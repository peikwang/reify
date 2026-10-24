import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Capability } from "../../api/types";
import { TemplateGallery } from "./TemplateGallery";

const website: Capability = {
  key: "website",
  label: "网站",
  short: "WEB",
  description: "有品牌感、响应式的落地页或个人官网",
  example: "",
  prompt: "做一个网站",
};

const video: Capability = {
  key: "video",
  label: "视频制作",
  short: "VIDEO",
  description: "把一个画面意图生成可播放的短视频",
  example: "",
  prompt: "做一段视频",
};

describe("TemplateGallery", () => {
  it("renders one illustrated card per available template", () => {
    const { container } = render(
      <TemplateGallery
        capabilities={[website, video]}
        activeKey="website"
        onSelect={vi.fn()}
      />,
    );

    const site = screen.getByRole("button", { name: /网站/ });
    const clip = screen.getByRole("button", { name: /视频制作/ });
    expect(site).toHaveAttribute("aria-pressed", "true");
    expect(clip).toHaveAttribute("aria-pressed", "false");
    expect(container.querySelectorAll("svg")).toHaveLength(2);
  });

  it("selects a template for the shared composer", () => {
    const onSelect = vi.fn();
    render(
      <TemplateGallery
        capabilities={[website, video]}
        activeKey={null}
        onSelect={onSelect}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /视频制作/ }));
    expect(onSelect).toHaveBeenCalledWith(video);
  });

  it("renders nothing while capabilities are unavailable", () => {
    const { container } = render(
      <TemplateGallery capabilities={[]} activeKey={null} onSelect={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
