# Telugu AI Hospital Voice Receptionist - Backend

A production-ready FastAPI backend for managing doctor appointments and availability in a realtime Telugu AI voice receptionist system. **Now with integrated AI orchestration layer powered by Google Gemini**.

This backend acts as the operational layer, handling:
- **AI-powered conversations** with multi-turn dialogue management
- **Tool calling** for appointments and doctor checks
- **Multi-client support** with configurable prompts and metadata
- **Google Sheets integration** for data persistence

## Features

- ✅ **AI-Powered Conversations** - Multi-turn dialogue with Google Gemini
- ✅ **Tool Calling** - Automatic execution of appointment and doctor checks
- ✅ **Multi-Client Support** - Serve multiple hospitals with different configs
- ✅ **Dynamic Prompts** - Client-specific system prompts and personalization
- ✅ **Doctor Availability Checking** - Query doctor schedules in real-time
- ✅ **Appointment Booking** - Book appointments with validation and duplicate prevention
- ✅ **Google Sheets Integration** - Read/write operations with gspread
- ✅ **Structured JSON Responses** - Deterministic responses optimized for LLM tool calling
- ✅ **Validation & Error Handling** - Comprehensive input validation and clean error responses
- ✅ **Structured Logging** - JSON-formatted logs for debugging and monitoring
- ✅ **CORS Support** - Cross-origin resource sharing configured
- ✅ **Health Check Endpoint** - Monitor backend health
- ✅ **Clean Architecture** - Modular, testable, production-style code

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application with AI orchestration
│   ├── config.py                    # Configuration and settings
│   │
│   ├── models/                      # Pydantic models
│   │   ├── doctor.py
│   │   ├── appointment.py
│   │   ├── conversation.py          # NEW: Conversation models
│   │   └── __init__.py
│   │
│   ├── routes/                      # API endpoints
│   │   ├── doctors.py
│   │   ├── appointments.py
│   │   ├── conversation.py          # NEW: Conversation endpoints
│   │   └── __init__.py
│   │
│   ├── services/                    # Business logic
│   │   ├── sheets_service.py        # Google Sheets CRUD
│   │   ├── doctor_service.py        # Doctor operations
│   │   ├── booking_service.py       # Appointment booking
│   │   ├── gemini_service.py        # NEW: Gemini API integration
│   │   ├── prompt_manager.py        # NEW: Dynamic prompts
│   │   ├── client_manager.py        # NEW: Multi-client configs
│   │   ├── conversation_orchestrator.py  # NEW: AI orchestration
│   │   └── __init__.py
│   │
│   ├── utils/                       # Utilities
│   │   ├── logger.py                # Structured logging
│   │   ├── validators.py            # Input validation
│   │   └── __init__.py
│   │
│   └── credentials/
│       └── google-service-account.json
│
├── requirements.txt                 # Python dependencies
├── .env.example                    # Environment variables template
├── .env                            # Environment variables (create from .env.example)
├── clients_config.json             # Client configurations (provide your own)
├── prompts_config.json             # Custom prompts (provide your own)
├── run.sh                          # Run script for Linux/Mac
├── run.bat                         # Run script for Windows
├── README.md                       # This file
├── AI_INTEGRATION.md               # NEW: AI system documentation
└── QUICKSTART.md                   # Quick setup guide
```

---

## 🤖 AI Integration Overview

The backend now includes a complete **AI Orchestration Layer** powered by Google Gemini API:

### Key Components

1. **GeminiService** - Handles all Gemini API interactions
2. **PromptManager** - Manages dynamic prompt loading and personalization
3. **ClientManager** - Manages multi-client/hospital configurations
4. **ConversationOrchestrator** - Orchestrates multi-turn conversations with tool calling

### How It Works

```
User Input
    ↓
[Conversation Endpoint]
    ↓
[ConversationOrchestrator]
    ├─ Loads client-specific prompt
    ├─ Calls Gemini API with tools
    ├─ Detects & executes tools (book appointment, check doctor)
    ├─ Manages conversation history
    └─ Returns structured response
```

### New Endpoints

- `POST /conversation/chat` - Send message, get AI response with tool execution
- `GET /conversation/history?conversation_id=xxx` - Get conversation history
- `POST /conversation/client-info` - Get client/hospital metadata
- `GET /conversation/clients` - List all configured clients

**→ See [AI_INTEGRATION.md](AI_INTEGRATION.md) for complete AI documentation**

---

## Prerequisites

- **Python 3.12+**
- **Google Cloud Project** with Sheets API enabled
- **Google Service Account** with credentials
- **Google Sheet** with proper structure
- **Google Gemini API Key** (for AI features) - [Get here](https://makersuite.google.com/app/apikey)

---

## Setup Instructions

### Step 1: Clone or Create Project

```bash
cd backend
```

### Step 2: Create Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Google Sheets Setup

#### 4.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the **Google Sheets API**
4. Create a **Service Account**:
   - Go to "Service Accounts"
   - Click "Create Service Account"
   - Name it (e.g., "Hospital Backend")
   - Create a key: JSON format
5. Download the JSON credentials file

#### 4.2 Create Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet (name it `Hospital_Appointments` or your preference)
3. Share the sheet with the Service Account email (found in JSON credentials)
4. Create two tabs:

**Tab 1: Doctors**
```
| doctor_name | department | timings | available |
| Dr Reddy | Cardiology | 5 PM - 8 PM | Yes |
| Dr Sharma | Orthopedics | 9 AM - 12 PM | Yes |
| Dr Patel | Neurology | 2 PM - 5 PM | Yes |
```

**Tab 2: Appointments**
```
| patient_name | phone | doctor_name | date | time | created_at |
(Leave empty - appointments will be written here)
```

### Step 5: Environment Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and fill in your values:
```env
ENVIRONMENT=development
DEBUG=True

