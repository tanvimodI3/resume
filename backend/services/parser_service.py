import os
import re
import json
import hashlib
import copy
import numpy as np
from dotenv import load_dotenv

load_dotenv()

from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_cohere import CohereEmbeddings, ChatCohere
from langchain_core.messages import HumanMessage
import fitz


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_env_stripped(key: str) -> str:
    value = os.getenv(key, "")
    if isinstance(value, str):
        return value.strip().strip('"').strip("'")
    return ""


# ── Cohere client (lazy singleton, reset on failure) ──────────────────────────

_cohere_client = None

def _get_cohere_client():
    global _cohere_client
    if _cohere_client is None:
        _cohere_client = ChatCohere(
            model="command-r-plus-08-2024",
            cohere_api_key=_get_env_stripped("COHERE_API_KEY"),
            temperature=0.1,
        )
    return _cohere_client


def _ask_cohere(prompt: str) -> str:
    global _cohere_client
    try:
        response = _get_cohere_client().invoke([HumanMessage(content=prompt)])
    except Exception as e:
        _cohere_client = None
        raise RuntimeError(f"Cohere API request failed: {e}")
    text = response.content.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


# ── File text extraction ───────────────────────────────────────────────────────

def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    import uuid
    ext = (filename or "upload").lower().split('.')[-1]
    tmp_path = f"/tmp/{uuid.uuid4()}.{ext}"
    try:
        with open(tmp_path, "wb") as f:
            f.write(file_bytes)
        return extract_text_from_file(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def extract_text_from_file(file_path: str) -> str:
    ext = file_path.lower().split('.')[-1]
    if ext == 'pdf':
        loader = PyMuPDFLoader(file_path)
    elif ext == 'docx':
        loader = Docx2txtLoader(file_path)
    elif ext == 'txt':
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
    docs = loader.load()
    return "\n".join(doc.page_content for doc in docs)


def extract_hyperlinks_from_pdf(file_path: str) -> list:
    urls = []
    try:
        pdf_document = fitz.open(file_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            for link in page.get_links():
                if link.get("uri"):
                    uri = link["uri"]
                    if not uri.lower().startswith("mailto:") and (
                        "http://" in uri.lower() or "https://" in uri.lower()
                    ):
                        urls.append(uri)
        pdf_document.close()
    except Exception as e:
        print(f"Error extracting hyperlinks: {e}")
    return urls


# ── SINGLE MEGA-PROMPT: replaces 3 separate Cohere calls ──────────────────────
# Old approach: 3 calls × ~6s each = ~18s (even in parallel, bounded by slowest)
# New approach: 1 call × ~6s = ~6s flat. Cuts LLM time by 65%.

def _parse_resume_with_one_call(resume_text: str, jd_text: str) -> dict:
    """
    One single Cohere call that does everything:
    - Extracts candidate info (name, email, phone, experience, profiles)
    - Extracts and normalizes skills
    - Evaluates match against job description (score, missing skills, strengths)

    Returns a dict with all fields merged.
    """
    prompt = f"""
You are an expert resume parser and ATS evaluator. Analyze the resume and job description below.
Return ONLY a single valid JSON object. NO markdown fences, NO explanation. Just raw JSON.

The JSON must have exactly these top-level keys:

{{
  "name": "Full name of candidate (string)",
  "email": "email or null",
  "phone": "phone number or null",
  "experience": "e.g. '2 years' or 'Fresher' (string)",
  "profiles": ["https://...", "https://..."],
  "skills": ["Python", "React", "Docker"],
  "match_percentage": <integer 0-100>,
  "missing_skills": ["skill1", "skill2"],
  "strengths": ["strength1", "strength2"]
}}

Rules for profiles:
- ONLY include URLs starting with http:// or https://
- If incomplete like "github.com/user", prepend "https://"
- If no URL found for a platform, omit it entirely

Rules for skills:
- Include all technical and professional skills
- Normalize names: "JS" -> "JavaScript", "C#" -> "C Sharp"
- No job titles, company names, or education

Rules for match_percentage:
- Score 0-100 based on how well resume matches the job description
- Penalize heavily for missing core skills
- Reward for direct experience matches

JOB DESCRIPTION:
{jd_text.strip()[:2000]}

RESUME:
{resume_text[:3000]}
"""
    raw = _ask_cohere(prompt)
    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    # Safe fallback — never crash the endpoint
    return {
        "name": "Not found", "email": None, "phone": None,
        "experience": "Unknown", "profiles": [], "skills": [],
        "match_percentage": 0, "missing_skills": [], "strengths": []
    }


# ── Embedding score (numpy, no ChromaDB) ──────────────────────────────────────

def chunk_text(text: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def compute_embedding_score_numpy(chunks: list, jd_text: str, k: int = 5) -> float:
    if not chunks:
        return 0.0
    api_key = _get_env_stripped("COHERE_API_KEY")
    embed_model = CohereEmbeddings(model="embed-english-v3.0", cohere_api_key=api_key)
    try:
        chunk_vecs = embed_model.embed_documents(chunks)
        jd_vec     = embed_model.embed_query(jd_text)
    except Exception as e:
        print(f"Embedding error (returning 0): {e}")
        return 0.0
    chunk_arr = np.array(chunk_vecs, dtype=np.float32)
    jd_arr    = np.array(jd_vec,    dtype=np.float32)
    sims  = [_cosine_similarity(chunk_arr[i], jd_arr) for i in range(len(chunk_arr))]
    top_k = sorted(sims, reverse=True)[:k]
    return round(max(0.0, float(np.mean(top_k))) * 100, 2)


def compute_final_score(embedding_score: float, llm_score: float) -> float:
    return round(0.3 * embedding_score + 0.7 * llm_score, 2)


# ── Keep these for backward compat (used by main.py helper endpoints) ─────────

def extract_info_with_cohere(resume_text: str) -> dict:
    prompt = f"""
Extract candidate info from this resume. Return ONLY valid JSON, no markdown.
{{
  "name": "full name",
  "email": "email or null",
  "phone": "phone or null",
  "experience": "e.g. 2 years",
  "profiles": ["https://..."]
}}
RESUME: {resume_text[:3000]}
"""
    raw = _ask_cohere(prompt)
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return {"name": "Not found", "email": None, "phone": None, "experience": "Unknown", "profiles": []}


def extract_skills_with_cohere(resume_text: str) -> list:
    prompt = f"""
Extract all skills from this resume. Return ONLY a JSON array of strings, no markdown.
RESUME: {resume_text[:3000]}
"""
    raw = _ask_cohere(prompt)
    try:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            return [s.strip() for s in json.loads(m.group(0)) if isinstance(s, str)]
    except Exception:
        pass
    return []


def evaluate_with_cohere(resume_text: str, jd_text: str) -> dict:
    prompt = f"""
Evaluate resume vs job description. Return ONLY valid JSON, no markdown.
{{"match_percentage": <0-100>, "missing_skills": [], "strengths": []}}
JD: {jd_text[:1500]}
RESUME: {resume_text[:2000]}
"""
    raw = _ask_cohere(prompt)
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return {"match_percentage": 0, "missing_skills": [], "strengths": []}


def normalize_skills_with_cohere(raw_skills: list) -> list:
    if not raw_skills:
        return []
    prompt = f"""
Normalize these skills. Return ONLY a JSON array, no markdown.
[{{"skill": "x", "normalized": "X", "category": "Tool"}}]
SKILLS: {chr(10).join(raw_skills)}
"""
    raw = _ask_cohere(prompt)
    try:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return [{"skill": s, "normalized": s, "category": "Other"} for s in raw_skills]


# ── Cache ──────────────────────────────────────────────────────────────────────

_parse_cache: dict = {}
_parse_cache_keys: list = []


# ── Main pipeline ──────────────────────────────────────────────────────────────

def parse_resume(file_path: str, job_description: str) -> dict:
    """
    Optimized pipeline:
    - 1 Cohere LLM call (was 3) → ~6s
    - 1 Cohere embed call       → ~2s (runs in parallel with LLM)
    - Total wall time: ~6-8s (safe on Render free tier even with cold start)
    """
    import concurrent.futures

    # ── Cache check ───────────────────────────────────────────────────────────
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    jd_hash   = hashlib.sha256(job_description.encode("utf-8")).hexdigest()
    cache_key = f"{file_hash}_{jd_hash}"

    if cache_key in _parse_cache:
        print("Cache hit for parse_resume!")
        return copy.deepcopy(_parse_cache[cache_key])

    # ── Text extraction ───────────────────────────────────────────────────────
    resume_text = extract_text_from_file(file_path)

    # ── PDF hyperlinks ────────────────────────────────────────────────────────
    pdf_urls = []
    if file_path.lower().endswith('.pdf'):
        pdf_urls = extract_hyperlinks_from_pdf(file_path)

    # ── Chunk for embedding ───────────────────────────────────────────────────
    chunks = chunk_text(resume_text)
    k = min(5, len(chunks)) if chunks else 1

    # ── Run mega-LLM call + embedding in parallel (2 threads, not 4) ─────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_llm   = pool.submit(_parse_resume_with_one_call, resume_text, job_description)
        f_embed = pool.submit(compute_embedding_score_numpy, chunks, job_description, k)

        parsed          = f_llm.result()
        embedding_score = f_embed.result()

    # ── Merge URLs ────────────────────────────────────────────────────────────
    cohere_urls = parsed.get("profiles", [])
    all_urls    = cohere_urls + pdf_urls

    def is_valid_url(url):
        if not isinstance(url, str):
            return False
        url_lower = url.lower()
        return "." in url and ("http://" in url_lower or "https://" in url_lower)

    profiles     = list(set(u for u in all_urls if is_valid_url(u)))
    github_url   = next((u for u in profiles if "github.com"   in u.lower()), None)
    leetcode_url = next((u for u in profiles if "leetcode.com" in u.lower()), None)

    # ── Final score ───────────────────────────────────────────────────────────
    llm_score   = float(parsed.get("match_percentage", 0))
    final_score = compute_final_score(embedding_score, llm_score)

    result = {
        "name":           parsed.get("name", "Not found"),
        "email":          parsed.get("email"),
        "phone":          parsed.get("phone"),
        "experience":     parsed.get("experience", "Unknown"),
        "profiles":       profiles,
        "skills":         parsed.get("skills", []),
        "github_url":     github_url,
        "leetcode_url":   leetcode_url,
        "match_score":    final_score,
        "missing_skills": parsed.get("missing_skills", []),
        "strengths":      parsed.get("strengths", []),
    }

    # ── Cache (last 5) ────────────────────────────────────────────────────────
    _parse_cache[cache_key] = copy.deepcopy(result)
    _parse_cache_keys.append(cache_key)
    if len(_parse_cache_keys) > 5:
        _parse_cache.pop(_parse_cache_keys.pop(0), None)

    return result