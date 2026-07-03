# AI Integration Guide - Multi-Client AI Runtime System

## Overview

The backend now owns the AI orchestration layer, integrating Google Gemini API for intelligent conversation management. The system supports multiple clients/hospitals with configurable prompts and metadata.

---

## Architecture

### AI Runtime Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Conversation Endpoint                     │
│               (Receives user input + client_id)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           ConversationOrchestrator                            │
│  - Manages conversation flow                                 │
│  - Handles tool calling                                      │
│  - Manages conversation history                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                   ▼
    ┌────────────┐  ┌────────────┐  ┌────────────────┐
    │ Gemini API │  │ Prompt     │  │ Client         │
    │ Service    │  │ Manager    │  │ Manager        │
    └────────────┘  └────────────┘  └────────────────┘
        │                │                   │
        │ generates      │ loads prompts    │ loads metadata
        │                │                   │
        ▼                ▼                   ▼
    ┌─────────────────────────────────────────────────────┐
    │        Tool Execution Layer                          │
    │  - check_doctor_availability()                      │
    │  - book_appointment()                               │
    │  - get_all_doctors()                                │
    └──────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ Doctor   │  │ Booking  │  │ Sheets   │
   │ Service  │  │ Service  │  │ Service  │
   └──────────┘  └──────────┘  └──────────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
              ┌─────────────────┐
              │ Google Sheets   │
              │ (Data Store)    │
              └─────────────────┘
```

---

## Key Services

### 1. GeminiService
**Purpose**: Handles all Gemini API interactions

```python
gemini = GeminiService(api_key="your-key", model="gemini-pro")

response = await gemini.generate_content(
    prompt="Check if Dr Reddy is available",
    system_prompt="You are a hospital receptionist",
    tools=[...],  # Optional tool definitions
)

text = await gemini.extract_response_text(response)
tool_calls = await gemini.extract_tool_calls(response)
```

**Features**:
- Async API calls
- Tool/function calling support
- Response parsing
- Timeout handling
- Error logging

### 2. PromptManager
**Purpose**: Manages dynamic prompt loading and generation

```python
prompts = PromptManager()

# Get pre-built prompt
prompt = prompts.get_prompt("appointment_booking")

# Generate personalized system prompt
system_prompt = prompts.generate_system_prompt(
    base_prompt=prompt,
    client_name="Apollo Hospital",
    client_context={
        "specialties": ["Cardiology", "Orthopedics"],
        "location": "Chennai",
        "phone": "044-XXXX-XXXX",
        "hours": "9 AM - 9 PM",
    }
)

# Load custom prompts from file
prompts.load_from_file("prompts.json")
```

**Available Prompts**:
- `default` - General assistant
- `appointment_booking` - Specialized for bookings
- `doctor_availability` - Doctor inquiry focused
- `general_assistance` - General support

### 3. ClientManager
**Purpose**: Manages multi-client configurations

```python
clients = ClientManager()

# Get client configuration
client = clients.get_client("apollo_hospital")

# Get client metadata for personalization
metadata = clients.get_client_metadata("apollo_hospital")

# Check if client exists
exists = clients.client_exists("apollo_hospital")

# Get sheet ID for data operations
sheet_id = clients.get_client_sheet_id("apollo_hospital")

# Load clients from configuration file
clients.load_from_file("clients.json")
```

**Client Configuration**:
```json
{
  "apollo_hospital": {
    "name": "Apollo Hospital",
    "location": "Chennai, Tamil Nadu",
    "phone": "044-XXXX-XXXX",
    "hours": "9 AM - 9 PM",
    "specialties": ["General", "Cardiology"],
    "language": "Telugu",
    "timezone": "IST",
    "google_sheet_id": "apollo_sheet_id",
    "prompt_key": "appointment_booking"
  }
}
```

### 4. ConversationOrchestrator
**Purpose**: Orchestrates multi-turn conversations with tool calling

```python
orchestrator = ConversationOrchestrator(
    gemini_service=gemini,
    prompt_manager=prompts,
    client_manager=clients,
    booking_service=booking,
    doctor_service=doctors,
)

