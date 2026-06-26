import os
import re
import json
import chromadb
from groq import Groq

# --- Optional extractors: use best available library per format ---
try:
    import docx2txt
    HAS_DOCX2TXT = True
except ImportError:
    HAS_DOCX2TXT = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False

try:
    from llama_index.core import SimpleDirectoryReader
    HAS_LLAMA = True
except ImportError:
    HAS_LLAMA = False

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="candidates")

# ── Text Extraction ───────────────────────────────────────────────────────────

def _extract_pdf(file_path: str) -> str:
    """Extract all text from a PDF using pypdf, page by page."""
    if not HAS_PYPDF:
        return ""
    try:
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except Exception as e:
        print(f"[resume_parser] pypdf error: {e}")
        return ""

def _extract_docx(file_path: str) -> str:
    """Extract all text from a DOCX using docx2txt."""
    if not HAS_DOCX2TXT:
        return ""
    try:
        return docx2txt.process(file_path) or ""
    except Exception as e:
        print(f"[resume_parser] docx2txt error: {e}")
        return ""

def _extract_llama(file_path: str) -> str:
    """Fallback extraction via llama-index SimpleDirectoryReader."""
    if not HAS_LLAMA:
        return ""
    try:
        docs = SimpleDirectoryReader(input_files=[file_path]).load_data()
        return "\n".join(doc.text for doc in docs)
    except Exception as e:
        print(f"[resume_parser] llama-index error: {e}")
        return ""

def _clean_text(raw: str) -> str:
    """Normalize whitespace, remove garbage characters, collapse blank lines."""
    # Remove non-printable chars except newline/tab
    raw = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]', ' ', raw)
    # Collapse multiple spaces
    raw = re.sub(r'[ \t]{2,}', ' ', raw)
    # Collapse 3+ blank lines to 2
    raw = re.sub(r'\n{3,}', '\n\n', raw)
    return raw.strip()

def extract_text(file_path: str) -> str:
    """
    Multi-strategy text extractor.
    Tries format-specific extractors first (highest quality),
    then falls back to llama-index.
    Returns the best (longest) non-empty result.
    """
    ext = os.path.splitext(file_path)[1].lower()
    candidates = []

    if ext == ".pdf":
        pdf_text = _clean_text(_extract_pdf(file_path))
        if pdf_text:
            candidates.append(pdf_text)

    elif ext in (".docx", ".doc"):
        docx_text = _clean_text(_extract_docx(file_path))
        if docx_text:
            candidates.append(docx_text)

    # Always try llama-index as an additional pass
    llama_text = _clean_text(_extract_llama(file_path))
    if llama_text:
        candidates.append(llama_text)

    if not candidates:
        return "No readable text could be extracted from the document."

    # Return the longest extracted text (most complete)
    return max(candidates, key=len)


# ── Profile Extraction via LLM ────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert resume parser. Given the raw text of a resume, extract all available structured information into a precise JSON object.

EXTRACTION RULES:
- Be thorough. Do not skip sections.
- If a field is not found, use an empty string "" or empty list [] — never omit the key.
- For skills, include ALL technical skills, tools, frameworks, languages, and platforms mentioned anywhere in the resume.
- For projects, capture each distinct project with its name, description, and tech stack used.
- For work_experience, capture each role with company, title, duration, and key responsibilities (as a short list).
- For education, capture institution, degree, field, and year.
- Infer target_role from the most senior/recent job title, or from an explicit objective/summary if present.
- years_of_experience: calculate or estimate total years from work history dates. If unclear, estimate from context.

