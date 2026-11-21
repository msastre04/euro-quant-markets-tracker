import json
import os
import re
import time
from datetime import datetime, timezone
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INTERNSHIPS_FILE = os.path.join(DATA_DIR, "internships.json")

# 1. Greenhouse public boards (verified slugs)
GREENHOUSE_BOARDS = [
    {"token": "optiver", "company": "Optiver", "category": "Market Maker / Prop"},
    {"token": "imc", "company": "IMC Trading", "category": "Market Maker / Prop"},
    {"token": "flowtraders", "company": "Flow Traders", "category": "Market Maker / Prop"},
    {"token": "jumptrading", "company": "Jump Trading", "category": "Market Maker / Prop"},
    {"token": "hudsonrivertrading", "company": "Hudson River Trading", "category": "Market Maker / Prop"},
    {"token": "davinciderivatives", "company": "Da Vinci Derivatives", "category": "Market Maker / Prop"},
    {"token": "quberesearchandtechnologies", "company": "Qube Research & Technologies (QRT)", "category": "Hedge Fund / Quant"},
    {"token": "squarepointcapital", "company": "Squarepoint Capital", "category": "Hedge Fund / Quant"},
    {"token": "point72", "company": "Point72", "category": "Hedge Fund / Quant"},
    {"token": "bamfunds", "company": "Balyasny Asset Management", "category": "Hedge Fund / Quant"},
    {"token": "janestreet", "company": "Jane Street", "category": "Market Maker / Prop"},
    {"token": "citadelsecurities", "company": "Citadel Securities", "category": "Market Maker / Prop"},
    {"token": "drweng", "company": "DRW", "category": "Market Maker / Prop"},
    {"token": "sig", "company": "Susquehanna (SIG)", "category": "Market Maker / Prop"},
    {"token": "gresearch", "company": "G-Research", "category": "Hedge Fund / Quant"},
    {"token": "marshallwace", "company": "Marshall Wace", "category": "Hedge Fund / Quant"},
    {"token": "man", "company": "Man Group", "category": "Hedge Fund / Quant"},
    {"token": "exoduspoint", "company": "ExodusPoint", "category": "Hedge Fund / Quant"},
]

# 2. Lever public boards
LEVER_BOARDS = [
    {"token": "wintermute-trading", "company": "Wintermute", "category": "Market Maker / Prop"},
    {"token": "mavensecurities", "company": "Maven Securities", "category": "Market Maker / Prop"},
    {"token": "cfm", "company": "Capital Fund Management (CFM)", "category": "Hedge Fund / Quant"},
]

# 3. SmartRecruiters public boards
SMARTRECRUITERS_BOARDS = [
    {"token": "SquarepointCapital", "company": "Squarepoint Capital", "category": "Hedge Fund / Quant"},
    {"token": "Marex", "company": "Marex (Marex Solutions)", "category": "Courtier / Broker"},
    {"token": "Vitol", "company": "Vitol", "category": "Commodities & Energy"},
    {"token": "Trafigura", "company": "Trafigura", "category": "Commodities & Energy"},
]

CITY_PATTERNS = {
    "Paris": [r"\bparis\b", r"\bfrance\b"],
    "Londres": [r"\blondon\b", r"\blondres\b", r"\bunited kingdom\b", r"\buk\b"],
    "Genève": [r"\bgeneva\b", r"\bgen[eè]ve\b", r"\bswitzerland\b"],
    "Amsterdam": [r"\bamsterdam\b", r"\bnetherlands\b"],
    "Francfort": [r"\bfrankfurt\b", r"\bfrancfort\b", r"\bgermany\b"],
    "Milan": [r"\bmilan\b", r"\bmilano\b", r"\bitaly\b"],
}

INTERN_KEYWORDS = [
    "intern", "internship", "stage", "stagiaire", "off-cycle", "off cycle",
    "summer", "graduate", "placement", "trainee", "industrial placement",
    "spring week", "insight", "analyst program"
]

EXCLUDE_KEYWORDS = [
    "hr ", "human resources", "recruiter", "talent acquisition", "legal",
    "marketing", "facilities", "receptionist", "office manager", "accounting",
    "payroll", "events", "executive assistant", "pa to"
]

def detect_city(location_str: str):
    loc = (location_str or "").lower()
    for city, patterns in CITY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, loc):
                return city
    return None

def is_relevant_internship(title: str) -> bool:
    t = (title or "").lower()
    if not any(k in t for k in INTERN_KEYWORDS):
        return False
    if any(k in t for k in EXCLUDE_KEYWORDS):
        return False
    return True

def classify_role(title: str) -> str:
    t = (title or "").lower()
    if any(k in t for k in ["structur", "derivatives sales", "solutions", "sales"]):
        return "Structuring"
    if any(k in t for k in ["quant", "research", "strats", "pricing", "stochastic", "alpha"]):
        return "Quant Research / Dev"
    if any(k in t for k in ["data scien", "machine learning", "ai ", "analytics", "data engineer", "software", "developer", "engineer"]):
        return "Data Science & Analytics"
    return "Trading & Market Making"

def classify_duration(title: str) -> str:
    t = (title or "").lower()
    if "summer" in t or "spring" in t or "insight" in t:
        return "Summer (2-3 mois)"
    return "Off-cycle / 6 mois"

