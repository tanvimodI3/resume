import os
import re
import json
import concurrent.futures
from dotenv import load_dotenv

from backend.services.cache_service import generate_hash, get_cache, set_cache

load_dotenv()

from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_cohere import CohereEmbeddings, ChatCohere
from langchain_core.messages import HumanMessage
import fitz


_cohere = ChatCohere(
    model="command-r-plus-08-2024",
    cohere_api_key=os.getenv("COHERE_API_KEY"),
    temperature=0.1,
)

_cohere_fast = ChatCohere(
    model="command-r-08-2024",
    cohere_api_key=os.getenv("COHERE_API_KEY"),
    temperature=0.1,
)


def _ask_cohere(prompt: str) -> str:
    response = _cohere.invoke([HumanMessage(content=prompt)])
    text = response.content.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def _ask_cohere_fast(prompt: str) -> str:
    response = _cohere_fast.invoke([HumanMessage(content=prompt)])
    text = response.content.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text

def _ask_cohere_fast(prompt: str) -> str:
    response = _cohere_fast.invoke([HumanMessage(content=prompt)])
    text = response.content.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


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

def extract_text_from_upload(file_content: bytes, filename: str) -> str:
    import tempfile
    ext = filename.lower().split('.')[-1]
    
    if ext not in ['pdf', 'docx', 'txt']:
        raise ValueError(f"Unsupported file extension: {ext}")
    
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    
    try:
        text = extract_text_from_file(tmp_path)
        return text
    finally:
        os.unlink(tmp_path)

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
                    # Skip mailto links, only keep http/https URIs
                    if not uri.lower().startswith("mailto:") and ("http://" in uri.lower() or "https://" in uri.lower()):
                        urls.append(uri)
        pdf_document.close()
    except Exception as e:
        print(f"Error extracting hyperlinks from PDF: {e}")
    return urls

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
- "skills": Extract max 15 HARD CORE technical skills and frameworks (e.g. Git, Docker, React) found implicitly in the entire text (list of strings). NO soft skills.

RESUME TEXT:
{resume_text[:3000]}
"""

    raw = _ask_cohere_fast(prompt)

    try:

        json_match = re.search(r"\{.*\}", raw, re.DOTALL)

        if json_match:
            return json.loads(json_match.group(0))

    except (json.JSONDecodeError, AttributeError):
        pass

    return {
        "name": "Not found",
        "email": None,
        "phone": None,
        "experience": "Unknown",
        "profiles": [],
        "skills": []
    }

def extract_skills_with_cohere(resume_text: str) -> list[str]:
    prompt = f"""
You are an expert technical recruiter. Extract ALL skills mentioned in this resume.

Include: programming languages, frameworks, libraries, databases, tools, cloud platforms,
DevOps tools, soft skills, methodologies (Agile, Scrum), and any other relevant skills.

Return ONLY a JSON array of skill strings. No explanation. No markdown. No code fences. Just raw JSON array.

Example: ["Python", "React", "MongoDB", "Docker", "Leadership"]

RESUME TEXT:
{resume_text[:4000]}
"""
    raw = _ask_cohere(prompt)
    try:
        arr_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if arr_match:
            return json.loads(arr_match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    return []

def normalize_skills_with_cohere(skills: list[str]) -> list[dict]:
    if not skills:
        return []

    prompt = f"""
You are a skill taxonomy expert. Normalize the following skill list and categorize each skill.

Rules:
- Fix abbreviations and synonyms (e.g. "JS" -> "JavaScript", "K8s" -> "Kubernetes", "Mongo" -> "MongoDB")
- Assign each skill to exactly one of these categories:
  "Languages", "Frontend", "Backend", "Databases", "DevOps & Cloud", "AI & ML",
  "Testing", "Tools & Version Control", "Soft Skills", "Other"

Return ONLY a JSON array. No explanation. No markdown. No code fences. Just raw JSON.

Format:
[{{"skill": "JavaScript", "category": "Languages"}}, ...]

Raw skills: {json.dumps(skills)}
"""
    raw = _ask_cohere(prompt)
    try:
        arr_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if arr_match:
            return json.loads(arr_match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass

    return [{"skill": s, "category": "Other"} for s in skills]


def chunk_text(text: str) -> list[str]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )

    return splitter.split_text(text)


def build_vectorstore(chunks: list[str], embedding_model) -> Chroma:

    from langchain_core.documents import Document

    docs = [Document(page_content=c) for c in chunks]

    return Chroma.from_documents(
        documents=docs,
        embedding=embedding_model
    )


def compute_embedding_score(vectorstore: Chroma, jd_text: str, k: int = 5) -> float:

    results = vectorstore.similarity_search_with_score(jd_text, k=k)

    if not results:
        return 0.0

    total = sum(
        max(0.0, (1.0 - (score / 2.0)) * 100)
        for _, score in results
    )

    return round(total / len(results), 2)


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

    return {
        "match_percentage": 0,
        "missing_skills": [],
        "strengths": []
    }


def compute_final_score(embedding_score: float, llm_score: float) -> float:
    return round(0.3 * embedding_score + 0.7 * llm_score, 2)


def _get_embedding_score_task(resume_text: str, jd_text: str) -> float:

    chunks = chunk_text(resume_text)

    embedding_model = CohereEmbeddings(
        model="embed-english-v3.0",
        cohere_api_key=os.getenv("COHERE_API_KEY")
    )

    vectorstore = build_vectorstore(chunks, embedding_model)

    k = min(5, len(chunks)) if len(chunks) > 0 else 1

    return compute_embedding_score(vectorstore, jd_text, k=k)


def parse_resume(file_path: str, job_description: str) -> dict:
    """
    End-to-end pipeline with Redis caching
    """

    resume_text = extract_text_from_file(file_path)

    key = generate_hash((resume_text + job_description).encode())

    cached = get_cache(key)

    if cached:
        return cached

    with concurrent.futures.ThreadPoolExecutor() as executor:

        future_info = executor.submit(extract_info_with_cohere, resume_text)

        future_eval = executor.submit(evaluate_with_cohere, resume_text, job_description)

        info = future_info.result()

        llm_eval = future_eval.result()

    # Embedding must run outside the thread pool - CohereEmbeddings is not thread-safe
    embedding_score = _get_embedding_score_task(resume_text, job_description)

    # --- URL Extraction ---
    cohere_urls = info.get("profiles", [])
    
    file_ext = file_path.lower().split('.')[-1]
    pdf_urls = []
    if file_ext == 'pdf':
        pdf_urls = extract_hyperlinks_from_pdf(file_path)
    
    all_urls = cohere_urls + pdf_urls
    
    def is_valid_url(url):
        if not isinstance(url, str):
            return False
        url_lower = url.lower()
        return "." in url and ("http://" in url_lower or "https://" in url_lower)
    
    profiles = list(set([url for url in all_urls if is_valid_url(url)]))
    # ----------------------

    llm_score = float(llm_eval.get("match_percentage", 0))

    final_score = compute_final_score(embedding_score, llm_score)

    result = {
        "name": info.get("name", "Not found"),
        "email": info.get("email"),
        "phone": info.get("phone"),
        "experience": info.get("experience", "Unknown"),
        "profiles": profiles,
        "skills": info.get("skills", []),
        "match_score": final_score,
        "missing_skills": llm_eval.get("missing_skills", []),
        "strengths": llm_eval.get("strengths", [])
    }

    set_cache(key, result)

    return result