import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { HomePage } from "../pages/HomePage";
import { AppShell } from "./AppShell";
import { ToastProvider } from "./ToastProvider";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { role: "user" },
    logout: vi.fn(),
  }),
}));

vi.mock("../hooks/useCapabilities", () => ({
  useCapabilities: () => ({
    capabilities: [],
    loading: false,
    error: null,
    ssrPreview: false,
    ssrPort: null,
  }),
}));

vi.mock("../hooks/useProjects", () => ({
  useProjects: () => ({
    items: [],
    loading: false,
    error: null,
    reload: vi.fn(),
  }),
}));

function renderApp() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <ToastProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<HomePage />} />
          </Route>
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  );
}

describe("AppShell new task action", () => {
  it("clears the composer and focuses it when already on the home page", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    renderApp();
    const textarea = screen.getByLabelText("项目需求");
    fireEvent.change(textarea, { target: { value: "做一个网站" } });
    expect(textarea).toHaveValue("做一个网站");

    fireEvent.click(screen.getByRole("button", { name: "新任务" }));

    await waitFor(() => expect(textarea).toHaveValue(""));
    await waitFor(() => expect(textarea).toHaveFocus());
  });
});
