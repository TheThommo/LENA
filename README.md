# LENA - Literature and Evidence Navigation Agent

A B2B SaaS clinical research platform that gives clinicians, researchers, and academics fast access to cited, validated, unbiased medical literature.

## Quick Start (Backend)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your actual keys

# Run connection tests (no API keys needed for the 5 public sources)
python -m tests.test_connections

# Start the API server
uvicorn app.main:app --reload --port 8000
```

Then visit http://localhost:8000/docs for the interactive API docs.

## Quick Start (Frontend)

```bash
cd frontend
npm install
npm run dev
```

Then visit http://localhost:3000

## Project Structure

```
lena/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI endpoints
│   │   ├── core/
│   │   │   ├── config.py      # Environment config
│   │   │   ├── pulse_engine.py # Cross-reference validation (PULSE Engine)
│   │   │   ├── persona.py     # Persona detection and config
│   │   │   └── guardrails.py  # Medical advice guardrail
│   │   ├── services/
│   │   │   ├── pubmed.py      # PubMed/NCBI E-Utilities
│   │   │   ├── clinical_trials.py  # ClinicalTrials.gov v2
│   │   │   ├── cochrane.py    # Cochrane via PubMed
│   │   │   ├── who_iris.py    # WHO IRIS repository
│   │   │   ├── cdc.py         # CDC Open Data (Socrata)
│   │   │   └── openai_service.py   # LLM integration
│   │   ├── db/
│   │   │   └── supabase.py    # Database client
│   │   └── main.py            # FastAPI app entry
│   ├── tests/
│   │   └── test_connections.py # API connection test suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js app router
│   │   ├── components/        # React components
│   │   ├── lib/api.ts         # API client
│   │   └── styles/            # Tailwind CSS
│   └── package.json
└── docs/
```

## Data Sources

| Source | API | Key Required | Rate Limit |
|--------|-----|-------------|------------|
| PubMed/NCBI | E-Utilities | Optional (recommended) | 3-10 req/sec |
| ClinicalTrials.gov | v2 REST | No | 500 req/min |
| Cochrane | Via PubMed | No | Same as PubMed |
| WHO IRIS | DSpace REST | No | Be respectful |
| CDC Open Data | Socrata | No | Generous |

## Three Core Differentiators

1. **PULSE Engine** - Published Literature Source Evaluation across all sources
2. **Warm Guardrails** - Empathetic medical advice redirection
3. **Persona Detection** - Adapts language to user's profession

## Stack

- Frontend: Next.js + Tailwind (Vercel)
- Backend: Python + FastAPI (Railway)
- Database: Supabase + pgvector
- LLM: OpenAI API (gpt-4o-mini)
