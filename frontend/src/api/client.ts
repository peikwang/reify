import { loginRedirectPath } from "../auth/nextPath";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface ApiOptions extends RequestInit {
  authRedirect?: boolean;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { authRedirect = true, headers, ...rest } = options;
  const requestHeaders = new Headers(headers);
  if (
    rest.body !== undefined &&
    !(rest.body instanceof FormData) &&
    !requestHeaders.has("Content-Type")
  ) {
    requestHeaders.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...rest, headers: requestHeaders });
  if (response.status === 401 && authRedirect) {
    location.replace(loginRedirectPath());
  }
  if (!response.ok) {
    let detail = response.statusText || "请求失败";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Non-JSON error bodies keep the status text.
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
