import os
import re
import json
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_cohere import CohereEmbeddings, ChatCohere
from langchain_core.messages import HumanMessage
import fitz


def _get_env_stripped(key: str) -> str:
    value = os.getenv(key, "")
    if isinstance(value, str):
        return value.strip().strip('"').strip("'")
    return ""

_cohere = ChatCohere(
    model="command-r-plus-08-2024",
    cohere_api_key=_get_env_stripped("COHERE_API_KEY"),
    temperature=0.1,
)

def _ask_cohere(prompt: str) -> str:
    try:
        response = _cohere.invoke([HumanMessage(content=prompt)])
    except Exception as e:
        raise RuntimeError(f"Cohere API request failed: {e}")
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



def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", " ", ""])
    return splitter.split_text(text)


def build_vectorstore(chunks: list[str], embedding_model) -> Chroma:
    from langchain_core.documents import Document
    docs = [Document(page_content=c) for c in chunks]
    return Chroma.from_documents(documents=docs, embedding=embedding_model)


def compute_embedding_score(vectorstore: Chroma, jd_text: str, k: int = 5) -> float:
    results = vectorstore.similarity_search_with_score(jd_text, k=k)
    if not results:
        return 0.0
    total = sum(max(0.0, (1.0 - (score / 2.0)) * 100) for _, score in results)
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
    return {"match_percentage": 0, "missing_skills": [], "strengths": []}

def compute_final_score(embedding_score: float, llm_score: float) -> float:
    return round(0.3 * embedding_score + 0.7 * llm_score, 2)


def parse_resume(file_path: str, job_description: str) -> dict:
    """End-to-end pipeline."""
    resume_text = extract_text_from_file(file_path)
    info = extract_info_with_cohere(resume_text)
    
    # Extract URLs from Cohere
    cohere_urls = info.get("profiles", [])
    
    # Extract hyperlinks directly from PDF if applicable
    file_ext = file_path.lower().split('.')[-1]
    pdf_urls = []
    if file_ext == 'pdf':
        pdf_urls = extract_hyperlinks_from_pdf(file_path)
    
    # Merge and deduplicate URLs
    all_urls = cohere_urls + pdf_urls
    
    # Filter: keep only strings that look like URLs (contain . and http)
    def is_valid_url(url):
        if not isinstance(url, str):
            return False
        url_lower = url.lower()
        return "." in url and ("http://" in url_lower or "https://" in url_lower)
    
    profiles = list(set([url for url in all_urls if is_valid_url(url)]))
    
    # Extract GitHub URL separately
    github_url = None
    for url in profiles:
        if "github.com" in url.lower():
            github_url = url
            break
    
    # Extract LeetCode URL separately
    leetcode_url = None
    for url in profiles:
        if "leetcode.com" in url.lower():
            leetcode_url = url
            break
    
    chunks = chunk_text(resume_text)
    embedding_model = CohereEmbeddings(
        model="embed-english-v3.0",
        cohere_api_key=os.getenv("COHERE_API_KEY")
    )
    vectorstore = build_vectorstore(chunks, embedding_model)
    k = min(5, len(chunks)) if len(chunks) > 0 else 1
    embedding_score = compute_embedding_score(vectorstore, job_description, k=k)
    
    llm_eval = evaluate_with_cohere(resume_text, job_description)
    llm_score = float(llm_eval.get("match_percentage", 0))
    
    final_score = compute_final_score(embedding_score, llm_score)

    # Extract skills
    skills = extract_skills_with_cohere(resume_text)

    result = {
        "name": info.get("name", "Not found"),
        "email": info.get("email"),
        "phone": info.get("phone"),
        "experience": info.get("experience", "Unknown"),
        "profiles": profiles,
        "skills": skills,
        "github_url": github_url,
        "leetcode_url": leetcode_url,
        "match_score": final_score,
        "missing_skills": llm_eval.get("missing_skills", []),
        "strengths": llm_eval.get("strengths", [])
    }

    return result

def extract_skills_with_cohere(resume_text: str) -> list[str]:
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


def normalize_skills_with_cohere(raw_skills: list[str]) -> list[dict]:
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
    # Fallback: return raw skills with default category
    return [{"skill": skill, "normalized": skill, "category": "Other"} for skill in raw_skills]
