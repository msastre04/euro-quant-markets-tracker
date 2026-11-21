import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INTERNSHIPS_FILE = os.path.join(DATA_DIR, "internships.json")

# 1. Greenhouse public boards
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
    {"token": "SocieteGenerale", "company": "Société Générale (SG CIB)", "category": "Banque"},
    {"token": "BNPParibas", "company": "BNP Paribas (CIB)", "category": "Banque"},
    {"token": "CreditAgricoleCIB", "company": "Crédit Agricole CIB", "category": "Banque"},
    {"token": "Natixis", "company": "Natixis CIB (Groupe BPCE)", "category": "Banque"},
    {"token": "TotalEnergies", "company": "TotalEnergies (Trading & Shipping)", "category": "Commodities & Energy"},
    {"token": "ENGIE", "company": "ENGIE Global Markets", "category": "Commodities & Energy"},
    {"token": "ODDOBHF", "company": "ODDO BHF", "category": "Banque"},
]

# 4. Workday public CXS JSON endpoints (used by major banks & commodity houses)
WORKDAY_BOARDS = [
    {
        "company": "Deutsche Bank",
        "category": "Banque",
        "url": "https://db.wd3.myworkdayjobs.com/wday/cxs/db/DBWebsite/jobs",
        "base_job_url": "https://db.wd3.myworkdayjobs.com/en-US/DBWebsite"
    },
    {
        "company": "Citigroup",
        "category": "Banque US",
        "url": "https://citi.wd5.myworkdayjobs.com/wday/cxs/citi/2/jobs",
        "base_job_url": "https://citi.wd5.myworkdayjobs.com/en-US/2"
    },
    {
        "company": "Trafigura",
        "category": "Commodities & Energy",
        "url": "https://trafigura.wd3.myworkdayjobs.com/wday/cxs/trafigura/TrafiguraCareerSite/jobs",
        "base_job_url": "https://trafigura.wd3.myworkdayjobs.com/en-US/TrafiguraCareerSite"
    },
    {
        "company": "BNP Paribas (CIB)",
        "category": "Banque",
        "url": "https://bnpparibas.wd3.myworkdayjobs.com/wday/cxs/bnpparibas/bnpparibas/jobs",
        "base_job_url": "https://bnpparibas.wd3.myworkdayjobs.com/en-US/bnpparibas"
    },
    {
        "company": "TotalEnergies (Trading & Shipping)",
        "category": "Commodities & Energy",
        "url": "https://totalenergies.wd3.myworkdayjobs.com/wday/cxs/totalenergies/TotalEnergiesCareers/jobs",
        "base_job_url": "https://totalenergies.wd3.myworkdayjobs.com/en-US/TotalEnergiesCareers"
    },
    {
        "company": "Barclays",
        "category": "Banque",
        "url": "https://barclays.wd3.myworkdayjobs.com/wday/cxs/barclays/External_Career_Site_Barclays/jobs",
        "base_job_url": "https://barclays.wd3.myworkdayjobs.com/en-US/External_Career_Site_Barclays"
    },
]

# 5. Direct RSS / XML / JSON feeds from French banks & energy majors (SG, CACIB, TotalEnergies, Engie)
RSS_FEEDS = [
    {
        "company": "Société Générale (SG CIB)",
        "category": "Banque",
        "url": "https://careers.societegenerale.com/en/rss/jobs?search=intern+trading+quant+structuring"
    },
    {
        "company": "Crédit Agricole CIB",
        "category": "Banque",
        "url": "https://jobs.ca-cib.com/rss/jobs"
    },
    {
        "company": "TotalEnergies (Trading & Shipping)",
        "category": "Commodities & Energy",
        "url": "https://jobs.totalenergies.com/en_US/careers/SearchJobs/feed/"
    },
]

CITY_PATTERNS = {
    "Paris": [r"\bparis\b", r"\bla d[ée]fense\b", r"\bcourbevoie\b", r"\bpup?teaux\b", r"\bmontrouge\b", r"\bfrance\b"],
    "Londres": [r"\blondon\b", r"\blondres\b", r"\bcanary wharf\b", r"\bunited kingdom\b"],
    "Genève": [r"\bgeneva\b", r"\bgen[eè]ve\b", r"\bswitzerland\b"],
    "Amsterdam": [r"\bamsterdam\b", r"\bnetherlands\b"],
    "Francfort": [r"\bfrankfurt\b", r"\bfrancfort\b", r"\bgermany\b"],
    "Milan": [r"\bmilan\b", r"\bmilano\b", r"\bitaly\b"],
}

NON_EU_EXCLUDE = [
    "sydney", "melbourne", "singapore", "hong kong", "tokyo", "shanghai",
    "new york", "chicago", "boston", "houston", "san francisco", "toronto",
    "mumbai", "bengaluru", "bangalore", "dubai", "austin", "seattle"
]

INTERN_KEYWORDS = [
    "intern", "internship", "stage", "stagiaire", "off-cycle", "off cycle",
    "summer", "graduate", "placement", "trainee", "industrial placement",
    "spring week", "insight", "analyst program", "césure", "cesure", "vie "
]

FRONT_OFFICE_KEYWORDS = [
    "trading", "trader", "structur", "quant", "quantitative", "market",
    "commodit", "energy", "oil", "gas", "power", "equity", "derivatives",
    "delta one", "fixed income", "rates", "fx", "credit", "sales",
    "data scien", "machine learning", "strats", "risk", "portfolio",
    "execution", "algo", "broker", "research", "pricing"
]