# Your Google Service Account JSON path
GOOGLE_SHEETS_CREDENTIALS_PATH=app/credentials/google-service-account.json

# Your Google Sheet name
GOOGLE_SHEET_NAME=Hospital_Appointments

CORS_ORIGINS=["*"]
```

3. Place the Google Service Account JSON in `app/credentials/`:
```bash
# Copy your downloaded JSON file
cp /path/to/service-account.json app/credentials/google-service-account.json
```

### Step 6: AI Configuration (Optional but Recommended)

For AI-powered conversations:

1. **Get Gemini API Key**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create API key
   - Add to `.env`:
   ```env
   GEMINI_API_KEY=your-gemini-api-key-here
   GEMINI_MODEL=gemini-pro
   ```

2. **Provide Client Configurations** (Optional)
   - Create `clients_config.json` with your hospital/client metadata
   - See [AI_INTEGRATION.md](AI_INTEGRATION.md) for format

3. **Provide Custom Prompts** (Optional)
   - Create `prompts_config.json` with your custom prompts
   - See [AI_INTEGRATION.md](AI_INTEGRATION.md) for examples

**Note**: If `GEMINI_API_KEY` is not set, appointment booking and doctor checking endpoints still work. AI conversation features will be disabled.

### Step 7: Run the Server

**On macOS/Linux:**
```bash
bash run.sh
```

**On Windows (PowerShell):**
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server will start at: **http://localhost:8000**

---

## API Documentation

### Interactive Docs

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### 1. Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

---

#### 2. Check Doctor Availability

```http
POST /doctors/check
Content-Type: application/json

{
  "doctor_name": "Dr Reddy"
}
```

**Success Response:**
```json
{
  "doctor_name": "Dr Reddy",
  "available": true,
  "time": "5 PM - 8 PM",
  "department": "Cardiology"
}
```

**Doctor Not Found:**
```json
{
  "available": false,
  "message": "Doctor not found"
}
```

---

#### 3. Get All Doctors

```http
GET /doctors/all
```

**Response:**
```json
{
  "doctors": [
    {
      "doctor_name": "Dr Reddy",
      "department": "Cardiology",
      "timings": "5 PM - 8 PM",
      "available": "Yes"
    }
  ],
  "count": 1
}
```

---

#### 4. Book Appointment

```http
POST /appointments/book
Content-Type: application/json

{
  "patient_name": "Ravi Kumar",
  "phone": "9876543210",
  "doctor_name": "Dr Reddy",
  "date": "2026-05-19",
  "time": "5 PM"
}
```

**Success Response:**
```json
{
  "status": "confirmed",
  "doctor_name": "Dr Reddy",
  "date": "2026-05-19",
  "time": "5 PM",
  "patient_name": "Ravi Kumar"
}
```

**Failure Response:**
```json
{
  "status": "failed",
  "message": "Slot unavailable"
}
```

---

#### 5. Get All Appointments

```http
GET /appointments/all
```

**Response:**
```json
{
  "appointments": [
    {
      "patient_name": "Ravi Kumar",
      "phone": "9876543210",
      "doctor_name": "Dr Reddy",
      "date": "2026-05-19",
      "time": "5 PM",
      "created_at": "2026-05-18T10:30:00.000000"
    }
  ],
  "count": 1
}
```

---

## cURL Examples

### Check Doctor Availability

```bash
curl -X POST http://localhost:8000/doctors/check \
  -H "Content-Type: application/json" \
  -d '{"doctor_name": "Dr Reddy"}'
```

### Book Appointment

```bash
curl -X POST http://localhost:8000/appointments/book \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Ravi Kumar",
    "phone": "9876543210",
    "doctor_name": "Dr Reddy",
    "date": "2026-05-19",
    "time": "5 PM"
  }'
```

### Get All Doctors

```bash
curl http://localhost:8000/doctors/all
```

### Get All Appointments

```bash
curl http://localhost:8000/appointments/all
```

### Health Check

```bash
curl http://localhost:8000/health
```

---

## Python Requests Examples

### Check Doctor Availability

```python
import requests

