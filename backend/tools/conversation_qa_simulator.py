import asyncio
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.local_training_service import LocalTrainingService
from app.services.outcome_service import OutcomeService
from app.services.prompt_manager import PromptManager


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "pdf"
JSON_REPORT = OUTPUT_DIR / "conversation_qa_report.json"
PDF_REPORT = OUTPUT_DIR / "conversation_qa_report.pdf"


class FakeCampaignService:
    def start_call(self, campaign_id, row_number=None):
        return {"success": False}


class FakeClientManager:
    def get_client_metadata(self, client_id):
        return {
            "name": "Homeo Pills Hospital",
            "prompt_key": "homeo_pills_campaign",
            "language": "Telugu",
        }


class FakeCampaignOrchestrator:
    def __init__(self):
        self.outcomes = OutcomeService()

    async def complete_call(self, **kwargs):
        return {"success": True, "outcome": None, "updated": False}


@dataclass
class Scenario:
    scenario_id: str
    category: str
    messages: List[str]
    expected: List[str]


def build_scenarios() -> List[Scenario]:
    categories = {
        "Greeting": ["Hello", "Hi", "Namaskaram", "Good Morning", "Hello andi"],
        "Identity": ["Who are you?", "Evaru maatladuthunnaru?", "Hospital nundi aa?", "Who is calling?", "Meeru evaru?"],
        "Purpose": ["Why are you calling?", "Enduku call chesaru?", "What is this call about?", "Call purpose enti?", "Enduku andi?"],
        "Campaign": ["Camp enti?", "Health camp ante enti?", "Free aa?", "Em chestaru?", "Camp details cheppandi"],
        "Venue": ["Venue ekkada?", "Address enti?", "Ekkada ravali?", "Place enti?", "Location share cheyyandi"],
        "Time": ["Time enti?", "Morning aa?", "Evening aa?", "Eppudu camp?", "Timing cheppandi"],
        "Doctor": ["Doctor untara?", "Eye doctor aa?", "Specialist untara?", "Doctor available aa?", "Dr Rao untara?"],
        "Medicine": ["Free medicines untaya?", "Tests free aa?", "Mandulu free aa?", "Medicine details enti?", "Tablets istara?"],
        "Interest": ["Interest undi", "Attend avutha", "Vastanu", "Sure", "Avunu ravachu"],
        "Not Interested": ["Naaku interest ledu", "No", "Vaddu", "Don't call again", "Not interested"],
        "Busy": ["Busy unna", "Later call cheyyandi", "Repu call cheyyandi", "Ippudu busy", "Call back evening"],
        "Wrong Number": ["Wrong number", "Wrong person", "Tappu number", "This is not Ravi", "Wrong call"],
        "Memory": ["Nenu ippude em adiganu?", "Naa peru enti?", "Nenu attend avuthanu ani cheppana?", "What did you tell me?", "What did I ask?"],
        "Multi Question": [
            "Venue? Time? Doctor?",
            "Medicines? Fee? Time?",
            "Address enti? Doctor untara? Free aa?",
            "Camp enti? Ekkada? Eppudu?",
            "Venue, time, tests free aa?",
        ],
        "Emotional": ["Naaku bayam ga undi", "Health problem undi", "Pain undi", "Naku tension ga undi", "Eye problem serious aa?"],
        "Interruptions": ["Hello ... wait ... continue", "One second ... cheppandi", "Hello ...", "Wait andi", "Continue cheyyandi"],
        "Code Switching": [
            "Camp details English lo cheppu",
            "Venue ekkada and what time?",
            "Doctor available aa bro?",
            "I am interested, but address enti?",
            "Free medicines untaya or only checkup?",
        ],
        "Unexpected": ["Weather enti?", "Politics enti?", "Cricket score enti?", "Movie tickets unnaya?", "Loan istara?"],
        "Conversation Summary": ["What did I ask?", "What happened?", "Nenu em cheppanu?", "Summary cheppu", "Mana conversation enti?"],
    }
    expected_by_category = {
        "Identity": ["identity"],
        "Purpose": ["purpose", "campaign"],
        "Campaign": ["campaign"],
        "Venue": ["location"],
        "Time": ["time"],
        "Doctor": ["doctor"],
        "Medicine": ["medicine", "fee"],
        "Interest": ["interest"],
        "Not Interested": ["close"],
        "Busy": ["callback"],
        "Wrong Number": ["close"],
        "Memory": ["memory"],
        "Multi Question": ["location", "time", "doctor"],
        "Unexpected": ["redirect"],
        "Conversation Summary": ["memory"],
    }
    scenarios: List[Scenario] = []
    for category, messages in categories.items():
        for index, message in enumerate(messages, start=1):
            scenarios.append(
                Scenario(
                    scenario_id=f"{category[:3].upper()}-{index:03d}",
                    category=category,
                    messages=[message],
                    expected=expected_by_category.get(category, []),
                )
            )

    long_turns = [
        "Hello",
        "Evaru maatladuthunnaru?",
        "Enduku call chesaru?",
        "Camp enti?",
        "Free aa?",
        "Venue ekkada?",
        "Time enti?",
        "Doctor untara?",
        "Medicines free aa?",
        "Tests free aa?",
        "Naa peru enti?",
        "Nenu ippude em adiganu?",
        "Naaku bayam ga undi",
        "Family kosam ravacha?",
        "Interest undi",
        "Vastanu",
        "What did you tell me?",
        "Okay confirm",
        "Thank you",
        "Bye",
    ]
    for index in range(1, 6):
        scenarios.append(
            Scenario(
                scenario_id=f"LON-{index:03d}",
                category="Long Conversation",
                messages=long_turns[:],
                expected=["memory", "location", "time", "doctor", "interest"],
            )
        )
    return scenarios


