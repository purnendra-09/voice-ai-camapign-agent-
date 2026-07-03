import { FormEvent, useMemo, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Loader2,
  Mic,
  Phone,
  RotateCcw,
  Save,
  Send,
  Square,
} from "lucide-react";
import { trainingApi } from "./api/trainingApi";
import type { ConversationEvent, Lead, Outcome } from "./types";

const campaignId = "Homeo Pills Free Health Camp";
const clientId = "homeo_pills_hospital";

function stamp() {
  return new Date().toLocaleTimeString([], { minute: "2-digit", second: "2-digit" });
}

function newEvent(role: ConversationEvent["role"], content: string, meta?: string): ConversationEvent {
  return {
    id: crypto.randomUUID(),
    role,
    label: role === "assistant" ? "AI Caller" : role === "user" ? "Patient" : "System",
    content,
    timestamp: stamp(),
    meta,
  };
}

export function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lead, setLead] = useState<Lead | null>(null);
  const [promptKey, setPromptKey] = useState("homeo_pills_campaign");
  const [events, setEvents] = useState<ConversationEvent[]>([
    newEvent("system", "Ready for Homeo Pills Telugu campaign training.", "standby"),
  ]);
  const [message, setMessage] = useState("");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canSave = events.some((item) => item.role === "assistant" || item.role === "user");

  const status = useMemo(() => {
    if (busy) return "Working";
    if (sessionId) return "Live training";
    return "Ready";
  }, [busy, sessionId]);

  async function startSession() {
    setBusy(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await trainingApi.startSession({
        campaign_id: campaignId,
        client_id: clientId,
      });
      if (!result.success || !result.session_id || !result.assistant_message) {
        throw new Error(result.error ?? "Unable to start training session");
      }
      setSessionId(result.session_id);
      setLead(result.lead ?? null);
      setPromptKey(result.prompt_key ?? "homeo_pills_campaign");
      setEvents([
        newEvent("system", "Homeo Pills campaign context loaded.", "session started"),
        newEvent("assistant", result.assistant_message, "opening"),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start training");
    } finally {
      setBusy(false);
    }
  }

  async function sendPatientMessage(event: FormEvent) {
    event.preventDefault();
    const clean = message.trim();
    if (!clean || !sessionId) return;
    setMessage("");
    setBusy(true);
    setError(null);
    setEvents((items) => [...items, newEvent("user", clean)]);
    try {
      const result = await trainingApi.sendMessage(sessionId, clean);
      if (!result.success || !result.assistant_message) {
        throw new Error(result.error ?? "No AI reply received");
      }
      const assistantMessage = result.assistant_message;
      setEvents((items) => [...items, newEvent("assistant", assistantMessage)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send message");
    } finally {
      setBusy(false);
    }
  }

  async function finishSession() {
    if (!sessionId) return;
    setBusy(true);
    setError(null);
    try {
      const report = await trainingApi.finishSession(sessionId, false);
      setOutcome(report.current_outcome ?? null);
      setEvents((items) => [...items, newEvent("system", "Training session evaluated.", "finished")]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to finish session");
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setSessionId(null);
    setLead(null);
    setOutcome(null);
    setError(null);
    setMessage("");
    setEvents([newEvent("system", "Ready for Homeo Pills Telugu campaign training.", "standby")]);
  }

  function saveConversationFile() {
    const lines = [
      "Homeo Pills AI Caller Training Report",
      `Saved At: ${new Date().toLocaleString()}`,
      "",
      "Campaign",
      `Campaign: ${campaignId}`,
      "Client: Homeo Pills Hospital",
      `Prompt: ${promptKey}`,
      "",
      "Patient",
      `Name: ${lead?.patient_name ?? "Not started"}`,
      `Phone: ${lead?.phone_number ?? "-"}`,
      `Language: ${lead?.language ?? "Telugu"}`,
      `Status: ${lead?.status ?? "-"}`,
      "",
      "Conversation",
      ...events.map((item) => `[${item.timestamp}] ${item.label}: ${item.content}`),
      "",
      "Evaluation",
      outcome
        ? [
            `Status: ${outcome.status}`,
            `Next Action: ${outcome.next_action}`,
            `Confidence: ${Math.round(outcome.confidence * 100)}%`,
            `Summary: ${outcome.summary}`,
            `Follow Up Required: ${outcome.follow_up_required ? "Yes" : "No"}`,
            outcome.intent ? `Intent: ${outcome.intent}` : "",
            outcome.sentiment ? `Sentiment: ${outcome.sentiment}` : "",
            outcome.notes ? `Notes: ${outcome.notes}` : "",
          ]
            .filter(Boolean)
            .join("\n")
        : "Not evaluated yet. Click Finish before sharing for evaluation.",
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    anchor.href = url;
    anchor.download = `homeo-pills-training-${date}.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen bg-[#0b0b0b] text-zinc-100">
      <header className="border-b border-white/10 bg-[#111]">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-zinc-500">Training Console</p>
            <h1 className="mt-1 text-2xl font-semibold">Homeo Pills AI Caller</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-zinc-300">
              {status}
            </span>
            <button
              className="inline-flex items-center gap-2 rounded-md bg-white px-4 py-2 text-sm font-medium text-zinc-950 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={startSession}
              disabled={busy}
              type="button"
            >
              {busy && !sessionId ? <Loader2 size={16} className="animate-spin" /> : <Phone size={16} />}
              Start Training
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-md border border-white/12 px-4 py-2 text-sm text-zinc-200 hover:bg-white/[0.06]"
              onClick={reset}
              type="button"
            >
              <RotateCcw size={16} />
              Reset
            </button>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-5 px-5 py-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-h-[70vh] rounded-lg border border-white/10 bg-[#151515]">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-md border border-white/10 bg-black">
                <Mic size={18} />
              </div>
              <div>
                <h2 className="font-semibold">Conversation</h2>
                <p className="text-sm text-zinc-500">Practice as the patient. AI replies in Telugu-English.</p>
              </div>
            </div>
            <button
              className="inline-flex items-center gap-2 rounded-md border border-white/12 px-3 py-2 text-sm text-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={finishSession}
              disabled={!sessionId || busy}
              type="button"
            >
              <Square size={15} />
              Finish
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-md border border-emerald-400/30 px-3 py-2 text-sm text-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={saveConversationFile}
              disabled={!canSave}
              type="button"
            >
              <Save size={15} />
              Save File
            </button>
          </div>

          <div className="space-y-4 px-5 py-5">
            {events.map((item) => (
              <article
                key={item.id}
                className={`max-w-[780px] rounded-lg border px-4 py-3 ${
                  item.role === "assistant"
                    ? "border-emerald-400/20 bg-emerald-400/[0.06]"
                    : item.role === "user"
                      ? "ml-auto border-sky-400/20 bg-sky-400/[0.06]"
                      : "border-white/10 bg-black/30"
                }`}
              >
                <div className="mb-2 flex items-center justify-between gap-3 text-xs text-zinc-500">
                  <span>{item.label}</span>
                  <span>{item.timestamp}</span>
                </div>
                <p className="text-[15px] leading-7 text-zinc-100">{item.content}</p>
              </article>
            ))}
          </div>

          <form className="border-t border-white/10 p-4" onSubmit={sendPatientMessage}>
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                className="min-h-12 flex-1 rounded-md border border-white/10 bg-black px-4 text-zinc-100 placeholder:text-zinc-600"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder={sessionId ? "Type patient reply, like: yes interested" : "Start training first"}
                disabled={!sessionId || busy}
              />
              <button
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-md bg-emerald-400 px-5 font-medium text-emerald-950 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!sessionId || busy || !message.trim()}
                type="submit"
              >
                {busy && sessionId ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
                Send
              </button>
            </div>
            {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
          </form>
        </div>

        <aside className="space-y-5">
          <section className="rounded-lg border border-white/10 bg-[#151515] p-5">
            <div className="mb-4 flex items-center gap-2">
              <Activity size={18} />
              <h2 className="font-semibold">Campaign Context</h2>
            </div>
            <dl className="space-y-3 text-sm">
              <Info label="Campaign" value={campaignId} />
              <Info label="Client" value="Homeo Pills Hospital" />
              <Info label="Prompt" value={promptKey} />
              <Info label="Language" value={lead?.language ?? "Telugu"} />
            </dl>
          </section>

          <section className="rounded-lg border border-white/10 bg-[#151515] p-5">
            <h2 className="mb-4 font-semibold">Patient</h2>
            <dl className="space-y-3 text-sm">
              <Info label="Name" value={lead?.patient_name ?? "Not started"} />
              <Info label="Phone" value={lead?.phone_number ?? "-"} />
              <Info label="Status" value={lead?.status ?? "-"} />
              <Info label="Priority" value={lead?.priority ?? "-"} />
            </dl>
          </section>

          <section className="rounded-lg border border-white/10 bg-[#151515] p-5">
            <div className="mb-4 flex items-center gap-2">
              <CheckCircle2 size={18} />
              <h2 className="font-semibold">Outcome</h2>
            </div>
            {outcome ? (
              <dl className="space-y-3 text-sm">
                <Info label="Status" value={outcome.status} />
                <Info label="Next Action" value={outcome.next_action} />
                <Info label="Confidence" value={`${Math.round(outcome.confidence * 100)}%`} />
                <Info label="Summary" value={outcome.summary} />
              </dl>
            ) : (
              <p className="text-sm leading-6 text-zinc-500">Finish the session to see classification.</p>
            )}
          </section>
        </aside>
      </section>
    </main>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <dt className="text-xs uppercase tracking-[0.18em] text-zinc-600">{label}</dt>
      <dd className="break-words text-zinc-100">{value}</dd>
    </div>
  );
}
