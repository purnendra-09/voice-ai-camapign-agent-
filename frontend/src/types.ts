export type Role = "assistant" | "user" | "system" | "tool";

export type ConversationEvent = {
  id: string;
  role: Role;
  label: string;
  content: string;
  timestamp: string;
  meta?: string;
};

export type Lead = {
  row_number: number;
  patient_id?: string;
  patient_name: string;
  phone_number: string;
  language?: string;
  campaign?: string;
  priority?: string;
  status: string;
  call_attempts?: number | string;
  last_call_time?: string | null;
  next_call_time?: string | null;
  assigned_agent?: string;
  raw?: Record<string, unknown>;
};

export type Outcome = {
  status: string;
  summary: string;
  next_action: string;
  follow_up_required: boolean;
  confidence: number;
  sentiment?: string;
  intent?: string;
  notes?: string;
};

export type TrainingReport = {
  success: boolean;
  session_id: string;
  campaign_id?: string;
  current_patient?: Lead;
  conversation_history: Array<{ role: string; content: string; timestamp: string }>;
  current_outcome?: Outcome;
  summary?: string;
  confidence?: number;
  prompt_key?: string;
  prompt_used?: string;
  patient_context: Record<string, unknown>;
  campaign_context: Record<string, unknown>;
  duration_seconds?: number;
  updated: boolean;
};
