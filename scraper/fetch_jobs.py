import json
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INTERNSHIPS_FILE = os.path.join(DATA_DIR, "internships.json")

# 1. Greenhouse public boards (verified active tokens + broadened keyword matching)
GREENHOUSE_BOARDS = [
    {"token": "optiver", "company": "Optiver", "category": "Market Maker / Prop"},
    {"token": "imc", "company": "IMC Trading", "category": "Market Maker / Prop"},
    {"token": "flowtraders", "company": "Flow Traders", "category": "Market Maker / Prop"},
    {"token": "jumptrading", "company": "Jump Trading", "category": "Market Maker / Prop"},
    {"token": "davinciderivatives", "company": "Da Vinci Derivatives", "category": "Market Maker / Prop"},
    {"token": "quberesearchandtechnologies", "company": "Qube Research & Technologies (QRT)", "category": "Hedge Fund / Quant"},
    {"token": "squarepointcapital", "company": "Squarepoint Capital", "category": "Hedge Fund / Quant"},
    {"token": "point72", "company": "Point72", "category": "Hedge Fund / Quant"},
    {"token": "janestreet", "company": "Jane Street", "category": "Market Maker / Prop"},
    {"token": "drweng", "company": "DRW", "category": "Market Maker / Prop"},
    {"token": "marshallwace", "company": "Marshall Wace", "category": "Hedge Fund / Quant"},
    {"token": "exoduspoint", "company": "ExodusPoint", "category": "Hedge Fund / Quant"},
    {"token": "hudsonrivertrading", "company": "Hudson River Trading", "category": "Market Maker / Prop"},
    {"token": "sig", "company": "Susquehanna (SIG)", "category": "Market Maker / Prop"},
]

# 2. Lever public boards
LEVER_BOARDS = [
    {"token": "wintermute-trading", "company": "Wintermute", "category": "Market Maker / Prop"},
    {"token": "mavensecurities", "company": "Maven Securities", "category": "Market Maker / Prop"},
    {"token": "cfm", "company": "Capital Fund Management (CFM)", "category": "Hedge Fund / Quant"},
]

# 3. SmartRecruiters public boards
SMARTRECRUITERS_BOARDS = [
    {"token": "Vitol", "company": "Vitol", "category": "Commodities & Energy"},
    {"token": "Marex", "company": "Marex (Marex Solutions)", "category": "Courtier / Broker"},
    {"token": "Trafigura", "company": "Trafigura", "category": "Commodities & Energy"},
]

# 4. Workday single-shot lightweight fetch (avoids HTTP 429 rate limits on GitHub Actions)
WORKDAY_BOARDS = [
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
        "company": "Deutsche Bank",
        "category": "Banque",
        "url": "https://db.wd3.myworkdayjobs.com/wday/cxs/db/DBWebsite/jobs",
        "base_job_url": "https://db.wd3.myworkdayjobs.com/en-US/DBWebsite"
    },
    {
        "company": "Trafigura",
        "category": "Commodities & Energy",
        "url": "https://trafigura.wd3.myworkdayjobs.com/wday/cxs/trafigura/TrafiguraCareerSite/jobs",
        "base_job_url": "https://trafigura.wd3.myworkdayjobs.com/en-US/TrafiguraCareerSite"
    },
    {
        "company": "Citigroup",
        "category": "Banque US",
        "url": "https://citi.wd5.myworkdayjobs.com/wday/cxs/citi/2/jobs",
        "base_job_url": "https://citi.wd5.myworkdayjobs.com/en-US/2"
    },
]