# Process a conversation
result = await orchestrator.process_conversation(
    user_input="I want to book an appointment",
    client_id="apollo_hospital",
    conversation_id="conv-123",  # Optional, for continuity
    max_iterations=3,  # Max tool calling iterations
)

# Get conversation history
history = orchestrator.get_conversation_history("conv-123")
```

**Defined Tools**:
1. `check_doctor_availability` - Check if doctor is available
2. `book_appointment` - Book an appointment
3. `get_all_doctors` - List all doctors

---

## API Endpoints

### 1. Chat Endpoint (NEW)

```http
POST /conversation/chat
Content-Type: application/json

{
  "client_id": "apollo_hospital",
  "message": "I want to book an appointment with Dr. Reddy",
  "conversation_id": "optional-conv-id"
}
```

**Response**:
```json
{
  "success": true,
  "response": "I'll help you book an appointment with Dr. Reddy. Let me check availability.",
  "conversation_id": "conv-123",
  "client_id": "apollo_hospital",
  "tools_used": ["check_doctor_availability"],
  "tool_calls_executed": 1
}
```

### 2. Conversation History Endpoint (NEW)

```http
GET /conversation/history?conversation_id=conv-123
```

**Response**:
```json
{
  "success": true,
  "conversation_id": "conv-123",
  "messages": [
    {
      "role": "user",
      "content": "Check Dr. Reddy availability",
      "timestamp": "2026-05-18T10:30:00"
    },
    {
      "role": "assistant",
      "content": "Dr. Reddy is available from 5 PM to 8 PM today.",
      "timestamp": "2026-05-18T10:30:02"
    }
  ]
}
```

### 3. Client Info Endpoint (NEW)

```http
POST /conversation/client-info
Content-Type: application/json

{
  "client_id": "apollo_hospital"
}
```

**Response**:
```json
{
  "name": "Apollo Hospital",
  "location": "Chennai, Tamil Nadu",
  "phone": "044-XXXX-XXXX",
  "hours": "9 AM - 9 PM",
  "specialties": ["General", "Cardiology", "Orthopedics"],
  "language": "Telugu",
  "timezone": "IST"
}
```

### 4. List Clients Endpoint (NEW)

```http
GET /conversation/clients
```

**Response**:
```json
{
  "clients": [
    {
      "id": "apollo_hospital",
      "metadata": {
        "name": "Apollo Hospital",
        "location": "Chennai",
        "phone": "044-XXXX-XXXX",
        "hours": "9 AM - 9 PM",
        "specialties": ["General", "Cardiology"],
        "language": "Telugu",
        "timezone": "IST"
      }
    }
  ],
  "count": 1
}
```

---

## Tool Calling Flow

### Appointment Booking Conversation

```
User: "I want to book an appointment with Dr Reddy for tomorrow at 5 PM"
                           ↓
    [Conversation Endpoint receives message]
                           ↓
    [ConversationOrchestrator.process_conversation()]
                           ↓
    [GeminiService.generate_content() with tools]
                           ↓
    [Gemini detects: check_doctor_availability("Dr Reddy")]
                           ↓
    [Execute Tool: DoctorService.check_availability()]
                           ↓
    Result: {"available": true, "time": "5 PM - 8 PM"}
                           ↓
    [Call Gemini again with tool results]
                           ↓
    [Gemini detects: book_appointment(...details...)]
                           ↓
    [Execute Tool: BookingService.book_appointment()]
                           ↓
    Result: {"status": "confirmed", ...}
                           ↓
    [Call Gemini again with booking confirmation]
                           ↓
    Gemini Response: "Perfect! I've booked your appointment with Dr. Reddy tomorrow at 5 PM."
                           ↓
    [Return to user]
