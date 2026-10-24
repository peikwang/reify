import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Capability, Task } from "../../api/types";
import { ToastProvider } from "../../layout/ToastProvider";
import { Composer } from "./Composer";

const capabilities: Capability[] = [
  {
    key: "game",
    label: "小游戏",
    short: "GAME",
    description: "",
    example: "",
    prompt: "做一个霓虹风格的贪吃蛇小游戏。",
  },
  {
    key: "website",
    label: "网站",
    short: "WEB",
    description: "",
    example: "",
    prompt: "为一家独立设计工作室做一个有编辑感的官网。",
  },
];

function renderComposer() {
  const onCreated = vi.fn<(task: Task) => void>();
  render(
    <ToastProvider>
      <Composer capabilities={capabilities} onCreated={onCreated} />
    </ToastProvider>,
  );
  return { onCreated };
}

function mockCreate() {
  const created: Task = {
    id: "created1",
    prompt: capabilities[1].prompt,
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
    shared: false,
    share_url: null,
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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Composer", () => {
  it("fills the dedicated prompt when a template is selected", () => {
    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "网站" }));
    expect(screen.getByPlaceholderText(/选一个模板/)).toHaveValue(
      capabilities[1].prompt,
    );
    expect(screen.getByText(/已填入专用提示词/)).toBeInTheDocument();
  });

  it("does not expose implementation stacks to the user", () => {
    renderComposer();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("STACK")).not.toBeInTheDocument();
    expect(screen.queryByText("静态模板")).not.toBeInTheDocument();
    expect(screen.queryByText("React 源码")).not.toBeInTheDocument();
    expect(screen.queryByText("Next SSR")).not.toBeInTheDocument();
  });

  it("posts only the prompt and template capability", async () => {
    const { created, fetchMock } = mockCreate();
    const { onCreated } = renderComposer();

    fireEvent.click(screen.getByRole("button", { name: "网站" }));
    fireEvent.click(screen.getByRole("button", { name: /开始生成/ }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/projects");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      prompt: capabilities[1].prompt,
      capability: "website",
    });
  });

  it("lets the backend classify a free-form prompt", async () => {
    const { fetchMock } = mockCreate();
    const { onCreated } = renderComposer();
    const prompt = "做一个安静的摄影作品集，手机上看也要舒服";

    fireEvent.change(screen.getByPlaceholderText(/选一个模板/), {
      target: { value: prompt },
    });
    fireEvent.click(screen.getByRole("button", { name: /开始生成/ }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({
      prompt,
      capability: null,
    });
  });

  it("drops the template capability when its prompt is edited", async () => {
    const { fetchMock } = mockCreate();
    const { onCreated } = renderComposer();
    const edited = capabilities[1].prompt + " 配色更冷静一点";

    fireEvent.click(screen.getByRole("button", { name: "网站" }));
    fireEvent.change(screen.getByPlaceholderText(/选一个模板/), {
      target: { value: edited },
    });
    fireEvent.click(screen.getByRole("button", { name: /开始生成/ }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({
      prompt: edited,
      capability: null,
    });
  });
});