# 5. Welcome to the Jungle (WTTJ) public Algolia search index for French banks & energy houses
WTTJ_QUERIES = [
    {"query": "Société Générale trading quant structuration stage", "default_company": "Société Générale (SG CIB)", "category": "Banque"},
    {"query": "BNP Paribas trading quant structuration stage", "default_company": "BNP Paribas (CIB)", "category": "Banque"},
    {"query": "Crédit Agricole CIB trading quant structuration stage", "default_company": "Crédit Agricole CIB", "category": "Banque"},
    {"query": "Natixis trading quant structuration stage", "default_company": "Natixis CIB (Groupe BPCE)", "category": "Banque"},
    {"query": "ODDO BHF trading quant structuration stage", "default_company": "ODDO BHF", "category": "Banque"},
    {"query": "TotalEnergies trading gas power oil stage", "default_company": "TotalEnergies (Trading & Shipping)", "category": "Commodities & Energy"},
    {"query": "ENGIE Global Markets trading quant stage", "default_company": "ENGIE Global Markets", "category": "Commodities & Energy"},
    {"query": "Marex trading commodities stage", "default_company": "Marex (Marex Solutions)", "category": "Courtier / Broker"},
    {"query": "Kepler Cheuvreux trading equity quant stage", "default_company": "Kepler Cheuvreux", "category": "Courtier / Broker"},
    {"query": "stage trading quant structuration commodities", "default_company": None, "category": "Banque"},
]

# 6. Public French/EU Job Aggregator APIs (Arbeitnow + Google News/Job RSS fallbacks)
FRENCH_BANKS_AND_ENERGY = {
    "societe generale": ("Société Générale (SG CIB)", "Banque"),
    "société générale": ("Société Générale (SG CIB)", "Banque"),
    "sg cib": ("Société Générale (SG CIB)", "Banque"),
    "bnp paribas": ("BNP Paribas (CIB)", "Banque"),
    "credit agricole": ("Crédit Agricole CIB", "Banque"),
    "crédit agricole": ("Crédit Agricole CIB", "Banque"),
    "cacib": ("Crédit Agricole CIB", "Banque"),
    "natixis": ("Natixis CIB (Groupe BPCE)", "Banque"),
    "oddo": ("ODDO BHF", "Banque"),
    "cic": ("CIC Market Solutions", "Banque"),
    "lcl": ("LCL (Banque des Entreprises / Marchés)", "Banque"),
    "totalenergies": ("TotalEnergies (Trading & Shipping)", "Commodities & Energy"),
    "total energies": ("TotalEnergies (Trading & Shipping)", "Commodities & Energy"),
    "engie": ("ENGIE Global Markets", "Commodities & Energy"),
    "edf trading": ("EDF Trading", "Commodities & Energy"),
    "marex": ("Marex (Marex Solutions)", "Courtier / Broker"),
    "vitol": ("Vitol", "Commodities & Energy"),
    "trafigura": ("Trafigura", "Commodities & Energy"),
    "gunvor": ("Gunvor Group", "Commodities & Energy"),
    "mercuria": ("Mercuria", "Commodities & Energy"),
    "kepler": ("Kepler Cheuvreux", "Courtier / Broker"),
    "cfm": ("Capital Fund Management (CFM)", "Hedge Fund / Quant"),
    "amundi": ("Amundi", "Hedge Fund / Quant"),
    "axa im": ("AXA IM", "Hedge Fund / Quant"),
}

CITY_PATTERNS = {
    "Paris": [r"\bparis\b", r"\bla d[ée]fense\b", r"\bcourbevoie\b", r"\bputeaux\b", r"\bmontrouge\b", r"\bfrance\b", r"\b[îi]le-de-france\b"],
    "Londres": [r"\blondon\b", r"\blondres\b", r"\bcanary wharf\b", r"\bunited kingdom\b", r"\buk\b"],
    "Genève": [r"\bgeneva\b", r"\bgen[eè]ve\b", r"\bswitzerland\b", r"\bsuisse\b"],
    "Amsterdam": [r"\bamsterdam\b", r"\bnetherlands\b", r"\bpays-bas\b"],
    "Francfort": [r"\bfrankfurt\b", r"\bfrancfort\b", r"\bgermany\b", r"\ballemagne\b"],
    "Milan": [r"\bmilan\b", r"\bmilano\b", r"\bitaly\b", r"\bitalie\b"],
}

NON_EU_EXCLUDE = [
    "sydney", "melbourne", "singapore", "hong kong", "tokyo", "shanghai",
    "new york", "chicago", "boston", "houston", "san francisco", "toronto",
    "mumbai", "bengaluru", "bangalore", "dubai", "austin", "seattle", "pune"
]