```

---

## Configuration Setup

### Step 1: Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Copy key to `.env`:

```env
GEMINI_API_KEY=your-key-here
```

### Step 2: Configure Clients

Create `clients.json`:

```json
{
  "apollo_hospital": {
    "name": "Apollo Hospital",
    "location": "Chennai, Tamil Nadu",
    "phone": "044-XXXX-XXXX",
    "hours": "9 AM - 9 PM",
    "specialties": ["General", "Cardiology", "Orthopedics"],
    "language": "Telugu",
    "timezone": "IST",
    "google_sheet_id": "apollo_sheet_id",
    "prompt_key": "appointment_booking"
  },
  "max_hospital": {
    "name": "Max Hospital",
    "location": "New Delhi",
    "phone": "011-XXXX-XXXX",
    "hours": "8 AM - 10 PM",
    "specialties": ["General", "Neurology", "Pediatrics"],
    "language": "English",
    "timezone": "IST",
    "google_sheet_id": "max_sheet_id",
    "prompt_key": "general_assistance"
  }
}
```

Then load in application:

```python
client_manager = ClientManager()
client_manager.load_from_file("clients.json")
```

### Step 3: Configure Prompts

Create `prompts.json`:

```json
{
  "custom_apollo": "You are a specialized receptionist for Apollo Hospital...",
  "custom_max": "You are a Max Hospital assistant..."
}
```

### Step 4: Update Environment

```env
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-pro
TEMPERATURE=0.7
MAX_TOKENS=1000
```

---

## Multi-Client Support

### How It Works

```
Same Backend → Multiple Clients
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
  Apollo         Max            Fortis
  Hospital       Hospital       Hospital
  (Client 1)     (Client 2)     (Client 3)
    │               │               │
    └───────────────┼───────────────┘
                    ↓
    [ConversationOrchestrator]
    - Routes to correct client config
    - Loads client-specific prompt
    - Accesses client's Google Sheet
    - Uses client's doctor data
    - Writes to client's appointments
```

### Client Switching

```python
# Same endpoint, different clients

# Apollo Hospital
response1 = await orchestrator.process_conversation(
    user_input="Book appointment",
    client_id="apollo_hospital",  # ← Different client
)

# Max Hospital
response2 = await orchestrator.process_conversation(
    user_input="Book appointment",
    client_id="max_hospital",  # ← Different client
)

# Both work independently with their own:
# - Data (Google Sheets)
# - Prompts
# - Metadata
# - Configurations
```

---

## Conversation History

### In-Memory Storage

Conversations are stored in memory during runtime:

```python
conversations = {
    "conv-id-123": {
        "client_id": "apollo_hospital",
        "created_at": "2026-05-18T10:30:00",
        "messages": [
            {"role": "user", "content": "...", "timestamp": "..."},
            {"role": "assistant", "content": "...", "timestamp": "..."},
        ]
    }
}
```

### Production Considerations

For production, implement persistent storage:

```python
# Option 1: PostgreSQL
conversation = await db.conversations.create(
    id=conversation_id,
    client_id=client_id,
    messages=[...]
)

# Option 2: MongoDB
await mongodb.conversations.insert_one({
    "_id": conversation_id,
    "client_id": client_id,
    "messages": [...]
})

# Option 3: DynamoDB
dynamodb.put_item(
    TableName="conversations",
    Item={
        "conversation_id": {"S": conversation_id},
        "client_id": {"S": client_id},
        "messages": {...}
    }
)
```

---

## Error Handling

### Gemini API Errors

```python
response = await gemini.generate_content(...)

if not response.get("success"):
    error = response.get("error")
    # Handle: timeout, invalid API key, rate limit, etc.
```

### Tool Execution Errors

```python
result = await orchestrator.execute_tool(tool_name, args)

if "error" in result:
    # Tool execution failed
    # Orchestrator will ask Gemini to handle gracefully
```

### Client Not Found

```python
if not client_manager.client_exists(client_id):
    return {
        "success": False,
        "error": "Client not found"
    }
```

---

## Performance Optimization

### 1. Caching

```python
# Cache doctor list (doesn't change often)
@cached(cache=TTLCache(maxsize=100, ttl=3600))
def get_all_doctors(client_id):
    return doctors_service.get_all_doctors()
```

### 2. Prompt Caching

```python
# Cache prompts after loading
prompt_cache = {}

def get_prompt(key):
    if key not in prompt_cache:
        prompt_cache[key] = load_from_file(key)
    return prompt_cache[key]