def load_existing_jobs():
    if not os.path.exists(INTERNSHIPS_FILE):
        return []
    with open(INTERNSHIPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_greenhouse_jobs(headers):
    collected = []
    for board in GREENHOUSE_BOARDS:
        token = board["token"]
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[GH-SKIP] {board['company']} ({token}): HTTP {resp.status_code}")
                continue
            jobs = resp.json().get("jobs", [])
            count = 0
            for j in jobs:
                title = j.get("title", "")
                loc_name = (j.get("location") or {}).get("name", "")
                # Also check offices list if location is generic
                offices = " ".join([o.get("name", "") for o in j.get("offices", [])])
                city = detect_city(f"{loc_name} {offices}")
                if not city or not is_relevant_internship(title):
                    continue

                updated_at = j.get("updated_at") or ""
                posted_date = updated_at[:10] if len(updated_at) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")

                collected.append({
                    "id": f"gh-{token}-{j.get('id')}",
                    "company": board["company"],
                    "category": board["category"],
                    "title": title.strip(),
                    "role": classify_role(title),
                    "city": city,
                    "duration": classify_duration(title),
                    "posted_date": posted_date,
                    "status": "Ouvert",
                    "url": j.get("absolute_url")
                })
                count += 1
            print(f"[GH-OK] {board['company']}: {len(jobs)} total -> {count} stage(s) EU")
            time.sleep(0.3)
        except Exception as e:
            print(f"[GH-ERR] {board['company']}: {e}")
    return collected

def fetch_lever_jobs(headers):
    collected = []
    for board in LEVER_BOARDS:
        token = board["token"]
        url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[LV-SKIP] {board['company']} ({token}): HTTP {resp.status_code}")
                continue
            jobs = resp.json()
            count = 0
            for j in jobs:
                title = j.get("text", "")
                cats = j.get("categories") or {}
                loc_str = f"{cats.get('location', '')} {' '.join(cats.get('allLocations', []))}"
                city = detect_city(loc_str)
                if not city or not is_relevant_internship(title):
                    continue

                created_ms = j.get("createdAt")
                if created_ms:
                    posted_date = datetime.fromtimestamp(created_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
                else:
                    posted_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                collected.append({
                    "id": f"lv-{token}-{j.get('id')}",
                    "company": board["company"],
                    "category": board["category"],
                    "title": title.strip(),
                    "role": classify_role(title),
                    "city": city,
                    "duration": classify_duration(title),
                    "posted_date": posted_date,
                    "status": "Ouvert",
                    "url": j.get("hostedUrl")
                })
                count += 1
            print(f"[LV-OK] {board['company']}: {len(jobs)} total -> {count} stage(s) EU")
            time.sleep(0.3)
        except Exception as e:
            print(f"[LV-ERR] {board['company']}: {e}")
    return collected

def fetch_smartrecruiters_jobs(headers):
    collected = []
    for board in SMARTRECRUITERS_BOARDS:
        token = board["token"]
        url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[SR-SKIP] {board['company']} ({token}): HTTP {resp.status_code}")
                continue
            jobs = resp.json().get("content", [])
            count = 0
            for j in jobs:
                title = j.get("name", "")
                loc = j.get("location") or {}
                loc_str = f"{loc.get('city', '')} {loc.get('country', '')}"
                city = detect_city(loc_str)
                if not city or not is_relevant_internship(title):
                    continue

                rel_date = j.get("releasedDate") or ""
                posted_date = rel_date[:10] if len(rel_date) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                posting_id = j.get("id")

                collected.append({
                    "id": f"sr-{token.lower()}-{posting_id}",
                    "company": board["company"],
                    "category": board["category"],
                    "title": title.strip(),
                    "role": classify_role(title),
                    "city": city,
                    "duration": classify_duration(title),
                    "posted_date": posted_date,
                    "status": "Ouvert",
                    "url": f"https://jobs.smartrecruiters.com/{token}/{posting_id}"
                })
                count += 1
            print(f"[SR-OK] {board['company']}: {len(jobs)} total -> {count} stage(s) EU")
            time.sleep(0.3)
        except Exception as e:
            print(f"[SR-ERR] {board['company']}: {e}")
    return collected

def main():
    headers = {"User-Agent": "EuroQuantMarketsTracker/1.1"}
    existing = load_existing_jobs()
    # Keep only manually added jobs (non-scraped prefixes)
    manual_jobs = [
        j for j in existing
        if not str(j.get("id", "")).startswith(("gh-", "lv-", "sr-"))
    ]

    scraped_jobs = []
    scraped_jobs.extend(fetch_greenhouse_jobs(headers))
    scraped_jobs.extend(fetch_lever_jobs(headers))
    scraped_jobs.extend(fetch_smartrecruiters_jobs(headers))

    merged_map = {}
    for job in manual_jobs + scraped_jobs:
        merged_map[job["id"]] = job

    merged_list = sorted(
        merged_map.values(),
        key=lambda x: x.get("posted_date", ""),
        reverse=True
    )

    with open(INTERNSHIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_list, f, ensure_ascii=False, indent=2)

    print(f"Total enregistré dans internships.json : {len(merged_list)} offres.")

if __name__ == "__main__":
    main()
