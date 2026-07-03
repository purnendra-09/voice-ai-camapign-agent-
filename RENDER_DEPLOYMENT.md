# Render Deployment

This repo is prepared for Render with `render.yaml`.

## Services

- `voice-ai-campaign-agent-api`: FastAPI backend
- `voice-ai-campaign-agent-ui`: Vite/React static frontend

## Required Backend Environment Variables

Set these on the backend service in Render:

```env
GROQ_API_KEY=your_groq_key
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SHEET_NAME=Hospital_Campaigns
CAMPAIGN_SHEET_TITLE=Hospital Campaign
CORS_ORIGINS=https://your-render-frontend-url.onrender.com
```

`GOOGLE_SERVICE_ACCOUNT_JSON` should be the full service-account JSON pasted as one value.

## Required Frontend Environment Variable

Set this on the static frontend service:

```env
VITE_API_BASE_URL=https://your-render-backend-url.onrender.com
```

After changing `VITE_API_BASE_URL`, redeploy the frontend because Vite reads it at build time.

## Health Check

Backend health URL:

```text
https://your-render-backend-url.onrender.com/health
```

Expected response:

```json
{"status":"ok"}
```

## Notes

- The backend uses Render's `$PORT` automatically.
- The frontend has an SPA rewrite so page refreshes do not 404.
- If Google Sheets credentials are missing, the backend can still boot for health checks, but sheet-backed training routes will not be available until the Sheets env vars are configured.
