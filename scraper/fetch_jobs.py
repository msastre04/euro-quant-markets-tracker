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

# 4. Welcome to the Jungle (WTTJ) broad French & English Front Office queries
# Short queries yield high recall across SG, BNPP, CACIB, Natixis, ODDO, TotalEnergies, Engie, etc.
WTTJ_QUERIES = [
    {"query": "finance de marché", "default_cat": "Banque"},
    {"query": "salle de marchés", "default_cat": "Banque"},
    {"query": "trading", "default_cat": "Banque"},
    {"query": "structuration", "default_cat": "Banque"},
    {"query": "quant", "default_cat": "Hedge Fund / Quant"},
    {"query": "quantitatif", "default_cat": "Banque"},
    {"query": "dérivés", "default_cat": "Banque"},
    {"query": "derivatives", "default_cat": "Banque"},
    {"query": "commodities", "default_cat": "Commodities & Energy"},
    {"query": "matières premières", "default_cat": "Commodities & Energy"},
    {"query": "énergie trading", "default_cat": "Commodities & Energy"},
    {"query": "risques de marché", "default_cat": "Banque"},
    {"query": "market risk", "default_cat": "Banque"},
    {"query": "fixed income", "default_cat": "Banque"},
    {"query": "delta one", "default_cat": "Banque"},
    {"query": "sales trading", "default_cat": "Banque"},
    {"query": "gestion quantitative", "default_cat": "Hedge Fund / Quant"},
    {"query": "data science finance", "default_cat": "Banque"},
]

KNOWN_ACTORS = {
    "societe generale": ("Société Générale (SG CIB)", "Banque"),
    "société générale": ("Société Générale (SG CIB)", "Banque"),
    "sg cib": ("Société Générale (SG CIB)", "Banque"),
    "bnp paribas": ("BNP Paribas (CIB)", "Banque"),
    "credit agricole": ("Crédit Agricole CIB", "Banque"),
    "crédit agricole": ("Crédit Agricole CIB", "Banque"),
    "cacib": ("Crédit Agricole CIB", "Banque"),
    "natixis": ("Natixis CIB (Groupe BPCE)", "Banque"),
    "bpce": ("Natixis CIB (Groupe BPCE)", "Banque"),
    "oddo": ("ODDO BHF", "Banque"),
    "cic": ("CIC Market Solutions", "Banque"),
    "crédit mutuel": ("CIC Market Solutions", "Banque"),
    "credit mutuel": ("CIC Market Solutions", "Banque"),
    "lcl": ("LCL (Banque des Entreprises / Marchés)", "Banque"),
    "totalenergies": ("TotalEnergies (Trading & Shipping)", "Commodities & Energy"),
    "total energies": ("TotalEnergies (Trading & Shipping)", "Commodities & Energy"),
    "engie": ("ENGIE Global Markets", "Commodities & Energy"),
    "edf trading": ("EDF Trading", "Commodities & Energy"),
    "edf": ("EDF Trading", "Commodities & Energy"),
    "marex": ("Marex (Marex Solutions)", "Courtier / Broker"),
    "vitol": ("Vitol", "Commodities & Energy"),
    "trafigura": ("Trafigura", "Commodities & Energy"),
    "gunvor": ("Gunvor Group", "Commodities & Energy"),
    "mercuria": ("Mercuria", "Commodities & Energy"),
    "kepler": ("Kepler Cheuvreux", "Courtier / Broker"),
    "cfm": ("Capital Fund Management (CFM)", "Hedge Fund / Quant"),
    "capital fund management": ("Capital Fund Management (CFM)", "Hedge Fund / Quant"),
    "amundi": ("Amundi", "Hedge Fund / Quant"),
    "axa im": ("AXA IM", "Hedge Fund / Quant"),
    "axa investment": ("AXA IM", "Hedge Fund / Quant"),
    "qrt": ("Qube Research & Technologies (QRT)", "Hedge Fund / Quant"),
    "qube": ("Qube Research & Technologies (QRT)", "Hedge Fund / Quant"),
    "optiver": ("Optiver", "Market Maker / Prop"),
    "imc": ("IMC Trading", "Market Maker / Prop"),
    "flow traders": ("Flow Traders", "Market Maker / Prop"),
    "jane street": ("Jane Street", "Market Maker / Prop"),
    "citadel": ("Citadel Securities", "Market Maker / Prop"),
    "millennium": ("Millennium Management", "Hedge Fund / Quant"),
    "squarepoint": ("Squarepoint Capital", "Hedge Fund / Quant"),
    "exoduspoint": ("ExodusPoint", "Hedge Fund / Quant"),
    "ubs": ("UBS", "Banque"),
    "hsbc": ("HSBC", "Banque"),
    "barclays": ("Barclays", "Banque"),
    "deutsche bank": ("Deutsche Bank", "Banque"),
    "goldman sachs": ("Goldman Sachs", "Banque US"),
    "j.p. morgan": ("J.P. Morgan", "Banque US"),
    "jpmorgan": ("J.P. Morgan", "Banque US"),
    "morgan stanley": ("Morgan Stanley", "Banque US"),
    "bank of america": ("Bank of America", "Banque US"),
    "citigroup": ("Citigroup", "Banque US"),
    "citi": ("Citigroup", "Banque US"),
    "rothschild": ("Rothschild & Co", "Banque"),
    "lazard": ("Lazard", "Banque"),
    "euronext": ("Euronext", "Courtier / Broker"),
    "tradition": ("Compagnie Financière Tradition", "Courtier / Broker"),
    "tp icap": ("TP ICAP", "Courtier / Broker"),
}