class ConversationQAEvaluator:
    hallucination_terms = ["amalapuram", "9 am", "10 am", "doctor available", "confirmed appointment"]

    def evaluate_turn(
        self,
        scenario: Scenario,
        patient_message: str,
        assistant_message: str,
        plan: Dict[str, Any],
        previous_assistant: List[str],
    ) -> Dict[str, Any]:
        lowered = assistant_message.lower()
        bugs: List[str] = []
        scores = {metric: 8 for metric in self.metric_names()}

        if "namaskaram" in lowered and any("namaskaram" in msg.lower() for msg in previous_assistant):
            bugs.append("Repeated greeting")
            scores["Repetition"] = 3

        if lowered.count("free health camp") > 1:
            bugs.append("Repeated campaign")
            scores["Repetition"] = min(scores["Repetition"], 4)

        if lowered.count("interest") > 1:
            bugs.append("Repeated interest")
            scores["Repetition"] = min(scores["Repetition"], 4)

        if len(assistant_message.split()) > 55:
            bugs.append("Long response")
            scores["Natural Telugu"] = 5
            scores["Conversation Progress"] = 5

        if any(term in lowered for term in self.hallucination_terms):
            bugs.append("Hallucination")
            scores["Hallucination"] = 1
            scores["Business Rules"] = 3

        if self._ignored_question(patient_message, assistant_message):
            bugs.append("Ignored question")
            scores["Question Handling"] = 3
            scores["Context Awareness"] = 4

        if scenario.category in {"Memory", "Conversation Summary", "Long Conversation"} and self._memory_failed(patient_message, assistant_message):
            bugs.append("Memory failure")
            scores["Memory"] = 2
            scores["Context Awareness"] = min(scores["Context Awareness"], 4)

        if scenario.category == "Unexpected" and not self._redirected(assistant_message):
            bugs.append("Wrong action")
            scores["Business Rules"] = 5
            scores["Conversation Progress"] = 4

        if previous_assistant and assistant_message.strip().lower() == previous_assistant[-1].strip().lower():
            bugs.append("Loop")
            scores["Conversation Progress"] = 2
            scores["Repetition"] = 2

        if not self._looks_telugu_english(assistant_message):
            bugs.append("Poor Telugu")
            scores["Natural Telugu"] = 4

        if plan.get("patient_intent") == "UNKNOWN" and scenario.expected:
            bugs.append("Wrong state")
            scores["Conversation Progress"] = min(scores["Conversation Progress"], 5)

        if "sorry" in lowered or "kshaminchandi" in lowered or "parledandi" in lowered:
            scores["Empathy"] = min(10, scores["Empathy"] + 1)
        if plan.get("requires_tool"):
            scores["Tool Usage"] = 8
        else:
            scores["Tool Usage"] = 7

        if not bugs:
            for metric in scores:
                scores[metric] = min(10, scores[metric] + 1)

        scores["Overall"] = round(sum(value for key, value in scores.items() if key != "Overall") / (len(scores) - 1), 2)
        return {
            "patient_message": patient_message,
            "assistant_message": assistant_message,
            "plan": plan,
            "scores": scores,
            "bugs": bugs,
            "failure_reason": "; ".join(bugs) if bugs else "No major failure detected",
        }

    def metric_names(self) -> List[str]:
        return [
            "Greeting",
            "Identity",
            "Purpose",
            "Natural Telugu",
            "Context Awareness",
            "Memory",
            "Question Handling",
            "Empathy",
            "Business Rules",
            "Tool Usage",
            "Conversation Progress",
            "Hallucination",
            "Repetition",
            "Overall",
        ]

    def _ignored_question(self, patient: str, assistant: str) -> bool:
        patient_lower = patient.lower()
        assistant_lower = assistant.lower()
        checks = {
            "location": ["venue", "address", "ekkada", "location", "place"],
            "time": ["time", "timing", "eppudu", "morning", "evening"],
            "doctor": ["doctor", "dr", "specialist"],
            "medicine": ["medicine", "medicines", "mandulu", "tablet", "tests"],
            "fee": ["free", "fee", "cost", "charge"],
        }
        asked = [name for name, tokens in checks.items() if any(token in patient_lower for token in tokens)]
        if not asked:
            return False
        answered = [name for name, tokens in checks.items() if any(token in assistant_lower for token in tokens)]
        return not set(asked).intersection(answered)

    def _memory_failed(self, patient: str, assistant: str) -> bool:
        patient_lower = patient.lower()
        assistant_lower = assistant.lower()
        if any(token in patient_lower for token in ["what did i ask", "em adiganu", "summary", "what happened"]):
            return not any(token in assistant_lower for token in ["adigaru", "ask", "conversation", "summary", "cheppanu", "venue", "time", "doctor"])
        if "naa peru" in patient_lower:
            return not any(token in assistant_lower for token in ["ravi", "peru"])
        if "attend avuthanu" in patient_lower:
            return not any(token in assistant_lower for token in ["attend", "vastanu", "confirm"])
        return False

    def _redirected(self, assistant: str) -> bool:
        lowered = assistant.lower()
        return any(token in lowered for token in ["camp", "health", "hospital", "medical", "conversation", "doubt"])

    def _looks_telugu_english(self, assistant: str) -> bool:
        lowered = assistant.lower()
        tokens = ["andi", "mee", "meeku", "rav", "che", "camp", "hospital", "dhanyavadalu", "kshaminchandi"]
        return any(token in lowered for token in tokens)


