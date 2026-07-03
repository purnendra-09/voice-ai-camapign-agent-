import { create } from "zustand";
import type { ConversationEvent, Lead, Outcome } from "../types";

type TrainingState = {
  sessionId: string | null;
  activeLead: Lead;
  campaignId: string;
  promptVersion: string;
  modelProvider: string;
  language: string;
  startedAt: number | null;
  transcriptDraft: string;
  events: ConversationEvent[];
  outcome: Outcome;
  setTranscriptDraft: (value: string) => void;
  addEvent: (event: ConversationEvent) => void;
  reset: () => void;
};

const initialLead: Lead = {
  row_number: 2,
  patient_id: "PAT001",
  patient_name: "Ravi Kumar",
  phone_number: "9876543210",
  language: "Telugu",
  campaign: "Free Eye Camp",
  priority: "High",
  status: "Pending",
  call_attempts: 0,
  assigned_agent: "AI Campaign Bot",
};

const initialEvents: ConversationEvent[] = [
  {
    id: "evt-1",
    role: "system",
    label: "Session armed",
    content: "Patient context loaded from Hospital Campaign row 2.",
    timestamp: "00:00",
    meta: "memory update",
  },
  {
    id: "evt-2",
    role: "assistant",
    label: "AI",
    content:
      "Namaskaram Ravi Kumar garu. Nenu Akira Eye Hospital nundi AI Assistant maatladutunnanu. Free Eye Camp gurinchi rendu nimishalu maatladataniki samayam unda?",
    timestamp: "00:04",
    meta: "greeting",
  },
];

export const useTrainingStore = create<TrainingState>((set) => ({
  sessionId: null,
  activeLead: initialLead,
  campaignId: "Free Eye Camp",
  promptVersion: "Prompt V1",
  modelProvider: "Groq",
  language: "Telugu",
  startedAt: Date.now(),
  transcriptDraft: "",
  events: initialEvents,
  outcome: {
    status: "Interested",
    summary: "Patient is responding positively to the eye camp invitation.",
    next_action: "Continue qualification",
    follow_up_required: true,
    confidence: 0.78,
    intent: "Campaign interest",
    sentiment: "Positive",
  },
  setTranscriptDraft: (value) => set({ transcriptDraft: value }),
  addEvent: (event) => set((state) => ({ events: [...state.events, event] })),
  reset: () =>
    set({
      sessionId: null,
      startedAt: Date.now(),
      transcriptDraft: "",
      events: initialEvents,
      outcome: {
        status: "Other",
        summary: "No final classification yet.",
        next_action: "Continue local training",
        follow_up_required: false,
        confidence: 0.32,
      },
    }),
}));