EXCLUDE_KEYWORDS = [
    "hr ", "human resources", "recruiter", "talent acquisition", "legal",
    "marketing", "facilities", "receptionist", "office manager", "accounting",
    "payroll", "events", "executive assistant", "pa to", "audit", "compliance",
    "communication", "rh ", "ressources humaines", "juridique", "comptab"
]

def detect_city(location_str: str, title_str: str = ""):
    combined = f"{location_str or ''} {title_str or ''}".lower()
    if any(bad in combined for bad in NON_EU_EXCLUDE):
        return None
    for city, patterns in CITY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, combined):
                return city
    return None

def is_relevant_internship(title: str, require_fo_keyword: bool = False) -> bool:
    t = (title or "").lower()
    if not any(k in t for k in INTERN_KEYWORDS):
        return False
    if any(k in t for k in EXCLUDE_KEYWORDS):
        return False
    if require_fo_keyword and not any(k in t for k in FRONT_OFFICE_KEYWORDS):
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
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
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
                # Strict check on location.name + title so global offices list doesn't mislabel Sydney jobs
                city = detect_city(loc_name, title)
                if not city or not is_relevant_internship(title, require_fo_keyword=False):
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
            time.sleep(0.25)
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
                loc_str = cats.get("location", "")
                city = detect_city(loc_str, title)
                if not city or not is_relevant_internship(title, require_fo_keyword=False):
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
            time.sleep(0.25)
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
            is_large_corp = board["category"] in ("Banque", "Commodities & Energy")
            for j in jobs:
                title = j.get("name", "")
                loc = j.get("location") or {}
                loc_str = f"{loc.get('city', '')} {loc.get('country', '')}"
                city = detect_city(loc_str, title)
                if not city or not is_relevant_internship(title, require_fo_keyword=is_large_corp):
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
            time.sleep(0.25)
        except Exception as e:
            print(f"[SR-ERR] {board['company']}: {e}")
    return collected

def fetch_workday_jobs():
    collected = []
    wd_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    search_terms = ["intern", "stage", "off-cycle", "trading", "quant"]

    for board in WORKDAY_BOARDS:
        company = board["company"]
        seen_paths = set()
        count = 0
        for term in search_terms:
            payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term}
            try:
                resp = requests.post(board["url"], json=payload, headers=wd_headers, timeout=15)
                if resp.status_code != 200:
                    print(f"[WD-SKIP] {company} ({term}): HTTP {resp.status_code}")
                    break
                postings = resp.json().get("jobPostings", [])
                for p in postings:
                    ext_path = p.get("externalPath", "")
                    if not ext_path or ext_path in seen_paths:
                        continue
                    seen_paths.add(ext_path)

                    title = p.get("title", "")
                    loc_text = p.get("locationsText", "")
                    city = detect_city(loc_text, title)
                    if not city or not is_relevant_internship(title, require_fo_keyword=True):
                        continue

                    job_url = f"{board['base_job_url']}{ext_path}"
                    slug_id = re.sub(r"[^a-zA-Z0-9]+", "-", ext_path).strip("-")[:60]

                    collected.append({
                        "id": f"wd-{slug_id}",
                        "company": company,
                        "category": board["category"],
                        "title": title.strip(),
                        "role": classify_role(title),
                        "city": city,
                        "duration": classify_duration(title),
                        "posted_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        "status": "Ouvert",
                        "url": job_url
                    })
                    count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"[WD-ERR] {company}: {e}")
                break
        if count > 0:
            print(f"[WD-OK] {company}: {count} stage(s) FO EU trouvé(s)")
    return collected

def fetch_rss_jobs(headers):
    collected = []
    for feed in RSS_FEEDS:
        company = feed["company"]
        try:
            resp = requests.get(feed["url"], headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[RSS-SKIP] {company}: HTTP {resp.status_code}")
                continue
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            count = 0
            for item in items:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = (item.findtext("description") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()

                city = detect_city(f"{title} {desc}", title)
                if not city or not is_relevant_internship(title, require_fo_keyword=True):
                    continue

                posted_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if pub_date:
                    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
                        try:
                            posted_date = datetime.strptime(pub_date, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            pass

                uid = re.sub(r"[^a-zA-Z0-9]+", "-", link)[-50:]
                collected.append({
                    "id": f"rss-{uid}",
                    "company": company,
                    "category": feed["category"],
                    "title": title,
                    "role": classify_role(title),
                    "city": city,
                    "duration": classify_duration(title),
                    "posted_date": posted_date,
                    "status": "Ouvert",
                    "url": link
                })
                count += 1
            print(f"[RSS-OK] {company}: {len(items)} items -> {count} stage(s) FO EU")
        except Exception as e:
            print(f"[RSS-ERR] {company}: {e}")
    return collected

def main():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EuroQuantMarketsTracker/1.2"}
    existing = load_existing_jobs()
    manual_jobs = [
        j for j in existing
        if not str(j.get("id", "")).startswith(("gh-", "lv-", "sr-", "wd-", "rss-"))
    ]

    scraped_jobs = []
    scraped_jobs.extend(fetch_greenhouse_jobs(headers))
    scraped_jobs.extend(fetch_lever_jobs(headers))
    scraped_jobs.extend(fetch_smartrecruiters_jobs(headers))
    scraped_jobs.extend(fetch_workday_jobs())
    scraped_jobs.extend(fetch_rss_jobs(headers))

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