async def run_scenarios() -> Dict[str, Any]:
    service = LocalTrainingService(
        FakeCampaignService(),
        FakeCampaignOrchestrator(),
        PromptManager(),
        FakeClientManager(),
        llm_service=None,
    )
    evaluator = ConversationQAEvaluator()
    results = []
    scenarios = build_scenarios()

    for scenario in scenarios:
        start = await service.start_session(
            "Homeo Pills Free Health Camp",
            client_id="homeo_pills_hospital",
        )
        session_id = start["session_id"]
        turns = []
        previous_assistant = [start["assistant_message"]]
        for patient_message in scenario.messages:
            reply = await service.send_message(session_id, patient_message)
            session = service.sessions[session_id]
            plan = session.get("last_plan") or {}
            turn = evaluator.evaluate_turn(
                scenario=scenario,
                patient_message=patient_message,
                assistant_message=reply["assistant_message"],
                plan=plan,
                previous_assistant=previous_assistant,
            )
            turns.append(turn)
            previous_assistant.append(reply["assistant_message"])

        report = service.report(session_id)
        scenario_bugs = [bug for turn in turns for bug in turn["bugs"]]
        turn_scores = [turn["scores"]["Overall"] for turn in turns]
        results.append(
            {
                "scenario_id": scenario.scenario_id,
                "category": scenario.category,
                "expected": scenario.expected,
                "transcript": report["conversation_history"],
                "turns": turns,
                "state_timeline": [turn["plan"].get("next_state") for turn in turns],
                "detected_intents": [turn["plan"].get("patient_intent") for turn in turns],
                "detected_actions": [
                    (turn["plan"].get("entities") or {}).get("business_action")
                    for turn in turns
                ],
                "bugs": scenario_bugs,
                "failure_reason": "; ".join(sorted(set(scenario_bugs))) if scenario_bugs else "No major failure detected",
                "overall_score": round(sum(turn_scores) / max(len(turn_scores), 1), 2),
            }
        )

    return summarize(results)


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    bug_counter = Counter(bug for result in results for bug in result["bugs"])
    category_scores = defaultdict(list)
    for result in results:
        category_scores[result["category"]].append(result["overall_score"])

    summary = {
        "generated_at": datetime.utcnow().isoformat(),
        "scenario_count": len(results),
        "turn_count": sum(len(result["turns"]) for result in results),
        "overall_score": round(sum(result["overall_score"] for result in results) / max(len(results), 1), 2),
        "bug_counts": dict(bug_counter.most_common()),
        "category_scores": {
            category: round(sum(scores) / len(scores), 2)
            for category, scores in sorted(category_scores.items())
        },
        "failed_scenarios": sum(1 for result in results if result["bugs"]),
    }
    return {
        "title": "Conversation QA Report",
        "summary": summary,
        "results": results,
        "recommendations": build_recommendations(bug_counter),
    }


