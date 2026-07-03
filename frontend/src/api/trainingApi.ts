import type { Lead, TrainingReport } from "../types";

function resolveApiBase(): string {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:8000`;
}

const API_BASE = resolveApiBase();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const trainingApi = {
  startSession(payload: {
    campaign_id: string;
    row_number?: number;
    client_id?: string;
    prompt_key?: string;
  }) {
    return request<{
      success: boolean;
      session_id?: string;
      campaign_id?: string;
      lead?: Lead;
      assistant_message?: string;
      prompt_key?: string;
      error?: string;
    }>("/training/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  sendMessage(sessionId: string, message: string) {
    return request<{ success: boolean; assistant_message?: string; error?: string }>(
      `/training/sessions/${sessionId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
    );
  },
  finishSession(sessionId: string, updateExcel = true) {
    return request<TrainingReport>(`/training/sessions/${sessionId}/finish`, {
      method: "POST",
      body: JSON.stringify({ update_excel: updateExcel }),
    });
  },
  getReport(sessionId: string) {
    return request<TrainingReport>(`/training/sessions/${sessionId}`);
  },
};
