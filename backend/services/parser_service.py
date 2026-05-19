import os
import re
import json
import hashlib
import copy
import concurrent.futures
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
        _cohere_client = None  # reset so next call rebuilds a fresh client
        raise RuntimeError(f"Cohere API request failed: {e}")
    text = response.content.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


# ── File text extraction ───────────────────────────────────────────────────────

def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    """Takes raw bytes + filename, writes to /tmp, extracts text, cleans up."""
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
    """Extract hyperlink URIs from PDF using PyMuPDF (fitz)."""
    urls = []
    try:
        pdf_document = fitz.open(file_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            links = page.get_links()
            for link in links:
                if link.get("uri"):
                    uri = link["uri"]
                    if not uri.lower().startswith("mailto:") and (
                        "http://" in uri.lower() or "https://" in uri.lower()
                    ):
                        urls.append(uri)
        pdf_document.close()
    except Exception as e:
        print(f"Error extracting hyperlinks from PDF: {e}")
    return urls


# ── Cohere LLM calls ──────────────────────────────────────────────────────────

def extract_info_with_cohere(resume_text: str) -> dict:
    prompt = f"""
You are an expert resume parser. Extract the following fields from the resume below.
Return ONLY a valid JSON object. NO markdown fences, NO explanation. Just raw JSON.

Fields to extract:
- "name": Full name of the candidate (string)
- "email": Email address (string or null)
- "phone": Phone number (string or null)
- "experience": Total years of experience as a short string like "2 years" or "Fresher" (string)
- "profiles": List of properly formatted URLs ONLY (GitHub, LinkedIn, Portfolio, etc.) found in the resume (list of strings). 
  CRITICAL RULES:
  1. ONLY extract URLs that start with http:// or https://
  2. Do NOT include labels like "Github", "Linkedin", "Portfolio" without a URL
  3. Do NOT guess or construct URLs - only extract what you can see as a complete URL
  4. If a URL is incomplete (like just "github.com/username"), prepend "https://" to make it complete
  5. If only a label with no URL is found, skip it entirely and return empty list

RESUME TEXT:
{resume_text[:3000]}
"""
    raw = _ask_cohere(prompt)
    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"name": "Not found", "email": None, "phone": None, "experience": "Unknown", "profiles": []}


def evaluate_with_cohere(resume_text: str, jd_text: str) -> dict:
    prompt = f"""
You are a senior ATS evaluator. Evaluate how well the candidate's resume matches the job description below.
Score strictly between 0-100 based on core technical skill requirements. 
Penalize the score heavily if core skills from the Job Description are missing. Reward the score for exact matches in their experience.
Respond ONLY with a valid JSON object. No explanation. No markdown.
Format:
{{
"match_percentage": <integer 0-100>,
"missing_skills": ["skill1", "skill2"],
"strengths": ["strength1", "strength2"]
}}

JOB DESCRIPTION:
{jd_text.strip()}

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
    return {"match_percentage": 0, "missing_skills": [], "strengths": []}


def extract_skills_with_cohere(resume_text: str) -> list:
    prompt = f"""
You are a skilled resume parser. Extract all technical and professional skills from the resume below.
Return ONLY a JSON array of strings. NO markdown fences, NO explanation. Just raw JSON.

Rules:
- Extract only actual skills (programming languages, frameworks, tools, technologies, soft skills)
- Do NOT include job titles, company names, education, or personal info
- Be comprehensive but avoid duplicates
- Normalize to standard names (e.g., "JS" -> "JavaScript", "C#" -> "C Sharp")

RESUME TEXT:
{resume_text[:3000]}
"""
    raw = _ask_cohere(prompt)
    try:
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            skills_list = json.loads(json_match.group(0))
            return [skill.strip() for skill in skills_list if isinstance(skill, str)]
    except (json.JSONDecodeError, AttributeError):
        pass
    return []


def normalize_skills_with_cohere(raw_skills: list) -> list:
    if not raw_skills:
        return []
    skills_str = "\n".join(raw_skills)
    prompt = f"""
You are a skills normalization expert. For each skill below, provide a normalized version and category.
Return ONLY a valid JSON array of objects. NO markdown fences, NO explanation. Just raw JSON.

Format:
[
  {{"skill": "original skill", "normalized": "Normalized Skill Name", "category": "Programming Language|Framework|Tool|Technology|Soft Skill"}},
  ...
]