def build_recommendations(bug_counter: Counter) -> List[str]:
    recommendations = []
    if bug_counter.get("Ignored question"):
        recommendations.append("Strengthen pending-question enforcement so multi-question turns are answered before new qualification.")
    if bug_counter.get("Memory failure"):
        recommendations.append("Expose the blackboard summary and answered-question list more explicitly in local training responses.")
    if bug_counter.get("Wrong action"):
        recommendations.append("Add stronger off-topic redirection rules for weather, politics, cricket, and unrelated requests.")
    if bug_counter.get("Poor Telugu"):
        recommendations.append("Expand Telugu phrase templates for memory and summary replies.")
    if bug_counter.get("Hallucination"):
        recommendations.append("Keep factual claims restricted to loaded knowledge and mark missing venue/time/doctor facts clearly.")
    if not recommendations:
        recommendations.append("No critical defects detected. Continue regression testing with live LLM provider responses.")
    return recommendations


def write_json_report(report: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")


def write_pdf_report(report: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleLarge", parent=styles["Title"], fontSize=24, leading=28, spaceAfter=18))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Muted", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#555555")))

    doc = SimpleDocTemplate(
        str(PDF_REPORT),
        pagesize=A4,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    story: List[Any] = []
    summary = report["summary"]

    story.append(Paragraph("Conversation QA Report", styles["TitleLarge"]))
    story.append(Paragraph(f"Generated: {summary['generated_at']}", styles["Muted"]))
    story.append(Spacer(1, 0.15 * inch))
    overview = [
        ["Scenarios", summary["scenario_count"], "Turns", summary["turn_count"]],
        ["Overall Score", summary["overall_score"], "Failed Scenarios", summary["failed_scenarios"]],
    ]
    story.append(make_table(overview, [1.4 * inch, 1.2 * inch, 1.5 * inch, 1.2 * inch]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Failure Summary", styles["Heading2"]))
    bug_rows = [["Bug", "Count"]] + [[bug, count] for bug, count in summary["bug_counts"].items()]
    if len(bug_rows) == 1:
        bug_rows.append(["No major failures", 0])
    story.append(make_table(bug_rows, [3.6 * inch, 1.1 * inch], header=True))
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("Category Scores", styles["Heading2"]))
    category_rows = [["Category", "Avg Score"]] + [
        [category, score] for category, score in summary["category_scores"].items()
    ]
    story.append(make_table(category_rows, [3.4 * inch, 1.2 * inch], header=True))
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("Recommendations", styles["Heading2"]))
    for recommendation in report["recommendations"]:
        story.append(Paragraph(f"- {recommendation}", styles["BodyText"]))
    story.append(PageBreak())

    story.append(Paragraph("Scenario Details", styles["Heading2"]))
    for result in report["results"]:
        story.append(Paragraph(
            f"{result['scenario_id']} - {result['category']} - Score {result['overall_score']}",
            styles["Heading3"],
        ))
        story.append(Paragraph(f"Failure reason: {result['failure_reason']}", styles["Muted"]))
        timeline = ", ".join(str(item) for item in result["state_timeline"] if item)
        intents = ", ".join(str(item) for item in result["detected_intents"] if item)
        actions = ", ".join(str(item) for item in result["detected_actions"] if item)
        story.append(Paragraph(f"State timeline: {timeline or 'n/a'}", styles["Small"]))
        story.append(Paragraph(f"Detected intents: {intents or 'n/a'}", styles["Small"]))
        story.append(Paragraph(f"Detected actions: {actions or 'n/a'}", styles["Small"]))

        transcript_lines = []
        for message in result["transcript"][:8]:
            role = "AI" if message["role"] == "assistant" else "Patient"
            transcript_lines.append(f"{role}: {message['content']}")
        if len(result["transcript"]) > 8:
            transcript_lines.append("... transcript truncated in PDF; full transcript in JSON.")
        story.append(Paragraph("<br/>".join(escape_pdf(line) for line in transcript_lines), styles["Small"]))
        story.append(Spacer(1, 0.12 * inch))

    doc.build(story)


def make_table(rows: List[List[Any]], widths: List[float], header: bool = False) -> Table:
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7") if header else colors.white),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold" if header else "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]
    table.setStyle(TableStyle(style))
    return table


def escape_pdf(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def main() -> None:
    report = await run_scenarios()
    write_json_report(report)
    write_pdf_report(report)
    print(json.dumps({
        "scenario_count": report["summary"]["scenario_count"],
        "turn_count": report["summary"]["turn_count"],
        "overall_score": report["summary"]["overall_score"],
        "failed_scenarios": report["summary"]["failed_scenarios"],
        "pdf": str(PDF_REPORT),
        "json": str(JSON_REPORT),
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