response = requests.post(
    "http://localhost:8000/doctors/check",
    json={"doctor_name": "Dr Reddy"}
)
print(response.json())
```

### Book Appointment

```python
import requests

response = requests.post(
    "http://localhost:8000/appointments/book",
    json={
        "patient_name": "Ravi Kumar",
        "phone": "9876543210",
        "doctor_name": "Dr Reddy",
        "date": "2026-05-19",
        "time": "5 PM"
    }
)
print(response.json())
```

---

## Validation Rules

The backend enforces:

- ✅ **Phone**: Must be exactly 10 digits
- ✅ **Date**: Must be in `YYYY-MM-DD` format and not in the past
- ✅ **Doctor Name**: Non-empty string
- ✅ **Patient Name**: Non-empty string
- ✅ **Time**: Non-empty string
- ✅ **Duplicate Prevention**: Cannot book same patient with same doctor on same date/time
- ✅ **Doctor Existence**: Doctor must exist in database
- ✅ **Availability**: Doctor must be marked as available

---

## Error Handling

All errors return clean JSON without stack traces:

```json
{
  "status": "failed",
  "message": "Phone number must be 10 digits"
}
```

or

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Logging

Logs are structured as JSON for easy parsing:

```json
{
  "timestamp": "2026-05-18T10:30:00.000000",
  "level": "INFO",
  "message": "Checking availability for doctor: Dr Reddy",
  "logger": "app.routes.doctors"
}
```

View logs in the terminal where the server is running.

---

## Testing Locally

### Manual Testing

1. Start the server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Open Swagger UI:
```
http://localhost:8000/docs
```

3. Test endpoints directly from the UI

### Integration Testing

```python
# test_integration.py
import requests

BASE_URL = "http://localhost:8000"

def test_doctor_check():
    response = requests.post(
        f"{BASE_URL}/doctors/check",
        json={"doctor_name": "Dr Reddy"}
    )
    assert response.status_code == 200
    print(response.json())

def test_book_appointment():
    response = requests.post(
        f"{BASE_URL}/appointments/book",
        json={
            "patient_name": "Test Patient",
            "phone": "9876543210",
            "doctor_name": "Dr Reddy",
            "date": "2026-05-20",
            "time": "5 PM"
        }
    )
    assert response.status_code == 200
    print(response.json())

if __name__ == "__main__":
    test_doctor_check()
    test_book_appointment()
```

Run tests:
```bash
python test_integration.py
```

---

## Production Deployment

### Security Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Use strong CORS restrictions: `CORS_ORIGINS=["https://your-frontend-domain.com"]`
- [ ] Store credentials in secure secret management (not in repo)
- [ ] Use environment variables for all secrets
- [ ] Add rate limiting
- [ ] Enable HTTPS
- [ ] Add authentication/authorization layer
- [ ] Set up monitoring and alerts

### Deployment Options

1. **Docker** - Create Dockerfile for containerization
2. **Cloud Run** - Google Cloud Run for serverless deployment
3. **AWS Lambda** - Use Mangum adapter for Lambda
4. **Heroku** - Deploy with Procfile
5. **VPS** - Use systemd, nginx reverse proxy, SSL certificate

---

## Troubleshooting

### Google Sheets Error

**Error:** `gspread.exceptions.APIError: [403] Forbidden`

**Solution:** 
- Share Google Sheet with Service Account email
- Ensure Service Account has Editor access
- Check credentials file path is correct

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Change port in .env or command:
python -m uvicorn app.main:app --port 8001
```

### Module Not Found

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Make sure you're in the backend directory:
cd backend
python -m uvicorn app.main:app --reload
```

### Import Error: pydantic

**Error:** `ImportError: cannot import name 'BaseSettings'`

**Solution:**
```bash
pip install pydantic-settings
pip install pydantic==2.5.0
```

---

## Environment Variables Reference

```env
# Application
ENVIRONMENT          # "development" or "production"
DEBUG               # True or False
HOST                # Server host (0.0.0.0)
PORT                # Server port (8000)

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH  # Path to JSON credentials
GOOGLE_SHEET_NAME               # Google Sheet document name

# CORS
CORS_ORIGINS        # List of allowed origins
CORS_CREDENTIALS    # Allow credentials
CORS_METHODS        # Allowed HTTP methods
CORS_HEADERS        # Allowed headers
```

---

## Performance Notes

This backend is optimized for realtime voice AI:
- ✅ Lightweight endpoints with minimal processing
- ✅ Fast Google Sheets reads/writes
- ✅ Deterministic responses for LLM tool calling
- ✅ Structured, non-ambiguous JSON responses
- ✅ Async endpoints ready for high concurrency

---

## Support

For issues, questions, or improvements:
1. Check the troubleshooting section
2. Review logs for error details
3. Test endpoints in Swagger UI
4. Verify Google Sheets setup

---

## License

This project is part of Telugu AI Hospital Voice Receptionist system.

---

## Version History

- **v1.0.0** (May 2026) - Initial release with doctor availability and appointment booking
