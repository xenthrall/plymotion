import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];
export type Job = Schemas["JobInfo"];
export type JobDetail = Schemas["JobDetail"];
export type LibraryTheme = Schemas["LibraryTheme"];
export type InstalledTheme = Schemas["InstalledTheme"];
export type VideoInfo = Schemas["VideoInfo"];
export type Meta = Schemas["Meta"];
export type Prefs = Schemas["Prefs"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message);
  }
}

// X-Plymotion is required by the server on every state-changing request
// (see plymotion/api/security.py); a cross-site form can't send it.
export const api = createClient<paths>({
  baseUrl: "",
  headers: { "X-Plymotion": "1" },
  credentials: "same-origin",
});

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

api.use({
  async onResponse({ response }) {
    if (response.ok) return response;
    if (response.status === 401) onUnauthorized?.();
    let body: { code?: string; message?: string; detail?: unknown } = {};
    try {
      body = await response.clone().json();
    } catch {
      /* not JSON */
    }
    throw new ApiError(
      body.message ?? `Error ${response.status}`,
      body.code ?? "http_error",
      response.status,
      body.detail,
    );
  },
});

/** Unwrap an openapi-fetch result; errors were already thrown by the middleware. */
export async function call<T>(promise: Promise<{ data?: T; error?: unknown }>): Promise<T> {
  const { data } = await promise;
  return data as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return String(error);
}