```

### 3. Connection Pooling

```python
# httpx automatically pools connections
client = httpx.AsyncClient()  # Reused across requests
```

### 4. Batch Operations

```python
# Fetch multiple doctors at once
doctors = sheets_service.read_all_records("Doctors")
# Instead of N individual queries
```

---

## Security Considerations

### 1. API Key Management

```env
# NEVER commit .env
GEMINI_API_KEY=secret-key

# Use secrets management in production
# - AWS Secrets Manager
# - Google Secret Manager
# - HashiCorp Vault
```

### 2. Tool Validation

```python
# Validate tool inputs before execution
required_fields = ["patient_name", "phone", "doctor_name"]
for field in required_fields:
    if field not in tool_args:
        return {"error": f"Missing field: {field}"}
```

### 3. Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/conversation/chat")
@limiter.limit("10/minute")
async def chat(request: ConversationRequest):
    ...
```

### 4. Client Isolation

```python
# Client A cannot access Client B's data
def book_appointment(client_id, sheet_id, appointment):
    # Always verify sheet belongs to client
    if clients.get_client_sheet_id(client_id) != sheet_id:
        raise PermissionError("Invalid sheet for this client")
```

---

## Testing

### Unit Tests

```python
# Test Gemini integration
@pytest.mark.asyncio
async def test_gemini_response_parsing():
    gemini = GeminiService(api_key="test-key")
    response = {
        "success": True,
        "data": {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Response text"}]
                }
            }]
        }
    }
    text = await gemini.extract_response_text(response)
    assert text == "Response text"
```

### Integration Tests

```python
# Test full conversation flow
@pytest.mark.asyncio
async def test_conversation_with_tool_calling():
    result = await orchestrator.process_conversation(
        user_input="Book appointment",
        client_id="apollo_hospital",
    )
    assert result["success"] is True
    assert len(result["tools_used"]) > 0
```

---

## Troubleshooting

### Issue: "GEMINI_API_KEY not set"

**Solution**: Add to `.env`:
```env
GEMINI_API_KEY=your-actual-key-here
```

### Issue: Tool calls not executing

**Reason**: Gemini model might not support function calling

**Solution**: Ensure using correct model version:
```env
GEMINI_MODEL=gemini-pro
```

### Issue: Client not found

**Solution**: Add client to configuration:
```python
client_manager.add_client("new_hospital", {
    "name": "New Hospital",
    "location": "...",
    ...
})
```

### Issue: Slow responses

**Solution**:
1. Check Gemini API latency
2. Optimize tool execution
3. Cache frequently accessed data
4. Consider request batching

---

## Example Conversations

### Booking Appointment

```
User: "I need an appointment with the cardiologist"

AI: "I'll help you book with our cardiologist. Let me check availability."
[Tool: check_doctor_availability("Cardiologist")]
Result: {"available": true, "time": "3 PM - 6 PM"}

AI: "Great! The cardiologist is available from 3 PM to 6 PM. 
What's your preferred time and what's your name and phone number?"

User: "4 PM works, I'm Ravi Kumar, 9876543210"

AI: "Perfect! I'm booking your appointment."
[Tool: book_appointment("Ravi Kumar", "9876543210", "Cardiologist", "2026-05-20", "4 PM")]
Result: {"status": "confirmed"}

AI: "Your appointment is confirmed! 
Dr. [Cardiologist Name] on May 20th at 4 PM. 
See you soon!"
```

---

## Production Deployment

### Environment Setup

```env
ENVIRONMENT=production
DEBUG=False
GEMINI_API_KEY=prod-key
CORS_ORIGINS=["https://your-domain.com"]
```

### Scaling

1. **Horizontal Scaling**: Run multiple backend instances
2. **Session Persistence**: Use Redis for conversation storage
3. **Monitoring**: Track API latency, errors, tool calls
4. **Caching**: Cache prompts, client configs, doctor lists

---

## Next Steps

1. ✅ Integrate Gemini API key
2. ✅ Configure client metadata
3. ✅ Set up custom prompts
4. ✅ Test conversation flows
5. ✅ Deploy to production
6. ✅ Monitor and optimize
