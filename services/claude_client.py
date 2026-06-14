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


def draft_linkedin_message(
    contact_name: str,
    job_title: str,
    company: str,
    job_description: str,
    base_cv: str,
) -> str:
    prompt = f"""Write a concise, natural LinkedIn connection request message.

RULES:
- Max 300 characters (LinkedIn limit for connection notes)
- First name only, no "Dear"
- One specific reason you're reaching out (mention role/company)
- End with a soft call to action (e.g. "happy to share my background")
- Sound human, not like a template
- No emojis

Contact first name: {contact_name.split()[0]}
Role I'm applying for: {job_title} at {company}

My background summary (from CV):
{base_cv[:800]}

Job context:
{job_description[:800]}

Write only the message text:"""

    return _chat(prompt, max_tokens=200)
