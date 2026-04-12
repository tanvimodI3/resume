# AI-Powered Resume

## forreal.

## Overview

The AI-Powered Resume ATS is a full-stack, intelligent web application built to help technical recruiters, HR professionals, and administrators streamline their hiring process. By leveraging large language models (LLMs) and vector databases, the application compares candidate resumes against given job descriptions (JDs) and automatically generates match scores, identifies missing skills, and extracts essential candidate information.

The system also verifies candidate profiles by analyzing real developer activity from platforms such as GitHub and LeetCode.
(Built during a hackathon for the classic impressive… impressive… wait? maybe we should run some analysis.)

---

## Key Features

### Intelligent Resume Parsing

Automatically extracts candidate details such as:

* Name
* Email
* Phone
* Experience
* Profiles (LinkedIn, GitHub, LeetCode)

from uploaded resumes.

Supported formats:

* PDF
* DOCX
* TXT

The parsing pipeline extracts the structured information and prepares it for downstream analysis.

---

### AI-Powered Evaluation

Uses LangChain and Cohere's advanced LLMs to analyze the candidate resume against a given job description.

The system:

* Identifies candidate strengths
* Highlights missing skills
* Produces a summarized evaluation

This helps recruiters quickly understand candidate fit beyond simple keyword matching.

---

### Semantic Matching (Vector Search)

Resume content is split into chunks and embedded using Cohere Embeddings.

These embeddings are stored in **ChromaDB**, where semantic similarity search is performed against the job description to calculate a contextual match score.

The resulting score reflects how closely the candidate aligns with the JD (instead of blindly rewarding whoever mentioned “Python” the most times).

---

### Developer Profile Verification

The platform verifies developer claims by analyzing public profile data.

If the resume includes profile links, the system fetches information from:

* GitHub
* LeetCode
* LinkedIn

GitHub repositories, languages, and activity are analyzed.
LeetCode problem-solving statistics are retrieved.
LinkedIn profile data is extracted for additional validation.

This information is then evaluated using Gemini to generate a **verification score**, comparing resume claims with actual activity (because “proficient in distributed systems” should ideally involve… distributing something).

---

### AI Interview Practice

The platform can generate personalized interview questions based on the uploaded resume.

Workflow:

1. Resume is uploaded
2. Gemini generates interview questions tailored to the resume
3. The user answers them in the interface
4. Gemini evaluates each answer
5. A final performance report is generated

The report includes feedback on accuracy, depth, and relevance.

---

### Secure Authentication

JWT-based secure signup and login flows for admins and recruiters.

Authentication includes:

* password hashing
* JWT token generation
* Google OAuth login support

Each user's evaluation history is isolated and securely stored.

---

### History Tracking

All previously scanned resumes and evaluations are stored in the PostgreSQL database.

Recruiters can revisit previous candidate analyses at any time (because losing past evaluations would be… extremely awkward).

To improve performance and reduce repeated heavy processing, Redis is used as a caching layer for frequently accessed evaluation data and intermediate processing states (because asking the AI the same question five times is impressive, but inefficient).

---

## Tech Stack

| Layer          | Technology                                           |
| -------------- | ---------------------------------------------------- |
| Backend        | FastAPI, Python                                      |
| Database       | PostgreSQL, SQLAlchemy                               |
| Caching        | Redis                                                |
| AI / LLM       | Cohere (Command R+ and v3 embeddings), Google Gemini |
| Vector Store   | ChromaDB                                             |
| Frontend       | React + Vite                                         |
| Auth           | OAuth2, JWT (python-jose, passlib)                   |
| Infrastructure | Docker Compose                                       |

---
## Infrastructure (Docker)

Docker Compose is used to run supporting services like **PostgreSQL** and **Redis** in containers, so the project can be set up quickly without manually installing or configuring these dependencies.

---

resume/
├── docker-compose.yml
├── requirements.txt
├── backend/
│   ├── main.py
│   ├── db.py
│   ├── auth.py
│   ├── oauth.py
│   ├── redis_client.py
│   ├── queries/
│   │   └── tables.sql
│   └── services/
│       ├── models.py
│       ├── schemas.py
│       ├── parser_service.py
│       ├── interviewer_service.py
│       ├── verification_service.py
│       ├── profile_service.py
│       ├── github_fetcher.py
│       ├── leetcode_fetcher.py
│       └── linkedin_extraction.py
└── frontend/
    ├── index.html
    ├── package.json
    └── src/
        ├── App.jsx
        ├── index.css
        └── components/
            ├── Dashboard.jsx
            ├── ResumeParser.jsx
            ├── AIInterviewer.jsx
            ├── ProfileVerification.jsx
            ├── Login.jsx
            └── Signup.jsx
```

---

## Setup and Installation

### Prerequisites

* Python 3.9+
* Node.js
* PostgreSQL
* Docker and Docker Compose

---

### Environment Variables

Create a `.env` file in the root directory.

```
COHERE_API_KEY=your_cohere_api_key
GEMINI_API_KEY=your_gemini_api_key

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/parser_db

SESSION_SECRET=your_session_secret

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

FRONTEND_URL=http://localhost:5173
```

---

### Start Infrastructure

```
docker-compose up -d
```

This starts PostgreSQL and Redis locally.

---

### Backend Setup

```
python -m venv venv

source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt

cd backend
uvicorn main:app --reload
```

Backend runs at:

```
http://localhost:8000
```

API documentation:

```
http://localhost:8000/docs
```

---

### Frontend Setup

```
cd frontend
npm install
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---

