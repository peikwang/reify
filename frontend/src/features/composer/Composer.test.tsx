import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Capability, Task } from "../../api/types";
import { ToastProvider } from "../../layout/ToastProvider";
import { Composer } from "./Composer";

const website: Capability = {
  key: "website",
  label: "网站",
  short: "WEB",
  description: "有品牌感、响应式的落地页或个人官网",
  example: "",
  prompt: "为一家独立设计工作室做一个有编辑感的官网。",
};

const video: Capability = {
  key: "video",
  label: "视频制作",
  short: "VIDEO",
  description: "把一个画面意图生成可播放的短视频",
  example: "",
  prompt: "生成一段 5 秒的咖啡杯晨光慢镜头。",
};

function Harness({
  initialPrompt = "",
  selectedTemplate = null,
  onCreated,
}: {
  initialPrompt?: string;
  selectedTemplate?: Capability | null;
  onCreated: (task: Task) => void;
}) {
  const [prompt, setPrompt] = useState(initialPrompt);
  return (
    <ToastProvider>
      <Composer
        prompt={prompt}
        onPromptChange={setPrompt}
        selectedTemplate={selectedTemplate}
        onCreated={onCreated}
      />
    </ToastProvider>
  );
}

function mockCreate() {
  const created: Task = {
    id: "created1",
    prompt: website.prompt,
    capability: "website",
    status: "queued",
    created_at: "2026-10-24T05:00:00+00:00",
    updated_at: "2026-10-24T05:00:00+00:00",
    result: null,
    error: null,
    source: "director",
    title: "网站",
    revision: 0,
    stack: "static",
    url: "/p/created1/",
    shared: true,
    share_url: "/s/public-token/",
    event_count: 0,
  };
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ task: created, events: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return { created, fetchMock };
}

function openNaming() {
  fireEvent.click(screen.getByRole("button", { name: /开始生成/ }));
  return screen.getByRole("dialog");
}

function confirmNaming(dialog: HTMLElement, title?: string) {
  if (title) {
    fireEvent.change(within(dialog).getByLabelText("项目名称"), {
      target: { value: title },
    });
  }
  fireEvent.click(within(dialog).getByRole("button", { name: /开始生成/ }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Composer", () => {
  it("renders one generic chat box without template controls", () => {
    render(
      <Harness
        initialPrompt={website.prompt}
        selectedTemplate={website}
        onCreated={vi.fn()}
      />,
    );

    expect(screen.getByPlaceholderText(/描述你想做的东西/)).toHaveValue(
      website.prompt,
    );
    expect(screen.queryByRole("group", { name: "模板选择" })).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "网站" })).not.toBeInTheDocument();
    expect(screen.queryByText("React 源码")).not.toBeInTheDocument();
    expect(screen.queryByText("Next SSR")).not.toBeInTheDocument();
  });

  it("asks for a project name with a prompt-derived default", async () => {
    const { fetchMock } = mockCreate();
    const onCreated = vi.fn<(task: Task) => void>();
    render(
      <Harness
        initialPrompt={website.prompt}
        selectedTemplate={website}
        onCreated={onCreated}
      />,
    );

    const dialog = openNaming();
    expect(within(dialog).getByLabelText("项目名称")).toHaveValue(
      "独立设计工作室官网",
    );
    confirmNaming(dialog, "我的工作室");

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/projects");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      prompt: website.prompt,
      capability: "website",
      title: "我的工作室",
    });
  });

  it("drops the template capability after the prompt is edited", async () => {
    const { fetchMock } = mockCreate();
    const onCreated = vi.fn<(task: Task) => void>();
    const edited = website.prompt + " 配色更冷静一点";
    render(
      <Harness
        initialPrompt={website.prompt}
        selectedTemplate={website}
        onCreated={onCreated}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText(/描述你想做的东西/), {
      target: { value: edited },
    });
    const dialog = openNaming();
    confirmNaming(dialog);

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({
      prompt: edited,
      capability: null,
      title: "独立设计工作室官网",
    });
  });

  it("lets the backend classify free-form prompts", async () => {
    const { fetchMock } = mockCreate();
    const onCreated = vi.fn<(task: Task) => void>();
    const prompt = "做一个安静的摄影作品集，手机上看也要舒服";
    render(<Harness initialPrompt={prompt} onCreated={onCreated} />);

    const dialog = openNaming();
    expect(within(dialog).getByLabelText("项目名称")).toHaveValue(
      "安静的摄影作品集",
    );
    confirmNaming(dialog);

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({
      prompt,
      capability: null,
      title: "安静的摄影作品集",
    });
  });

  it("does not submit an empty prompt", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<Harness onCreated={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /开始生成/ }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(await screen.findByText("先写一句你想做的东西")).toBeInTheDocument();
  });

  it("labels the selected template without exposing chips", () => {
    render(
      <Harness
        initialPrompt={video.prompt}
        selectedTemplate={video}
        onCreated={vi.fn()}
      />,
    );
    expect(screen.getByText(/视频制作 · 已填入专用提示词/)).toBeInTheDocument();
  });
});
