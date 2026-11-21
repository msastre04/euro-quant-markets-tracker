import json
import os
import re
import time
from datetime import datetime, timezone
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INTERNSHIPS_FILE = os.path.join(DATA_DIR, "internships.json")

# Public Greenhouse boards for key Quant / Market Making / Hedge Fund firms
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
]

CITY_PATTERNS = {
    "Paris": [r"\bparis\b"],
    "Londres": [r"\blondon\b", r"\blondres\b"],
    "Genève": [r"\bgeneva\b", r"\bgen[eè]ve\b"],
    "Amsterdam": [r"\bamsterdam\b"],
    "Francfort": [r"\bfrankfurt\b", r"\bfrancfort\b"],
    "Milan": [r"\bmilan\b", r"\bmilano\b"],
}

INTERN_KEYWORDS = [
    "intern", "internship", "stage", "stagiaire", "off-cycle", "off cycle",
    "summer analyst", "summer associate", "graduate"
]

EXCLUDE_KEYWORDS = [
    "hr ", "human resources", "recruiter", "legal", "marketing", "facilities",
    "receptionist", "office manager", "accounting", "audit"
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
    if any(k in t for k in ["structur", "derivatives sales", "solutions"]):
        return "Structuring"
    if any(k in t for k in ["quant", "research", "strats", "pricing", "stochastic"]):
        return "Quant Research / Dev"
    if any(k in t for k in ["data scien", "machine learning", "ai ", "analytics", "data engineer"]):
        return "Data Science & Analytics"
    return "Trading & Market Making"

def classify_duration(title: str) -> str:
    t = (title or "").lower()
    if "summer" in t:
        return "Summer (2-3 mois)"
    return "Off-cycle / 6 mois"

def load_existing_jobs():
    if not os.path.exists(INTERNSHIPS_FILE):
        return []
    with open(INTERNSHIPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def fetch_greenhouse_jobs():
    collected = []
    headers = {"User-Agent": "EuroQuantMarketsTracker/1.0"}

    for board in GREENHOUSE_BOARDS:
        token = board["token"]
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[WARN] {board['company']} ({token}): HTTP {resp.status_code}")
                continue
            data = resp.json()
            jobs = data.get("jobs", [])
            count_added = 0

            for j in jobs:
                title = j.get("title", "")
                loc_name = (j.get("location") or {}).get("name", "")
                city = detect_city(loc_name)
                if not city:
                    continue
                if not is_relevant_internship(title):
                    continue

                updated_at = j.get("updated_at") or ""
                posted_date = updated_at[:10] if len(updated_at) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")

                job_id = f"gh-{token}-{j.get('id')}"
                collected.append({
                    "id": job_id,
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
                count_added += 1

            print(f"[OK] {board['company']}: {count_added} stage(s) européen(s) trouvé(s)")
            time.sleep(0.5)
        except Exception as e:
            print(f"[ERR] {board['company']}: {e}")

    return collected

def main():
    existing = load_existing_jobs()
    # Keep manually added / seed entries that do not start with 'gh-'
    manual_jobs = [j for j in existing if not str(j.get("id", "")).startswith("gh-")]
    scraped_jobs = fetch_greenhouse_jobs()

    # Deduplicate by ID
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
