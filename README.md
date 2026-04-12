# Resume Intelligence Platform

A full-stack web application for AI-powered resume evaluation, profile verification, and interview practice. Designed for recruiters and hiring teams to assess candidates against job descriptions using LLM-based scoring and real-world profile data.

---

## Features

- **Resume Parsing** — Extracts name, email, phone, experience, and profile links from PDF, DOCX, and TXT files
- **ATS Match Scoring** — Combines semantic similarity (ChromaDB embeddings) with LLM evaluation (Cohere) to produce a final match score against a job description
- **Profile Verification** — Fetches live data from GitHub and LeetCode to cross-check resume-claimed skills, scored via Gemini
- **AI Interview Practice** — Generates personalized interview questions from an uploaded resume, evaluates answers, and produces a final performance report
- **Scan History** — All resume evaluations are saved per user for later review
- **Authentication** — JWT-based login and signup, with Google OAuth support

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.9+ |
| Database | PostgreSQL, SQLAlchemy |
| Caching | Redis |
| AI / LLM | Cohere (Command R+ and v3.0 embeddings), Google Gemini (2.0 Flash) |
| Vector Store | ChromaDB |
| Frontend | React + Vite |
| Auth | OAuth2, JWT (python-jose, passlib) |
| Infrastructure | Docker Compose |

---

## Project Structure

```
resume/
├── docker-compose.yml          # Spins up PostgreSQL and Redis
├── requirements.txt            # Root-level Python dependencies
├── backend/
│   ├── main.py                 # FastAPI app, all route definitions
│   ├── db.py                   # Database connection and session
│   ├── auth.py                 # JWT and password utilities
│   ├── oauth.py                # Google OAuth configuration
│   ├── redis_client.py         # Redis connection
│   ├── queries/
│   │   └── tables.sql          # Database schema
│   └── services/
│       ├── models.py           # SQLAlchemy models
│       ├── schemas.py          # Pydantic schemas
│       ├── parser_service.py   # Resume parsing and ATS scoring (Cohere)
│       ├── interviewer_service.py  # AI interview logic (Gemini)
│       ├── verification_service.py # Profile verification scoring (Gemini)
│       ├── profile_service.py  # Profile URL classification and analysis
│       ├── github_fetcher.py   # GitHub API integration
│       ├── leetcode_fetcher.py # LeetCode API integration
│       └── linkedin_extraction.py  # LinkedIn profile extraction
└── frontend/
    ├── index.html
    ├── package.json
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── Dashboard.jsx
        │   ├── ResumeParser.jsx
        │   ├── AIInterviewer.jsx
        │   ├── ProfileVerification.jsx
        │   ├── Login.jsx
        │   └── Signup.jsx
        └── index.css
```

---

## How It Works

### Resume Matching

1. User uploads a resume (PDF, DOCX, or TXT) along with a job description
2. The backend extracts text, chunks it, and generates embeddings via Cohere
3. A semantic similarity score is computed against the job description using ChromaDB
4. Cohere's LLM independently evaluates the resume to identify strengths and missing skills
5. Both scores are combined into a final match percentage
6. The result is saved to the user's scan history

### Profile Verification

1. GitHub and LeetCode URLs are extracted from the parsed resume
2. Live data is fetched from both platforms (repositories, languages, solved problems)
3. The fetched profile data and resume-claimed skills are sent to Gemini
4. Gemini returns a verification score and a breakdown of corroborated vs unverified skills

### AI Interview

1. User uploads a resume PDF
2. Gemini generates five personalized interview questions based on the resume content
3. The user answers each question in the UI
4. Each answer is evaluated by Gemini for relevance, depth, and accuracy
5. A final report with an overall score and per-question feedback is returned

---

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker and Docker Compose

### Environment Variables

Create a `.env` file in the root directory:

```env
COHERE_API_KEY=your_cohere_api_key
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/parser_db
SESSION_SECRET=your_session_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
FRONTEND_URL=http://localhost:5173
```

### 1. Start the Database and Redis

```bash
docker-compose up -d
```

This starts PostgreSQL on port `5432` and Redis on port `6379`.

### 2. Backend

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
cd backend
uvicorn main:app --reload
```

Backend runs at: `http://localhost:8000`  
API docs available at: `http://localhost:8000/docs`

### 3. Frontend

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Register a new user |
| POST | `/auth/token` | Login and receive JWT |
| GET | `/auth/google` | Initiate Google OAuth |
| POST | `/api/parse` | Parse resume and match to job description |
| GET | `/api/history` | Get all past scans for current user |
| GET | `/api/me` | Get current user info |
| POST | `/api/interview/start` | Upload resume and get interview questions |
| POST | `/api/interview/evaluate` | Evaluate a single answer |
| POST | `/api/interview/report` | Generate final interview report |
| POST | `/api/analyze-profiles` | Analyze GitHub and LeetCode profile URLs |
| POST | `/api/verify-profiles` | Score skill verification against profile data |
| GET | `/github` | Fetch GitHub data for the latest scanned resume |
| GET | `/leetcode` | Fetch LeetCode data for the latest scanned resume |

---

## Notes

- The `chroma_db/` directory is auto-generated and stores temporary vector embeddings locally
- Resume files are processed in memory and not stored on disk beyond the request lifecycle
- All scan results are persisted in PostgreSQL and tied to the authenticated user