CITY_PATTERNS = {
    "Paris": [r"\bparis\b", r"\bla d[ée]fense\b", r"\bcourbevoie\b", r"\bputeaux\b", r"\bmontrouge\b", r"\bfrance\b", r"\b[îi]le-de-france\b", r"\bissy-les-moulineaux\b", r"\bneuilly\b", r"\blevallois\b"],
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
    "énergie", "energie", "dérivés", "derives", "taux", "change", "actions",
    "finance de march", "trésorerie", "tresorerie", "gestion d'actifs", "asset management",
    "hedge fund", "arbitrage", "volatilit", "options", "futures", "swaps"
]

EXCLUDE_KEYWORDS = [
    "hr ", "human resources", "recruiter", "talent acquisition", "legal",
    "marketing", "facilities", "receptionist", "office manager", "accounting",
    "payroll", "events", "executive assistant", "pa to", "audit", "compliance",
    "communication", "rh ", "ressources humaines", "juridique", "comptab",
    "contrôle de gestion", "controle de gestion", "inspecteur", "alternance"
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
    if any(k in t for k in ["quant", "research", "strats", "pricing", "stochastic", "alpha", "quantitatif"]):
        return "Quant Research / Dev"
    if any(k in t for k in ["data scien", "machine learning", "ai ", "analytics", "data engineer", "software", "developer", "engineer"]):
        return "Data Science & Analytics"
    return "Trading & Market Making"

def classify_duration(title: str) -> str:
    t = (title or "").lower()
    if "summer" in t or "spring" in t or "insight" in t:
        return "Summer (2-3 mois)"
    return "Off-cycle / 6 mois"

def match_known_actor(org_name: str, fallback_cat="Banque"):
    low = (org_name or "").lower()
    for key, (clean_name, cat) in KNOWN_ACTORS.items():
        if key in low:
            return clean_name, cat
    clean = (org_name or "").strip()
    return (clean if clean else None), fallback_cat

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
    """Queries Welcome to the Jungle public Algolia index with broad French/English market terms."""
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
            "hitsPerPage": 50,
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
            timeout=25
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

                if not is_relevant_internship(title, require_intern_word=False, require_fo_keyword=True):
                    continue

                matched_company, matched_cat = match_known_actor(
                    org_name,
                    fallback_cat=q_meta["default_cat"]
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
            matched_comp, matched_cat = match_known_actor(comp, fallback_cat="Banque")
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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EuroQuantMarketsTracker/1.5"}
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
