import json
import os
import re
import time
import urllib.parse
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
    {"token": "davinciderivatives", "company": "Da Vinci Derivatives", "category": "Market Maker / Prop"},
    {"token": "quberesearchandtechnologies", "company": "Qube Research & Technologies (QRT)", "category": "Hedge Fund / Quant"},
    {"token": "squarepointcapital", "company": "Squarepoint Capital", "category": "Hedge Fund / Quant"},
    {"token": "point72", "company": "Point72", "category": "Hedge Fund / Quant"},
    {"token": "janestreet", "company": "Jane Street", "category": "Market Maker / Prop"},
    {"token": "drweng", "company": "DRW", "category": "Market Maker / Prop"},
    {"token": "marshallwace", "company": "Marshall Wace", "category": "Hedge Fund / Quant"},
    {"token": "exoduspoint", "company": "ExodusPoint", "category": "Hedge Fund / Quant"},
]

# 2. Lever public boards
LEVER_BOARDS = [
    {"token": "wintermute-trading", "company": "Wintermute", "category": "Market Maker / Prop"},
]

# 3. SmartRecruiters public boards
SMARTRECRUITERS_BOARDS = [
    {"token": "Vitol", "company": "Vitol", "category": "Commodities & Energy"},
    {"token": "Marex", "company": "Marex (Marex Solutions)", "category": "Courtier / Broker"},
    {"token": "Trafigura", "company": "Trafigura", "category": "Commodities & Energy"},
]

# 4. Welcome to the Jungle (WTTJ) public Algolia search index
# Note: Algolia already filters by contract_type ("internship" or "vie"), so we DO NOT require
# the word "stage" in the French title (e.g., "Assistant Trader Dérivés (H/F)" is valid!).
WTTJ_QUERIES = [
    {"query": "Société Générale trading", "default_company": "Société Générale (SG CIB)", "category": "Banque"},
    {"query": "Société Générale quant structuration", "default_company": "Société Générale (SG CIB)", "category": "Banque"},
    {"query": "BNP Paribas trading quant", "default_company": "BNP Paribas (CIB)", "category": "Banque"},
    {"query": "BNP Paribas structuration marchés", "default_company": "BNP Paribas (CIB)", "category": "Banque"},
    {"query": "Crédit Agricole CIB trading quant", "default_company": "Crédit Agricole CIB", "category": "Banque"},
    {"query": "Natixis trading quant structuration", "default_company": "Natixis CIB (Groupe BPCE)", "category": "Banque"},
    {"query": "ODDO BHF trading quant", "default_company": "ODDO BHF", "category": "Banque"},
    {"query": "TotalEnergies trading", "default_company": "TotalEnergies (Trading & Shipping)", "category": "Commodities & Energy"},
    {"query": "ENGIE trading quant", "default_company": "ENGIE Global Markets", "category": "Commodities & Energy"},
    {"query": "Marex trading", "default_company": "Marex (Marex Solutions)", "category": "Courtier / Broker"},
    {"query": "Kepler Cheuvreux", "default_company": "Kepler Cheuvreux", "category": "Courtier / Broker"},
    {"query": "trading quant structuration", "default_company": None, "category": "Banque"},
]

# 5. eFinancialCareers public job search API (JSON endpoint used by efinancialcareers.fr / .co.uk)
EFC_QUERIES = [
    {"q": "Societe Generale intern trading quant", "location": "Paris", "city": "Paris", "company": "Société Générale (SG CIB)", "category": "Banque"},
    {"q": "BNP Paribas intern trading quant", "location": "Paris", "city": "Paris", "company": "BNP Paribas (CIB)", "category": "Banque"},
    {"q": "Credit Agricole CIB intern trading quant", "location": "Paris", "city": "Paris", "company": "Crédit Agricole CIB", "category": "Banque"},
    {"q": "Natixis intern trading quant", "location": "Paris", "city": "Paris", "company": "Natixis CIB (Groupe BPCE)", "category": "Banque"},
    {"q": "TotalEnergies intern trading", "location": "Geneva", "city": "Genève", "company": "TotalEnergies (Trading & Shipping)", "category": "Commodities & Energy"},
    {"q": "TotalEnergies intern trading", "location": "Paris", "city": "Paris", "company": "TotalEnergies (Trading & Shipping)", "category": "Commodities & Energy"},
    {"q": "Vitol intern trading", "location": "Geneva", "city": "Genève", "company": "Vitol", "category": "Commodities & Energy"},
    {"q": "Marex intern", "location": "London", "city": "Londres", "company": "Marex (Marex Solutions)", "category": "Courtier / Broker"},
    {"q": "quant intern", "location": "London", "city": "Londres", "company": None, "category": "Hedge Fund / Quant"},
    {"q": "quant stage", "location": "Paris", "city": "Paris", "company": None, "category": "Banque"},
]

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
    "qrt": ("Qube Research & Technologies (QRT)", "Hedge Fund / Quant"),
    "qube": ("Qube Research & Technologies (QRT)", "Hedge Fund / Quant"),
    "optiver": ("Optiver", "Market Maker / Prop"),
    "imc": ("IMC Trading", "Market Maker / Prop"),
    "flow traders": ("Flow Traders", "Market Maker / Prop"),
    "jane street": ("Jane Street", "Market Maker / Prop"),
    "citadel": ("Citadel Securities", "Market Maker / Prop"),
}

