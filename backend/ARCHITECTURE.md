# ARCHITECTURE GUIDE

## Overview

This is a production-ready FastAPI backend for a realtime voice AI receptionist system. The architecture is designed for:

- **Modularity**: Clear separation of concerns
- **Reusability**: Services can be used independently
- **Testability**: Each layer can be tested in isolation
- **Performance**: Optimized for realtime operations
- **Maintainability**: Clean code with proper typing

---

## Architecture Layers

### 1. **Models Layer** (`app/models/`)

**Purpose**: Define Pydantic data structures for validation and serialization

**Files**:
- `doctor.py` - Doctor and doctor check models
- `appointment.py` - Appointment booking models

**Why Pydantic**:
- Automatic request validation
- Type hints and IDE support
- Automatic OpenAPI schema generation
- Built-in serialization

**Example**:
```python
class BookAppointmentRequest(AppointmentBase):
    """Request model for booking appointment"""
    pass
```

---

### 2. **Routes Layer** (`app/routes/`)

**Purpose**: Handle HTTP requests and responses

**Files**:
- `doctors.py` - Doctor availability endpoints
- `appointments.py` - Appointment booking endpoints

**Responsibilities**:
- Accept HTTP requests
- Parse request data (Pydantic handles this)
- Call service layer
- Return HTTP responses

**Design Pattern**:
```python
@router.post("/book")
async def book_appointment(request: BookAppointmentRequest):
    result = booking_service.book_appointment(...)
    return result
```

---

### 3. **Services Layer** (`app/services/`)

**Purpose**: Implement business logic and coordinate operations

**Files**:
- `sheets_service.py` - Google Sheets CRUD operations
- `doctor_service.py` - Doctor business logic
- `booking_service.py` - Appointment booking logic

**Responsibilities**:
- Validate business rules
- Coordinate multiple data sources
- Handle errors gracefully
- Log operations

**Example Flow for Booking**:
```
BookingService.book_appointment()
  ├─ Validate inputs
  ├─ Call DoctorService to check existence
  ├─ Call DoctorService to check availability
  ├─ Call SheetsService to check duplicates
  ├─ Call SheetsService to write appointment
  └─ Return result
```

---

### 4. **Utils Layer** (`app/utils/`)

**Purpose**: Provide shared utilities and helpers

**Files**:
- `logger.py` - Structured JSON logging
- `validators.py` - Input validation functions

**Key Functions**:
- `validate_phone()` - Check phone format
- `validate_date()` - Check date format
- `get_logger()` - Get logger instance

---

### 5. **Configuration** (`app/config.py`)

**Purpose**: Load and manage environment variables

**Uses**:
- `pydantic-settings` for type-safe config
- `.env` file for local development
- Environment variables for production

**Design**:
```python
class Settings(BaseSettings):
    GOOGLE_SHEETS_CREDENTIALS_PATH: str
    GOOGLE_SHEET_NAME: str
    # ... other settings
```

---

### 6. **Main App** (`app/main.py`)

**Purpose**: Create FastAPI instance and wire everything together

**Responsibilities**:
- Initialize FastAPI app
- Setup middleware (CORS)
- Setup exception handlers
- Initialize services
- Include routers

**Startup Sequence**:
```
main.py startup
  ├─ Create FastAPI instance
  ├─ Add CORS middleware
  ├─ Create global exception handler
  ├─ Initialize SheetsService (lifespan)
  └─ Include routers
```

---

## Data Flow

### Appointment Booking Flow

```
HTTP Request
    ↓
[Routes] book_appointment()
    ↓
[Pydantic] Validate request data
    ↓
[Routes] Call BookingService
    ↓
[Services] validate_booking_request()
    ├─ Validate phone format
    ├─ Validate date format
    └─ Return (is_valid, error_message)
    ↓
[Services] doctor_service.doctor_exists()
    ├─ Call SheetsService.read_all_records()
    └─ Search doctor in records
    ↓
[Services] doctor_service.is_slot_available()
    ├─ Check doctor availability from sheets
    └─ Return True/False
    ↓
[Services] sheets_service.check_duplicate()
    ├─ Query appointments sheet
    └─ Check for existing booking
    ↓
[Services] sheets_service.write_row()
    ├─ Append to appointments sheet
    └─ Return True/False
    ↓
[Routes] Return JSON response
    ↓
HTTP Response
```

---

## Design Patterns

### 1. **Dependency Injection**

Services receive dependencies as constructor parameters:

```python
def __init__(self, sheets_service: SheetsService, doctor_service: DoctorService):
    self.sheets_service = sheets_service
    self.doctor_service = doctor_service
```

**Benefits**:
- Easy to test (mock dependencies)
- Services are loosely coupled
- Easy to swap implementations

