import { API_URL, apiFetch } from "./apiClient";

export type UserRole = "user" | "admin";

export type UserResponse = {
  id: number;
  email: string;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
};

export type LoginData = {
  email: string;
  password: string;
};

export type RegisterData = {
  email: string;
  username: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserResponse;
};

export async function registerUser(data: RegisterData): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Ошибка регистрации");
  }

  return response.json();
}

export async function loginUser(data: LoginData): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Неверная почта или пароль");
  }

  return response.json();
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiFetch("/auth/me", { method: "GET" });

  if (!response.ok) {
    throw new Error("Не удалось получить текущего пользователя");
  }

  return response.json();
}

export async function logoutUser(refreshToken: string): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}