Return ONLY a valid JSON object with this exact schema (no extra fields, no markdown):
{
  "name": "Full name of the candidate",
  "email": "email address or empty string",
  "phone": "phone number or empty string",
  "target_role": "Most relevant job title or desired role",
  "years_of_experience": "e.g. 3 or '2-3' or 'fresher'",
  "location": "city/country or empty string",
  "summary": "Professional summary or objective in 2-4 sentences",
  "skills": ["skill1", "skill2", "skill3"],
  "tools_and_technologies": ["tool1", "tool2"],
  "work_experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "duration": "Jan 2022 - Present",
      "responsibilities": ["responsibility 1", "responsibility 2"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "Brief description of the project and your role",
      "tech_stack": ["React", "Python"]
    }
  ],
  "education": [
    {
      "institution": "University Name",
      "degree": "B.Tech / B.Sc / MBA etc.",
      "field": "Computer Science",
      "year": "2022"
    }
  ],
  "certifications": ["cert1", "cert2"],
  "languages": ["English", "Tamil"],
  "achievements": ["award or achievement 1"]
}"""

def _call_llm_extract(text: str) -> dict:
    """
    Send resume text to the LLM for structured extraction.
    Uses a 2-pass strategy: first pass on full text (up to 12k chars),
    second pass on the remainder if the resume is very long.
    """
    # LLM context budget: llama-3.3-70b supports ~32k tokens — 12k chars is safe
    MAX_CHARS = 12000

    chunk1 = text[:MAX_CHARS]
    profile = {}

    try:
        resp1 = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Parse this resume:\n\n{chunk1}"}
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=2048
        )
        profile = json.loads(resp1.choices[0].message.content)
    except Exception as e:
        print(f"[resume_parser] LLM pass 1 error: {e}")
        profile = _empty_profile()

    # If resume was very long, do a second pass on the remaining text to capture
    # any skills/projects/experience that might have been cut off
    if len(text) > MAX_CHARS:
        remainder = text[MAX_CHARS:MAX_CHARS * 2]
        try:
            supplement_prompt = (
                "The following is the CONTINUATION of the same resume. "
                "Extract any ADDITIONAL skills, tools, projects, work experience, "
                "certifications, or education entries NOT already captured. "
                "Return ONLY a JSON with the fields that have new items to merge:\n\n"
                f"{remainder}"
            )
            resp2 = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": supplement_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=1024
            )
            extra = json.loads(resp2.choices[0].message.content)
            profile = _merge_profiles(profile, extra)
        except Exception as e:
            print(f"[resume_parser] LLM pass 2 error: {e}")

    return profile


def _empty_profile() -> dict:
    return {
        "name": "Candidate",
        "email": "",
        "phone": "",
        "target_role": "Software Engineer",
        "years_of_experience": "",
        "location": "",
        "summary": "",
        "skills": [],
        "tools_and_technologies": [],
        "work_experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "languages": [],
        "achievements": []
    }


def _merge_profiles(base: dict, extra: dict) -> dict:
    """Merge list fields from extra into base (de-duplicated)."""
    list_fields = [
        "skills", "tools_and_technologies", "work_experience",
        "projects", "education", "certifications", "languages", "achievements"
    ]
    for field in list_fields:
        if field in extra and isinstance(extra[field], list):
            existing = base.get(field, [])
            # For simple string lists, do a set-merge
            if all(isinstance(x, str) for x in extra[field]):
                existing_lower = {s.lower() for s in existing if isinstance(s, str)}
                for item in extra[field]:
                    if isinstance(item, str) and item.lower() not in existing_lower:
                        existing.append(item)
                        existing_lower.add(item.lower())
            else:
                # For dicts (work_experience, projects, education) just append
                existing.extend(extra[field])
            base[field] = existing

    # Merge scalar fields only if base is empty/unknown
    for field in ["name", "email", "phone", "target_role", "summary", "location"]:
        if not base.get(field) and extra.get(field):
            base[field] = extra[field]

    return base


# ── ChromaDB Storage ──────────────────────────────────────────────────────────

def _store_in_chroma(session_id: str, text: str, profile: dict):
    """Chunk raw text + profile into ChromaDB for later retrieval."""
    # Store text chunks
    chunks = [text[i:i+1000] for i in range(0, min(len(text), 10000), 1000)]
    for i, chunk in enumerate(chunks):
        try:
            collection.upsert(
                documents=[chunk],
                metadatas=[{"session_id": session_id, "type": "resume_chunk", "chunk_index": i}],
                ids=[f"{session_id}_chunk_{i}"]
            )
        except Exception:
            pass

    # Store profile
    try:
        collection.upsert(
            documents=[json.dumps(profile)],
            metadatas=[{"session_id": session_id, "type": "profile"}],
            ids=[f"{session_id}_profile"]
        )
    except Exception as e:
        print(f"[resume_parser] ChromaDB upsert error: {e}")


# ── Public API ────────────────────────────────────────────────────────────────

def parse_resume(file_path: str, session_id: str = "default") -> dict:
    """
    Full resume parsing pipeline:
    1. Extract raw text (PDF / DOCX / fallback)
    2. Clean and normalize text
    3. LLM-based structured extraction (2-pass for long resumes)
    4. Store in ChromaDB for retrieval
    5. Return structured profile dict
    """
    print(f"[resume_parser] Parsing resume: {file_path}")

    # Step 1 & 2: Extract + clean
    raw_text = extract_text(file_path)
    print(f"[resume_parser] Extracted {len(raw_text)} characters")

    if len(raw_text) < 100:
        print("[resume_parser] Warning: Very little text extracted. Using fallback profile.")
        profile = _empty_profile()
    else:
        # Step 3: LLM extraction
        profile = _call_llm_extract(raw_text)

        # Ensure all required keys exist (guard against partial LLM output)
        defaults = _empty_profile()
        for key, default_val in defaults.items():
            if key not in profile:
                profile[key] = default_val

        # Flatten combined skills list for agents.py compatibility
        all_skills = list(profile.get("skills", []))
        for tool in profile.get("tools_and_technologies", []):
            if tool not in all_skills:
                all_skills.append(tool)
        profile["skills"] = all_skills

        # Build a rich experience_summary for the interview agent
        profile["experience_summary"] = _build_experience_summary(profile)

    # Step 4: Store in ChromaDB
    _store_in_chroma(session_id, raw_text, profile)

    print(f"[resume_parser] Profile extracted: name={profile.get('name')}, "
          f"role={profile.get('target_role')}, skills={len(profile.get('skills', []))}")
    return profile


def _build_experience_summary(profile: dict) -> str:
    """Build a concise experience narrative from structured profile for the interview agent."""
    parts = []

    yoe = profile.get("years_of_experience")
    if yoe:
        parts.append(f"{yoe} years of experience")

    roles = profile.get("work_experience", [])
    if roles:
        role_strs = []
        for r in roles[:3]:  # top 3 roles
            title = r.get("title", "")
            company = r.get("company", "")
            duration = r.get("duration", "")
            if title and company:
                role_strs.append(f"{title} at {company} ({duration})")
        if role_strs:
            parts.append("Work history: " + "; ".join(role_strs))

    edu = profile.get("education", [])
    if edu:
        e = edu[0]
        deg = e.get("degree", "")
        field = e.get("field", "")
        inst = e.get("institution", "")
        if deg or inst:
            parts.append(f"Education: {deg} {field} from {inst}".strip())

    certs = profile.get("certifications", [])
    if certs:
        parts.append("Certifications: " + ", ".join(certs[:4]))

    return ". ".join(parts) if parts else "No detailed experience information extracted."


def get_profile(session_id: str = "default") -> dict:
    """Retrieve the stored profile for a session from ChromaDB."""
    try:
        results = collection.get(ids=[f"{session_id}_profile"])
        if results and results.get("documents"):
            return json.loads(results["documents"][0])
    except Exception as e:
        print(f"[resume_parser] get_profile error: {e}")
    return _empty_profile()
