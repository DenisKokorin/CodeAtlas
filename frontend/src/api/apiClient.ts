export const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

type RequestOptions = RequestInit & {
  skipRefresh?: boolean;
};

function clearAuthStorage() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("auth_email");
  localStorage.removeItem("auth_role");
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem("refresh_token");

  if (!refreshToken) {
    clearAuthStorage();
    throw new Error("Refresh token is missing");
  }

  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearAuthStorage();
    throw new Error("Unable to refresh access token");
  }

  const data = await response.json();
  localStorage.setItem("auth_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data.access_token;
}

function buildHeaders(token: string, options?: RequestOptions) {
  const isFormData = options?.body instanceof FormData;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };

  if (!isFormData && !(options?.body instanceof Blob)) {
    headers["Content-Type"] = "application/json";
  }

  return { ...headers, ...(options?.headers ?? {}) };
}

export async function apiFetch(path: string, options: RequestOptions = {}) {
  const accessToken = localStorage.getItem("auth_token");

  if (!accessToken) {
    clearAuthStorage();
    throw new Error("Access token is missing");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: buildHeaders(accessToken, options),
  });

  if (response.status !== 401 || options.skipRefresh) {
    return response;
  }

  const newAccessToken = await refreshAccessToken();

  return fetch(`${API_URL}${path}`, {
    ...options,
    headers: buildHeaders(newAccessToken, options),
  });
}

export async function readErrorMessage(response: Response, fallback: string) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    return fallback;
  }

  return fallback;
}
