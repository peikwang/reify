import type { Stack } from "../../api/types";

const STATIC_SANDBOX = "allow-scripts allow-forms allow-popups allow-modals";
const SSR_SANDBOX =
  "allow-scripts allow-forms allow-popups allow-modals allow-same-origin";

export function previewSandbox(stack: Stack): string {
  // /apps/* lives on the separate 12889 origin; same-origin is required for its
  // own /api routes, while static /p/ pages stay in an opaque origin.
  return stack === "next" ? SSR_SANDBOX : STATIC_SANDBOX;
}

export function buildSsrPreviewUrl(
  runtimeUrl: string | null | undefined,
  ssrPreview: boolean,
  ssrPort: number | null,
  origin: string,
): string | null {
  if (!ssrPreview || !runtimeUrl) return null;
  const url = new URL(runtimeUrl, origin);
  if (ssrPort && url.port !== String(ssrPort)) {
    url.port = String(ssrPort);
  }
  return url.toString();
}
