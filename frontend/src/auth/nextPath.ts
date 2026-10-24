const CONTROL_CHARS = /[\u0000-\u001f]/;

export function safeNextPath(
  raw: string | null | undefined,
  origin: string,
  fallback = "/",
): string {
  if (!raw) return fallback;
  if (
    !raw.startsWith("/") ||
    raw.startsWith("//") ||
    raw.includes("\\") ||
    CONTROL_CHARS.test(raw)
  ) {
    return fallback;
  }
  try {
    const candidate = new URL(raw, origin);
    if (candidate.origin !== origin) return fallback;
    const resolved = candidate.pathname + candidate.search;
    if (
      !resolved.startsWith("/") ||
      resolved.startsWith("//") ||
      resolved.includes("\\") ||
      CONTROL_CHARS.test(resolved)
    ) {
      return fallback;
    }
    return resolved;
  } catch {
    return fallback;
  }
}

export function currentPathWithSearch(): string {
  return location.pathname + location.search;
}

export function loginRedirectPath(): string {
  const next = safeNextPath(currentPathWithSearch(), location.origin);
  return "/login?next=" + encodeURIComponent(next);
}
