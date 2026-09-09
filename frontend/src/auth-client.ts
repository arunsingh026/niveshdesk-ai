const nativeFetch = window.fetch.bind(window);

// Sessions live in a Secure, HttpOnly cookie. Every API request opts in to it;
// JavaScript never reads or stores the session credential.
window.fetch = (input: RequestInfo | URL, init: RequestInit = {}) =>
  nativeFetch(input, { ...init, credentials: "include" });

export type AccountUser = {
  id: number;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  role: "user" | "admin";
  must_change_password: boolean;
};

export const API = window.location.hostname === "localhost" ? "http://localhost:8000" : window.location.origin;

export async function apiJson(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API}${path}`, init);
  const payload = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.detail || "Something went wrong. Please try again.");
  return payload;
}
