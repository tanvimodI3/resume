# AI-Powered Resume ATS (Applicant Tracking System)

## 📌 Overview
The AI-Powered Resume ATS is a full-stack, intelligent web application built to help technical recruiters, HR professionals, and administrators streamline their hiring process. By leveraging large language models (LLMs) and vector databases, the application compares candidate resumes against given job descriptions (JDs) and automatically generates match scores, identifies missing skills, and extracts essential candidate information.

## 🚀 Key Features
- **Intelligent Resume Parsing:** Automatically extracts candidate details such as Name, Email, Phone, Experience, and Profiles (LinkedIn, GitHub) from uploaded resumes (supports PDF, DOCX, and TXT).
- **AI-Powered Evaluation:** Uses LangChain and Cohere's advanced LLMs to identify specific candidate strengths and pinpoint missing skills relative to the job description.
- **Semantic Matching (Vector Search):** Chunks resume content and uses ChromaDB with Cohere Embeddings to calculate a contextual match score based on how well the candidate aligns with the JD.
- **Secure Authentication:** JWT-based secure signup and login flows for admins/recruiters, ensuring resume evaluation histories remain private.
- **History Tracking:** All previously scanned resumes are saved to the PostgreSQL database, allowing recruiters to review past candidate matches effortlessly.

## 🛠️ Tech Stack 
**Backend**
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL & SQLAlchemy (ORM)
- **AI & NLP:** LangChain, Cohere (Command R+ LLM and v3.0 Embeddings) 
- **Vector Storage:** Chroma
- **Authentication:** OAuth2 with JWT (Passlib & python-jose)

**Frontend**
- **Framework:** React + Vite
- **Styling:** Custom CSS (Glassmorphism UI)
- **Routing:** React Router DOM

---

## 📂 Project Structure

```text
parser/
├── .env                 # Environment variables (API Keys, DB Credentials)
├── docker-compose.yml   # Docker configuration for local Postgres
├── requirements.txt     # Python backend dependencies
├── backend/             # FASTAPI APPLICATION
│   ├── main.py          # Entry point containing API routes (auth, parse, history)
│   ├── db.py            # Database connection and session management
│   ├── queries/         
│   │   └── tables.sql   # SQL tables schema outline
│   └── services/        
│       ├── auth.py          # JWT, hashing, and security logic
│       ├── models.py        # SQLAlchemy database models (User, CandidateDetails)
│       ├── schemas.py       # Pydantic data validation schemas
│       └── parser_service.py # LangChain & Cohere AI core logic
└── frontend/            # REACT VITE APPLICATION
    ├── src/
    │   ├── components/  # React components (Signup, Login, Dashboard)
    │   ├── App.jsx      # Main application router
    │   └── index.css    # Core visual styling
    └── package.json     # Node.js dependencies
```

---

## ⚙️ Setup and Installation

### 1. Prerequisites
- Python 3.9+
- Node.js (for the frontend environment)
- PostgreSQL (or use the provided `docker-compose.yml` to spin it up)

### 2. Environment Variables
Create an `.env` file in the root directory (`/parser`) and populate it with your credentials:
```env
COHERE_API_KEY="your-cohere-api-key"
DATABASE_URL="postgresql://username:password@localhost:5432/resume_db"
```

### 3. Start the Database
If you do not have a Postgres database running locally, you can use Docker:
```bash
docker-compose up -d
```

### 4. Backend Setup
Open a terminal in the root directory:
```powershell
# Create a virtual environment
python -m venv venv

# Activate the virtual environment (Windows)
.\venv\Scripts\activate
# (Mac/Linux: source venv/bin/activate)

# Install requirements
pip install -r requirements.txt

# Run the FastAPI server
cd backend
uvicorn main:app --reload
```
*The backend API will be running at: `http://127.0.0.1:8000`*

### 5. Frontend Setup
Open a second terminal window:
```powershell
# Navigate to the frontend
cd frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
```
*The React UI will be accessible at: `http://localhost:5173`*

---

## 📖 How it Works
1. **Admin Access:** You sign up securely on the platform. Your details are hashed and stored in Postgres. You log in to obtain a JWT token.
2. **Upload:** From the dashboard, attach a resume file and paste the target Job Description.
3. **Parse & Embed:** The backend slices the resume into chunks, creates mathematical embeddings out of them, and stores them temporarily in Chroma.
4. **Compare:** It uses Similarity Search against the JD embeddings. Meanwhile, Cohere's LLM reads the text directly to synthesize an overarching evaluation (Strengths & Missing Skills).
5. **View:** A concise match score and evaluation report is returned directly to your UI dashboard and archived forever in your search history.