INTERN_KEYWORDS = [
    "intern", "internship", "stage", "stagiaire", "off-cycle", "off cycle",
    "summer", "graduate", "placement", "trainee", "industrial placement",
    "spring week", "insight", "analyst program", "césure", "cesure", "vie ",
    "2026", "2027"
]

FRONT_OFFICE_KEYWORDS = [
    "trading", "trader", "structur", "quant", "quantitative", "market",
    "commodit", "energy", "oil", "gas", "power", "equity", "derivatives",
    "delta one", "fixed income", "rates", "fx", "credit", "sales",
    "data scien", "machine learning", "strats", "risk", "portfolio",
    "execution", "algo", "broker", "research", "pricing", "front office",
    "salle de march", "produits structur", "matières premières", "énergie"
]

EXCLUDE_KEYWORDS = [
    "hr ", "human resources", "recruiter", "talent acquisition", "legal",
    "marketing", "facilities", "receptionist", "office manager", "accounting",
    "payroll", "events", "executive assistant", "pa to", "audit", "compliance",
    "communication", "rh ", "ressources humaines", "juridique", "comptab",
    "contrôle de gestion", "controle de gestion", "inspecteur"
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
    if any(k in t for k in ["structur", "derivatives sales", "solutions", "sales", "produits structur"]):
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

def match_known_french_actor(org_name: str, default_company=None, default_cat="Banque"):
    low = (org_name or "").lower()
    for key, (clean_name, cat) in FRENCH_BANKS_AND_ENERGY.items():
        if key in low:
            return clean_name, cat
    if default_company:
        return default_company, default_cat
    return None, None

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
                city = detect_city(loc_name, title)
                # For Jane Street / Citadel / etc., "2027" + Trading/Quant/Software is an internship
                is_intern = is_relevant_internship(title, require_fo_keyword=False)
                if not city or not is_intern:
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
                posted_date = (
                    datetime.fromtimestamp(created_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
                    if created_ms else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                )

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
            for j in jobs:
                title = j.get("name", "")
                loc = j.get("location") or {}
                loc_str = f"{loc.get('city', '')} {loc.get('country', '')}"
                city = detect_city(loc_str, title)
                if not city or not is_relevant_internship(title, require_fo_keyword=True):
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

def fetch_workday_single_shot():
    collected = []
    wd_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    for board in WORKDAY_BOARDS:
        company = board["company"]
        # Single lightweight POST request with 2.5s cooldown to avoid HTTP 429
        payload = {"appliedFacets": {}, "limit": 50, "offset": 0, "searchText": "intern stage trading"}
        try:
            resp = requests.post(board["url"], json=payload, headers=wd_headers, timeout=20)
            if resp.status_code != 200:
                print(f"[WD-SKIP] {company}: HTTP {resp.status_code}")
                time.sleep(2.0)
                continue
            postings = resp.json().get("jobPostings", [])
            count = 0
            for p in postings:
                ext_path = p.get("externalPath", "")
                if not ext_path:
                    continue
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
            print(f"[WD-OK] {company}: {len(postings)} analysées -> {count} stage(s) FO EU")
            time.sleep(2.5)
        except Exception as e:
            print(f"[WD-ERR] {company}: {e}")
    return collected

def fetch_wttj_french_markets():
    """Queries Welcome to the Jungle public Algolia index for French banks & energy desks."""
    collected = []
    # Public read-only Algolia search credentials used by welcometothejungle.com frontend
    algolia_url = "https://csekhvms53-dsn.algolia.net/1/indexes/*/queries"
    algolia_headers = {
        "X-Algolia-Application-Id": "CSEKHVMS53",
        "X-Algolia-API-Key": "4bd8f6215d0cc52b26430765769e65a0",
        "Content-Type": "application/json",
        "Referer": "https://www.welcometothejungle.com/",
        "Origin": "https://www.welcometothejungle.com"
    }

    requests_payload = []
    for item in WTTJ_QUERIES:
        params = urllib.parse.urlencode({
            "query": item["query"],
            "hitsPerPage": 25,
            "filters": 'contract_type:"internship" OR contract_type:"vie"'
        })
        requests_payload.append({
            "indexName": "wttj_jobs_production_fr",
            "params": params
        })

    try:
        resp = requests.post(
            algolia_url,
            json={"requests": requests_payload},
            headers=algolia_headers,
            timeout=20
        )
        if resp.status_code != 200:
            print(f"[WTTJ-SKIP] HTTP {resp.status_code}")
            return collected

        results = resp.json().get("results", [])
        seen_slugs = set()

        for idx, res in enumerate(results):
            q_meta = WTTJ_QUERIES[idx]
            hits = res.get("hits", [])
            for h in hits:
                slug = h.get("slug") or str(h.get("objectID"))
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                title = (h.get("name") or "").strip()
                org = h.get("organization") or {}
                org_name = (org.get("name") or "").strip()
                org_slug = org.get("slug") or ""

                offices = h.get("offices") or []
                loc_str = " ".join([f"{o.get('city', '')} {o.get('country', '')}" for o in offices])
                city = detect_city(loc_str, title)
                if not city:
                    continue

                if not is_relevant_internship(title, require_fo_keyword=True):
                    continue

                matched_company, matched_cat = match_known_french_actor(
                    org_name,
                    default_company=q_meta["default_company"] or org_name,
                    default_cat=q_meta["category"]
                )
                if not matched_company:
                    continue

                pub_at = h.get("published_at") or ""
                posted_date = pub_at[:10] if len(pub_at) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
                job_url = f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}" if org_slug else f"https://www.welcometothejungle.com/fr/jobs/{slug}"

                collected.append({
                    "id": f"wttj-{slug[:55]}",
                    "company": matched_company,
                    "category": matched_cat,
                    "title": title,
                    "role": classify_role(title),
                    "city": city,
                    "duration": classify_duration(title),
                    "posted_date": posted_date,
                    "status": "Ouvert",
                    "url": job_url
                })

        print(f"[WTTJ-OK] {len(collected)} stage(s) Front Office / Banques FR & Énergie trouvé(s)")
    except Exception as e:
        print(f"[WTTJ-ERR] {e}")

    return collected

def fetch_arbeitnow_eu(headers):
    """Fallback public European job board API (no auth, no rate limit)."""
    collected = []
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=headers, timeout=15)
        if resp.status_code != 200:
            return collected
        jobs = resp.json().get("data", [])
        for j in jobs:
            title = j.get("title", "")
            comp = j.get("company_name", "")
            loc = j.get("location", "")
            city = detect_city(loc, title)
            if not city or not is_relevant_internship(title, require_fo_keyword=True):
                continue
            matched_comp, matched_cat = match_known_french_actor(comp, default_company=comp, default_cat="Banque")
            collected.append({
                "id": f"abn-{j.get('slug', '')[:50]}",
                "company": matched_comp,
                "category": matched_cat,
                "title": title.strip(),
                "role": classify_role(title),
                "city": city,
                "duration": classify_duration(title),
                "posted_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "status": "Ouvert",
                "url": j.get("url")
            })
        print(f"[ABN-OK] {len(collected)} stage(s) EU trouvé(s)")
    except Exception as e:
        print(f"[ABN-ERR] {e}")
    return collected

def main():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EuroQuantMarketsTracker/1.3"}
    existing = load_existing_jobs()
    manual_jobs = [
        j for j in existing
        if not str(j.get("id", "")).startswith(("gh-", "lv-", "sr-", "wd-", "rss-", "wttj-", "abn-"))
    ]

    scraped_jobs = []
    scraped_jobs.extend(fetch_greenhouse_jobs(headers))
    scraped_jobs.extend(fetch_lever_jobs(headers))
    scraped_jobs.extend(fetch_smartrecruiters_jobs(headers))
    scraped_jobs.extend(fetch_wttj_french_markets())
    scraped_jobs.extend(fetch_workday_single_shot())
    scraped_jobs.extend(fetch_arbeitnow_eu(headers))

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