CITY_PATTERNS = {
    "Paris": [r"\bparis\b", r"\bla d[ée]fense\b", r"\bcourbevoie\b", r"\bputeaux\b", r"\bmontrouge\b", r"\bfrance\b", r"\b[îi]le-de-france\b"],
    "Londres": [r"\blondon\b", r"\blondres\b", r"\bcanary wharf\b", r"\bunited kingdom\b", r"\buk\b", r"\beurope\b"],
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
    "2026", "2027", "assistant trader", "junior trader", "junior quant"
]

FRONT_OFFICE_KEYWORDS = [
    "trading", "trader", "structur", "quant", "quantitative", "market",
    "commodit", "energy", "oil", "gas", "power", "equity", "derivatives",
    "delta one", "fixed income", "rates", "fx", "credit", "sales",
    "data scien", "machine learning", "ai ", "analytics", "strats", "risk",
    "portfolio", "execution", "algo", "broker", "research", "pricing",
    "front office", "salle de march", "produits structur", "matières premières",
    "énergie", "energie", "dérivés", "derives", "taux", "change", "actions"
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

def is_relevant_internship(title: str, require_intern_word: bool = True, require_fo_keyword: bool = False) -> bool:
    t = (title or "").lower()
    if require_intern_word and not any(k in t for k in INTERN_KEYWORDS):
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

def match_known_actor(org_name: str, fallback_company=None, fallback_cat="Banque"):
    low = (org_name or "").lower()
    for key, (clean_name, cat) in FRENCH_BANKS_AND_ENERGY.items():
        if key in low:
            return clean_name, cat
    if fallback_company:
        return fallback_company, fallback_cat
    return (org_name.strip() if org_name else None), fallback_cat

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

            # Diagnostic sample for Jane Street if needed
            if token == "janestreet" and jobs:
                sample = [(j.get("title"), (j.get("location") or {}).get("name")) for j in jobs[:5]]
                print(f"[DEBUG-JS] Sample 5: {sample}")

            for j in jobs:
                title = j.get("title", "")
                loc_name = (j.get("location") or {}).get("name", "")
                city = detect_city(loc_name, title)
                if not city or not is_relevant_internship(title, require_intern_word=True, require_fo_keyword=False):
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
            time.sleep(0.2)
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
                continue
            jobs = resp.json()
            count = 0
            for j in jobs:
                title = j.get("text", "")
                cats = j.get("categories") or {}
                loc_str = cats.get("location", "")
                city = detect_city(loc_str, title)
                if not city or not is_relevant_internship(title, require_intern_word=True, require_fo_keyword=False):
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
                continue
            jobs = resp.json().get("content", [])
            count = 0
            for j in jobs:
                title = j.get("name", "")
                loc = j.get("location") or {}
                loc_str = f"{loc.get('city', '')} {loc.get('country', '')}"
                city = detect_city(loc_str, title)
                if not city or not is_relevant_internship(title, require_intern_word=True, require_fo_keyword=True):
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
        except Exception as e:
            print(f"[SR-ERR] {board['company']}: {e}")
    return collected

def fetch_wttj_french_markets():
    """Queries Welcome to the Jungle public Algolia index for French banks & energy desks."""
    collected = []
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
            "hitsPerPage": 30,
            "facetFilters": json.dumps([["contract_type:internship", "contract_type:vie"]])
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
            print(f"[WTTJ-SKIP] HTTP {resp.status_code} - {resp.text[:150]}")
            return collected

        results = resp.json().get("results", [])
        total_raw_hits = sum(len(r.get("hits", [])) for r in results)
        print(f"[WTTJ-RAW] {total_raw_hits} hits bruts reçus sur {len(results)} requêtes")
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

                # Algolia already restricted contract_type to internship/vie, so require_intern_word=False
                if not is_relevant_internship(title, require_intern_word=False, require_fo_keyword=True):
                    continue

                matched_company, matched_cat = match_known_actor(
                    org_name,
                    fallback_company=q_meta["default_company"] or org_name,
                    fallback_cat=q_meta["category"]
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

        print(f"[WTTJ-OK] {len(collected)} stage(s) Front Office / Banques FR & Énergie retenu(s)")
    except Exception as e:
        print(f"[WTTJ-ERR] {e}")

    return collected

def fetch_efinancialcareers_jobs():
    """Queries eFinancialCareers public search API for SG, BNPP, CACIB, TotalEnergies, Vitol, Marex."""
    collected = []
    efc_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    seen_ids = set()

    for q_item in EFC_QUERIES:
        params = {
            "q": q_item["q"],
            "location": q_item["location"],
            "page": 1,
            "pageSize": 25
        }
        url = "https://www.efinancialcareers.com/api/job-search/v2/jobs"
        try:
            resp = requests.get(url, params=params, headers=efc_headers, timeout=15)
            if resp.status_code != 200:
                print(f"[EFC-SKIP] ({q_item['q']}): HTTP {resp.status_code}")
                break
            data = resp.json()
            jobs = data.get("data") or data.get("jobs") or []
            for j in jobs:
                jid = str(j.get("id") or j.get("jobId") or "")
                if not jid or jid in seen_ids:
                    continue
                seen_ids.add(jid)

                title = (j.get("title") or "").strip()
                comp_raw = (j.get("companyName") or j.get("company", {}).get("name") or "").strip()
                if not is_relevant_internship(title, require_intern_word=True, require_fo_keyword=True):
                    continue

                matched_company, matched_cat = match_known_actor(
                    comp_raw,
                    fallback_company=q_item["company"] or comp_raw,
                    fallback_cat=q_item["category"]
                )
                if not matched_company:
                    continue

                job_url = j.get("jobDetailUrl") or j.get("url") or f"https://www.efinancialcareers.com/jobs-{jid}"
                if job_url.startswith("/"):
                    job_url = f"https://www.efinancialcareers.com{job_url}"

                pub_date = (j.get("postedDate") or j.get("createdDate") or "")[:10]
                if len(pub_date) < 10:
                    pub_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                collected.append({
                    "id": f"efc-{jid}",
                    "company": matched_company,
                    "category": matched_cat,
                    "title": title,
                    "role": classify_role(title),
                    "city": q_item["city"],
                    "duration": classify_duration(title),
                    "posted_date": pub_date,
                    "status": "Ouvert",
                    "url": job_url
                })
            time.sleep(0.4)
        except Exception as e:
            print(f"[EFC-ERR] {e}")
            break

    print(f"[EFC-OK] {len(collected)} stage(s) trouvé(s) via eFinancialCareers")
    return collected

def fetch_arbeitnow_eu(headers):
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
            if not city or not is_relevant_internship(title, require_intern_word=True, require_fo_keyword=True):
                continue
            matched_comp, matched_cat = match_known_actor(comp, fallback_company=comp, fallback_cat="Banque")
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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EuroQuantMarketsTracker/1.4"}
    existing = load_existing_jobs()
    manual_jobs = [
        j for j in existing
        if not str(j.get("id", "")).startswith(("gh-", "lv-", "sr-", "wd-", "rss-", "wttj-", "abn-", "efc-"))
    ]

    scraped_jobs = []
    scraped_jobs.extend(fetch_greenhouse_jobs(headers))
    scraped_jobs.extend(fetch_lever_jobs(headers))
    scraped_jobs.extend(fetch_smartrecruiters_jobs(headers))
    scraped_jobs.extend(fetch_wttj_french_markets())
    scraped_jobs.extend(fetch_efinancialcareers_jobs())
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
