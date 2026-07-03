from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ConversationMessage(BaseModel):
    """Single message in a conversation"""
    role: str = Field(..., description="Role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Timestamp of message")


class ConversationRequest(BaseModel):
    """Request for conversation/chat"""
    client_id: str = Field(..., min_length=1, description="Client/hospital identifier")
    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for continuity")


class ConversationResponse(BaseModel):
    """Response from conversation processing"""
    success: bool
    response: Optional[str] = Field(None, description="AI response text")
    conversation_id: str = Field(..., description="Conversation identifier")
    client_id: str = Field(..., description="Client identifier")
    tools_used: Optional[List[str]] = Field(None, description="Tools executed")
    tool_calls_executed: Optional[int] = Field(None, description="Number of tool calls")
    error: Optional[str] = Field(None, description="Error message if any")


class ConversationHistoryRequest(BaseModel):
    """Request to get conversation history"""
    conversation_id: str = Field(..., description="Conversation ID")


class ConversationHistoryResponse(BaseModel):
    """Response with conversation history"""
    success: bool
    conversation_id: str
    messages: Optional[List[ConversationMessage]] = None
    error: Optional[str] = None


class ClientMetadataResponse(BaseModel):
    """Client metadata response"""
    name: str
    location: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[str] = None
    specialties: Optional[List[str]] = None
    language: str = "English"
    timezone: str = "UTC"


class ClientInfoRequest(BaseModel):
    """Request for client information"""
    client_id: str = Field(..., description="Client identifier")
