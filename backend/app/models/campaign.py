from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CampaignImportRequest(BaseModel):
    """Request to import or inspect a campaign sheet."""

    campaign_id: str = Field(..., min_length=1, description="Campaign identifier")
    sheet_title: Optional[str] = Field(None, description="Worksheet title to read")
    column_map: Optional[Dict[str, str]] = Field(
        None,
        description="Optional backend field to spreadsheet column-name mapping",
    )


class LeadResponse(BaseModel):
    """Campaign lead returned by the campaign engine."""

    row_number: int
    patient_id: Optional[str] = None
    patient_name: str
    phone_number: str
    language: Optional[str] = None
    campaign: Optional[str] = None
    priority: Optional[str] = None
    status: str
    call_attempts: Optional[Any] = None
    last_call_time: Optional[str] = None
    next_call_time: Optional[str] = None
    assigned_agent: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class CampaignImportResponse(BaseModel):
    """Campaign import summary."""

    success: bool
    campaign_id: str
    total_leads: int = 0
    pending_leads: int = 0
    error: Optional[str] = None


class CampaignStatsResponse(BaseModel):
    """Campaign status counts."""

    campaign_id: str
    total: int
    by_status: Dict[str, int]
    by_outcome: Dict[str, int]


class NextLeadRequest(BaseModel):
    """Request the next pending lead for a campaign."""

    campaign_id: str = Field(..., min_length=1)


class NextLeadResponse(BaseModel):
    """Next pending lead response."""

    success: bool
    lead: Optional[LeadResponse] = None
    message: Optional[str] = None


class CampaignCallRequest(BaseModel):
    """Start or mark a campaign call for a lead."""

    campaign_id: str = Field(..., min_length=1)
    row_number: Optional[int] = Field(None, ge=2)
    lead_id: Optional[str] = None


class CampaignCallResponse(BaseModel):
    """Campaign call start response."""

    success: bool
    campaign_id: str
    row_number: Optional[int] = None
    status: str
    message: Optional[str] = None


class TranscriptAnalysisRequest(BaseModel):
    """Analyze a completed campaign call transcript."""

    campaign_id: str = Field(..., min_length=1)
    row_number: int = Field(..., ge=2)
    transcript: str = Field(..., min_length=1)
    call_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CallOutcome(BaseModel):
    """Structured result produced from a completed call."""

    status: str
    summary: str
    next_action: str
    follow_up_required: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sentiment: Optional[str] = None
    intent: Optional[str] = None
    notes: Optional[str] = None


class TranscriptAnalysisResponse(BaseModel):
    """Transcript analysis and Excel update result."""

    success: bool
    campaign_id: str
    row_number: int
    outcome: Optional[CallOutcome] = None
    updated: bool = False
    error: Optional[str] = None


class RetellWebhookRequest(BaseModel):
    """Normalized Retell webhook payload accepted by this backend."""

    event: str = Field(..., min_length=1)
    call_id: Optional[str] = None
    campaign_id: Optional[str] = None
    row_number: Optional[int] = None
    transcript: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)


class RetellWebhookResponse(BaseModel):
    """Webhook processing response."""

    success: bool
    event: str
    processed: bool
    message: Optional[str] = None
    analysis: Optional[CallOutcome] = None


class TrainingStartRequest(BaseModel):
    """Start a local AI campaign training session."""

    campaign_id: str = Field(..., min_length=1)
    row_number: Optional[int] = Field(None, ge=2)
    client_id: Optional[str] = Field(None, description="Optional client/hospital config id")
    prompt_key: Optional[str] = Field("campaign_calling", description="Prompt key to use")


class TrainingMessage(BaseModel):
    """Single local training conversation message."""

    role: str
    content: str
    timestamp: str


class TrainingStartResponse(BaseModel):
    """Local training session start response."""

    success: bool
    session_id: Optional[str] = None
    campaign_id: str
    lead: Optional[LeadResponse] = None
    assistant_message: Optional[str] = None
    prompt_key: Optional[str] = None
    error: Optional[str] = None


class TrainingMessageRequest(BaseModel):
    """Send patient/developer text into a local training session."""

    message: str = Field(..., min_length=1)


class TrainingMessageResponse(BaseModel):
    """AI response from a local training session."""

    success: bool
    session_id: str
    assistant_message: Optional[str] = None
    error: Optional[str] = None


class TrainingFinishRequest(BaseModel):
    """Finish a local training session and classify the outcome."""

    notes: Optional[str] = None
    update_excel: bool = True


class TrainingReportResponse(BaseModel):
    """Local training session dashboard/report."""

    success: bool
    session_id: str
    campaign_id: Optional[str] = None
    current_patient: Optional[LeadResponse] = None
    conversation_history: List[TrainingMessage] = Field(default_factory=list)
    current_outcome: Optional[CallOutcome] = None
    summary: Optional[str] = None
    confidence: Optional[float] = None
    prompt_key: Optional[str] = None
    prompt_used: Optional[str] = None
    last_plan: Optional[Dict[str, Any]] = None
    last_blueprint: Optional[Dict[str, Any]] = None
    patient_context: Dict[str, Any] = Field(default_factory=dict)
    campaign_context: Dict[str, Any] = Field(default_factory=dict)
    duration_seconds: Optional[float] = None
    updated: bool = False
    error: Optional[str] = None
