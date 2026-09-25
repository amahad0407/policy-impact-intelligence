# Policy Impact Intelligence

AI-powered government analyst workspace for the Microsoft + CCI Innovation Challenge (Virginia, Sept 2026).

Analyzes the FTC Non-Compete Clause Rule: proposed rule, final rule, public comments, and news coverage.

## Stack

- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS
- **Backend**: Python + FastAPI
- **AI**: Azure AI Foundry (OpenAI GPT-4o, AI Search, Prompt Flow)
- **Data**: Federal Register API, Regulations.gov API, Bing News API

## Setup

### 1. Clone and configure

```bash
cp .env.example .env
# Fill in your API keys (see sections below)
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

## API Keys You Need

| Service | Where to get it | Cost | Notes |
|---|---|---|---|
| regulations.gov | https://api.data.gov/signup/ | Free | Same-day approval |
| Azure OpenAI | Azure portal → AI Foundry | Pay-per-use | Need Azure subscription |
| Azure AI Search | Azure portal | Free tier available | |
| Bing News Search | Azure portal → Cognitive Services | 1,000 free/month | |

## Data Collection

Run these once before starting the backend server:

```bash
cd backend
source venv/bin/activate

# Step 1: Fetch Federal Register documents (no key needed)
python scripts/fetch_federal_register.py

# Step 2: Fetch a sample of public comments (needs REGULATIONS_API_KEY in .env)
python scripts/fetch_comments.py
```

Output files in `data/raw/`:
- `federal_register_proposed_rule.json` — proposed rule, Jan 2023
- `federal_register_final_rule.json` — final rule, May 2024
- `regulations_comments_sample.json` — 20 public comments

## Running Locally

```bash
# Terminal 1 — backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

## Project Structure

```
policy-impact-intelligence/
├── frontend/          # Next.js app
│   └── src/
│       ├── app/       # App Router pages
│       ├── components/
│       └── types/
├── backend/
│   ├── app/           # FastAPI application
│   │   ├── main.py
│   │   └── routers/
│   └── scripts/       # One-time data collection
│       ├── fetch_federal_register.py
│       └── fetch_comments.py
├── data/
│   ├── raw/           # Downloaded from APIs
│   └── processed/     # AI-analyzed output
└── .env.example
```
