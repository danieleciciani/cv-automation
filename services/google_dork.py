import re
import urllib.parse
from ddgs import DDGS

HR_ROLES = [
    "HR Manager", "Talent Acquisition", "Recruiter", "People Partner",
    "HR Business Partner", "Hiring Manager", "Head of People",
]

_LOCATION_RE = re.compile(r"Location:\s*([^·\n\|]{3,60})", re.IGNORECASE)


def search_linkedin_contacts(company: str, region: str | None = None, max_results: int = 8) -> list[dict]:
    """
    Search LinkedIn profiles for HR/Talent people at the given company via DuckDuckGo.
    Optionally biases results toward `region` (city/area).
    Returns [{name, role, linkedin_url, location}], sorted by region match then A→Z.
    """
    roles_query = " OR ".join(f'"{r}"' for r in HR_ROLES[:4])
    # Including the region in the query steers DDG toward local profiles
    # and makes LinkedIn snippets more likely to include Location:
    region_hint = f' "{region}"' if region else ""
    query = f'site:linkedin.com/in "{company}"{region_hint} ({roles_query})'

    contacts = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results * 2):
            url = r.get("href", "")
            if "linkedin.com/in/" not in url:
                continue
            name, role = _parse_title(r.get("title", ""), company)
            location = _parse_location(r.get("body", ""))
            contacts.append({"name": name, "role": role, "linkedin_url": url, "location": location})
            if len(contacts) >= max_results:
                break

    return contacts


def sort_contacts_by_region(contacts: list[dict], region: str | None) -> list[dict]:
    """
    Sort order:
      1. Contacts whose location matches the region (A→Z by location)
      2. Contacts with a location but no region match (A→Z by location)
      3. Contacts with no location (A→Z by name)
    """
    if not region:
        return sorted(contacts, key=lambda c: (c["location"] is None, (c["location"] or "").lower()))

    region_tokens = set(re.sub(r"[,/]", " ", region).lower().split())

    def _rank(c: dict) -> tuple:
        loc = (c.get("location") or "").lower()
        loc_tokens = set(re.sub(r"[,/]", " ", loc).split())
        match = bool(region_tokens & loc_tokens)
        has_loc = bool(loc)
        return (
            0 if match else (1 if has_loc else 2),  # tier
            loc if has_loc else (c.get("name") or "").lower(),
        )

    return sorted(contacts, key=_rank)


def _parse_title(title: str, company: str) -> tuple[str, str]:
    title = re.sub(r"\s*[\|–]\s*LinkedIn.*$", "", title, flags=re.IGNORECASE).strip()
    parts = title.split(" - ", 1)
    name = parts[0].strip()
    role = ""
    if len(parts) > 1:
        role = re.sub(rf"\s+at\s+{re.escape(company)}.*$", "", parts[1], flags=re.IGNORECASE).strip()
    return name, role


def _parse_location(body: str) -> str | None:
    m = _LOCATION_RE.search(body)
    return m.group(1).strip() if m else None


def build_linkedin_search_url(company: str) -> str:
    roles_query = " OR ".join(f'"{r}"' for r in HR_ROLES[:5])
    query = f'site:linkedin.com/in "{company}" ({roles_query})'
    return "https://www.google.com/search?q=" + urllib.parse.quote(query)


def build_linkedin_direct_url(company: str) -> str:
    query = urllib.parse.quote(f"{company} HR recruiter talent")
    return f"https://www.linkedin.com/search/results/people/?keywords={query}"
