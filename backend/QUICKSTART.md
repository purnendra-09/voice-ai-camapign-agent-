# Quick Start Guide

## For Windows Users

### 1. Open PowerShell in the backend folder

```powershell
cd "c:\Users\kpurn\OneDrive\Desktop\hive minds tech solutions\backend"
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Setup Google Credentials

1. Download your Google Service Account JSON file
2. Place it in: `app/credentials/google-service-account.json`

### 5. Setup Environment Variables

```powershell
# Copy the example file
Copy-Item .env.example .env

# Edit .env with your values (use Notepad or your editor)
# - GOOGLE_SHEET_NAME=Your_Sheet_Name
```

### 6. Run the Server

**Option A: Using batch file**
```powershell
.\run.bat
```

**Option B: Using command**
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Test the Backend

Open your browser to:
```
http://localhost:8000/docs
```

---

## For macOS/Linux Users

### 1. Navigate to backend folder

```bash
cd backend
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Google Credentials

1. Download your Google Service Account JSON file
2. Place it in: `app/credentials/google-service-account.json`

### 5. Setup Environment Variables

```bash
cp .env.example .env

# Edit .env with your values
nano .env
```

### 6. Run the Server

```bash
bash run.sh
```

### 7. Test the Backend

Open your browser to:
```
http://localhost:8000/docs
```

---

## First Test

### Test Doctor Check

```bash
curl -X POST http://localhost:8000/doctors/check \
  -H "Content-Type: application/json" \
  -d '{"doctor_name": "Dr Reddy"}'
```

### Test Booking

```bash
curl -X POST http://localhost:8000/appointments/book \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Test Patient",
    "phone": "9876543210",
    "doctor_name": "Dr Reddy",
    "date": "2026-05-20",
    "time": "5 PM"
  }'
```

---

## Common Issues

**Port 8000 already in use?**
```bash
# Change port
python -m uvicorn app.main:app --port 8001
```

**Google Sheets error?**
- Share the Google Sheet with the Service Account email
- Verify the Sheet name in `.env` matches exactly

**ModuleNotFoundError?**
- Make sure virtual environment is activated
- Make sure you're in the `backend` directory

---

## Next Steps

1. ✅ Backend is running on http://localhost:8000
2. ✅ Check health: http://localhost:8000/health
3. ✅ View docs: http://localhost:8000/docs
4. ✅ Make API calls to check doctors and book appointments
5. ✅ Monitor logs in the terminal

All done! Your backend is ready for the voice AI system.