### 2. **Factory Pattern**

Router creation functions return configured routers:

```python
def create_doctors_router(sheets_service: SheetsService) -> APIRouter:
    router = APIRouter(prefix="/doctors", tags=["doctors"])
    # ... define endpoints
    return router
```

### 3. **Singleton Pattern**

Global service instances initialized at startup:

```python
sheets_service = None  # Global

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sheets_service
    sheets_service = SheetsService(...)  # Initialize once
    yield
    # Cleanup if needed
```

---

## Error Handling Strategy

### Validation Errors (User Input)
- **Return**: 422 Unprocessable Entity (Pydantic automatic)
- **Message**: "Phone number must be 10 digits"

### Business Logic Errors (Domain Rules)
- **Return**: 200 OK with status: "failed"
- **Message**: "Slot unavailable"

### System Errors (Server Issues)
- **Return**: 500 Internal Server Error
- **Message**: "Internal server error" (don't expose details)

### Logging

```python
# Log at appropriate levels
logger.info("Doctor check requested")      # Info - normal flow
logger.warning("Doctor not found")         # Warning - expected but notable
logger.error("Google Sheets connection failed")  # Error - unexpected
```

---

## Performance Considerations

### 1. **Lightweight Operations**

Each endpoint performs minimal work:
- Doctor check: Single row search (milliseconds)
- Appointment book: Validation + single write (< 1 second)

### 2. **No Blocking Operations**

All operations are I/O bound but not CPU intensive:
- Google Sheets API calls are reasonably fast
- No heavy computation or processing

### 3. **Async Ready**

Endpoints marked as `async` for future scalability:

```python
@router.post("/book")
async def book_appointment(request: BookAppointmentRequest):
    # Can be made truly async with async Google Sheets client
    pass
```

### 4. **Deterministic Responses**

Responses don't change based on timing or external state:
- Same input → Same output every time
- Perfect for LLM tool calling

---

## Testing Strategy

### Unit Tests

Test individual functions:
```python
def test_validate_phone():
    assert validate_phone("9876543210") == True
    assert validate_phone("123") == False
```

### Integration Tests

Test full flows:
```python
def test_book_appointment_success():
    response = requests.post("/appointments/book", json={...})
    assert response.json()["status"] == "confirmed"
```

### Sample Test File

See `tests_sample.py` for runnable integration tests

---

## Adding New Features

### To add a new endpoint:

1. **Create model** in `app/models/`
   ```python
   class MyRequest(BaseModel):
       field: str
   ```

2. **Create service** in `app/services/`
   ```python
   class MyService:
       def my_operation(self, data):
           # Business logic
           pass
   ```

3. **Create route** in `app/routes/`
   ```python
   @router.post("/my-endpoint")
   async def my_endpoint(request: MyRequest):
       result = my_service.my_operation(request.field)
       return result
   ```

4. **Include router** in `app/main.py`
   ```python
   app.include_router(create_my_router(sheets_service))
   ```

---

## Environment Setup

### Development
```
ENVIRONMENT=development
DEBUG=True
CORS_ORIGINS=["*"]
```

### Production
```
ENVIRONMENT=production
DEBUG=False
CORS_ORIGINS=["https://your-domain.com"]
```

---

## Deployment Checklist

- [ ] Change DEBUG to False
- [ ] Configure CORS properly
- [ ] Store credentials securely
- [ ] Setup monitoring/logging
- [ ] Add rate limiting
- [ ] Add authentication layer
- [ ] Test all endpoints
- [ ] Setup error alerts

---

## Key Dependencies

| Package | Purpose |
|---------|---------|
| FastAPI | Web framework |
| uvicorn | ASGI server |
| Pydantic | Data validation |
| gspread | Google Sheets API |
| oauth2client | Google authentication |
| python-dotenv | Environment variables |

---

## File Organization

```
Modularity: Services are independent
├─ sheets_service.py - Can be used standalone
├─ doctor_service.py - Depends on sheets_service
└─ booking_service.py - Depends on both above
```

Changes to one service don't affect others if interfaces stay same.

---

## Common Extension Points

### Add authentication:
- Add middleware in `main.py`
- Protect routes with decorators

### Add rate limiting:
- Use FastAPI slowapi library
- Apply to specific routes

### Add caching:
- Wrap service calls with cache
- Cache doctor list (doesn't change often)

### Add real database:
- Replace SheetsService with DatabaseService
- Keep interface same, routes unchanged

---

This architecture allows the backend to be:
- **Testable**: Mock any layer
- **Maintainable**: Clear responsibilities
- **Scalable**: Easy to add features
- **Reliable**: Proper error handling
- **Fast**: Optimized for realtime operations