SKILLS:
{skills_str}
"""
    raw = _ask_cohere(prompt)
    try:
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    return [{"skill": skill, "normalized": skill, "category": "Other"} for skill in raw_skills]


# ── Embedding score (in-memory numpy — NO ChromaDB) ───────────────────────────

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
    """
    Embed resume chunks + JD with Cohere, compute cosine similarity in-memory.
    No ChromaDB — no sqlite3 dependency, no disk writes.
    """
    if not chunks:
        return 0.0

    api_key = _get_env_stripped("COHERE_API_KEY")
    embed_model = CohereEmbeddings(
        model="embed-english-v3.0",
        cohere_api_key=api_key,
    )

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
    score = max(0.0, float(np.mean(top_k))) * 100
    return round(score, 2)


def compute_final_score(embedding_score: float, llm_score: float) -> float:
    return round(0.3 * embedding_score + 0.7 * llm_score, 2)


# ── Cache ──────────────────────────────────────────────────────────────────────

_parse_cache: dict = {}
_parse_cache_keys: list = []


# ── Main pipeline ──────────────────────────────────────────────────────────────

def parse_resume(file_path: str, job_description: str) -> dict:
    """
    End-to-end pipeline:
    1. Extract text from file
    2. Run 3 Cohere LLM calls + embedding IN PARALLEL
    3. Return merged result

    Last 5 results cached in-memory.
    """
    # ── Cache check ────────────────────────────────────────────────────────────
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    jd_hash   = hashlib.sha256(job_description.encode("utf-8")).hexdigest()
    cache_key = f"{file_hash}_{jd_hash}"

    if cache_key in _parse_cache:
        print("Cache hit for parse_resume!")
        return copy.deepcopy(_parse_cache[cache_key])

    # ── Text extraction ────────────────────────────────────────────────────────
    resume_text = extract_text_from_file(file_path)

    # ── Hyperlinks from PDF ────────────────────────────────────────────────────
    file_ext = file_path.lower().split('.')[-1]
    pdf_urls = []
    if file_ext == 'pdf':
        pdf_urls = extract_hyperlinks_from_pdf(file_path)

    # ── Chunk text for embedding ───────────────────────────────────────────────
    chunks = chunk_text(resume_text)
    k = min(5, len(chunks)) if chunks else 1

    # ── Run all heavy calls in parallel ───────────────────────────────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        f_info   = pool.submit(extract_info_with_cohere, resume_text)
        f_eval   = pool.submit(evaluate_with_cohere, resume_text, job_description)
        f_skills = pool.submit(extract_skills_with_cohere, resume_text)
        f_embed  = pool.submit(compute_embedding_score_numpy, chunks, job_description, k)

        info            = f_info.result()
        llm_eval        = f_eval.result()
        skills          = f_skills.result()
        embedding_score = f_embed.result()

    # ── Merge URLs ─────────────────────────────────────────────────────────────
    cohere_urls = info.get("profiles", [])
    all_urls    = cohere_urls + pdf_urls

    def is_valid_url(url):
        if not isinstance(url, str):
            return False
        url_lower = url.lower()
        return "." in url and ("http://" in url_lower or "https://" in url_lower)

    profiles     = list(set(url for url in all_urls if is_valid_url(url)))
    github_url   = next((u for u in profiles if "github.com"   in u.lower()), None)
    leetcode_url = next((u for u in profiles if "leetcode.com" in u.lower()), None)

    # ── Scores ─────────────────────────────────────────────────────────────────
    llm_score   = float(llm_eval.get("match_percentage", 0))
    final_score = compute_final_score(embedding_score, llm_score)

    # ── Build result ───────────────────────────────────────────────────────────
    result = {
        "name":           info.get("name", "Not found"),
        "email":          info.get("email"),
        "phone":          info.get("phone"),
        "experience":     info.get("experience", "Unknown"),
        "profiles":       profiles,
        "skills":         skills,
        "github_url":     github_url,
        "leetcode_url":   leetcode_url,
        "match_score":    final_score,
        "missing_skills": llm_eval.get("missing_skills", []),
        "strengths":      llm_eval.get("strengths", []),
    }

    # ── Cache (keep last 5) ────────────────────────────────────────────────────
    _parse_cache[cache_key] = copy.deepcopy(result)
    _parse_cache_keys.append(cache_key)
    if len(_parse_cache_keys) > 5:
        oldest = _parse_cache_keys.pop(0)
        _parse_cache.pop(oldest, None)

    return result