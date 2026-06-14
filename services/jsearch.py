import re
from urllib.parse import urlparse, urlunparse
import httpx
from config import get_settings

# Subdomini country-specific da normalizzare → country target
_COUNTRY_SUBDOMAIN_RE = re.compile(
    r'^([a-z]{2})\.(indeed|glassdoor|linkedin|monster|stepstone|infojobs)\.', re.IGNORECASE
)


def normalize_job_url(url: str, target_country: str = "it") -> str:
    """Sostituisce il subdomain country-specific con target_country per i siti noti."""
    if not url:
        return url
    parsed = urlparse(url)
    host = parsed.netloc
    new_host = _COUNTRY_SUBDOMAIN_RE.sub(
        lambda m: f"{target_country}.{m.group(2)}.", host
    )
    if new_host == host:
        return url
    return urlunparse(parsed._replace(netloc=new_host))

JSEARCH_BASE = "https://jsearch.p.rapidapi.com"

ENGLISH_PATTERNS = re.compile(
    r"\b(english|inglese|fluent\s+in\s+english|english\s+(required|mandatory|proficiency|speaker|native)|"
    r"c1|c2|bilingual|mother\s+tongue\s+english)\b",
    re.IGNORECASE,
)


def requires_english(job: dict) -> bool:
    text = f"{job.get('title', '')} {job.get('description', '')}"
    return bool(ENGLISH_PATTERNS.search(text))


async def search_jobs(query: str, locations: list[str], num_pages: int = 1, country: str = "it", english_only: bool = False) -> list[dict]:
    settings = get_settings()
    if not settings.jsearch_api_key:
        raise ValueError("JSEARCH_API_KEY non configurata nel file .env")
    headers = {
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
        "x-rapidapi-key": settings.jsearch_api_key,
    }
    results = []
    async with httpx.AsyncClient() as client:
        for location in locations:
            for page in range(1, num_pages + 1):
                params = {
                    "query": f"{query} in {location}" if location.lower() != "remote" else f"{query} remote",
                    "page": str(page),
                    "num_pages": "1",
                    "date_posted": "month",
                    "country": country,
                }
                resp = await client.get(
                    f"{JSEARCH_BASE}/search",
                    headers=headers,
                    params=params,
                    timeout=15.0,
                )
                resp.raise_for_status()
                data = resp.json()
                for job in data.get("data", []):
                    if not _city_matches(job, location):
                        continue
                    parsed = _parse_job(job)
                    if english_only and not requires_english(parsed):
                        continue
                    results.append(parsed)
    return results


def _city_matches(raw: dict, location: str) -> bool:
    """Return True if the job's city roughly matches the requested location."""
    if location.lower() == "remote":
        return True
    job_city = (raw.get("job_city") or "").lower().strip()
    if not job_city:
        return True  # no city data → keep (could be remote or unlisted)
    loc = location.lower().strip()
    return loc in job_city or job_city in loc


def _parse_job(raw: dict) -> dict:
    return {
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "location": f"{raw.get('job_city', '')} {raw.get('job_country', '')}".strip(),
        "description": raw.get("job_description", ""),
        "source_url": normalize_job_url(raw.get("job_apply_link") or raw.get("job_url", "")),
        "employer_logo": raw.get("employer_logo", ""),
        "salary": _format_salary(raw),
        "job_type": raw.get("job_employment_type", ""),
    }


def _format_salary(raw: dict) -> str:
    min_s = raw.get("job_min_salary")
    max_s = raw.get("job_max_salary")
    currency = raw.get("job_salary_currency", "")
    period = raw.get("job_salary_period", "")
    if min_s and max_s:
        return f"{currency} {min_s:,.0f} – {max_s:,.0f} / {period}"
    return ""
