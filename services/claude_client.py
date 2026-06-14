import httpx
from config import get_settings


def _chat(prompt: str, max_tokens: int = 4096) -> str:
    s = get_settings()
    resp = httpx.post(
        f"{s.ollama_host}/api/chat",
        json={
            "model": s.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def tailor_cv(base_cv: str, job_title: str, company: str, job_description: str) -> str:
    prompt = f"""You are an expert CV writer. Adapt the following CV for the job below.

RULES:
- Keep everything factually true — do not invent experience or skills
- Reorder bullet points to lead with the most relevant achievements
- Mirror key terms from the JD naturally (avoid keyword stuffing)
- Keep the same overall structure; adjust wording and emphasis only
- Return ONLY the adapted CV text, formatted in Markdown with these sections:
  # [Full Name]
  Contact info line
  ## Summary
  ## Experience
  ### [Role] | [Company] | [Dates]
  - bullet
  ## Education
  ## Skills

BASE CV:
{base_cv}

JOB:
Title: {job_title}
Company: {company}

Job Description:
{job_description[:4000]}

Return the adapted CV now:"""

    return _chat(prompt, max_tokens=4096)


_LINKEDIN_LIMIT = 300


def draft_linkedin_message(
    contact_name: str,
    job_title: str,
    company: str,
    job_description: str,
    base_cv: str,
) -> str:
    first_name = contact_name.split()[0]

    def _prompt(extra: str = "") -> str:
        return f"""Write a LinkedIn connection request note.

HARD LIMIT: the message MUST be under {_LINKEDIN_LIMIT} characters total — count every character including spaces.
- First name only, no "Dear"
- One specific reason you're reaching out (role + company)
- Soft call to action at the end
- Human tone, no emojis
{extra}
Contact first name: {first_name}
Role: {job_title} at {company}

My background (brief):
{base_cv[:400]}

Write ONLY the message, nothing else:"""

    text = _chat(_prompt(), max_tokens=120)

    # Retry once with explicit character count if over limit
    if len(text) > _LINKEDIN_LIMIT:
        text = _chat(
            _prompt(f"\nIMPORTANT: your previous attempt was {len(text)} chars. Try again, shorter.\n"),
            max_tokens=100,
        )

    # Hard truncate at word boundary as last resort
    if len(text) > _LINKEDIN_LIMIT:
        text = text[:_LINKEDIN_LIMIT].rsplit(" ", 1)[0].rstrip(",.;:")

    return text
