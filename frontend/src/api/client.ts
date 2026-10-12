// Small fetch wrapper that adds the login token and turns errors into readable messages.

const TOKEN_KEY = "georevive.token";

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: token lives only in memory for this tab */
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* not JSON */
    }
    if (res.status === 401) window.dispatchEvent(new Event("georevive:unauthorised"));
    throw new ApiError(res.status, msg);
  }
  const ct = res.headers.get("content-type") || "";
  return (ct.includes("application/json") ? res.json() : res.text()) as Promise<T>;
}

function headers(extra?: HeadersInit): HeadersInit {
  const t = getToken();
  return { ...(t ? { Authorization: `Bearer ${t}` } : {}), ...(extra || {}) };
}

export const api = {
  get: <T>(path: string) => fetch(path, { headers: headers() }).then((r) => handle<T>(r)),
  post: <T>(path: string, body?: unknown) =>
    fetch(path, {
      method: "POST",
      headers: headers({ "Content-Type": "application/json" }),
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then((r) => handle<T>(r)),
  put: <T>(path: string, body?: unknown) =>
    fetch(path, {
      method: "PUT",
      headers: headers({ "Content-Type": "application/json" }),
      body: JSON.stringify(body ?? {}),
    }).then((r) => handle<T>(r)),
  del: <T>(path: string) => fetch(path, { method: "DELETE", headers: headers() }).then((r) => handle<T>(r)),
  upload: <T>(path: string, form: FormData) =>
    fetch(path, { method: "POST", headers: headers(), body: form }).then((r) => handle<T>(r)),
};

/** URL for a protected file (image, PDF, download) usable in <img src> or a new tab. */
export function authUrl(path: string): string {
  const t = getToken();
  if (!t) return path;
  return `${path}${path.includes("?") ? "&" : "?"}token=${encodeURIComponent(t)}`;
}
