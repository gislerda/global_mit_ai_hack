# solar_detective.py (v0.4.6)
"""
Solar Detective – agentic crawler & dashboard

2025‑05‑02
* v0.4.2  add  --auto
* v0.4.3  live DB schema patch
* v0.4.4  DuckDuckGo rate‑limit guard
* v0.4.5  fix ensure_schema() for SQLModel 0.0.16
* v0.4.6  **better SECI scraper + optional GPT parsing of tender titles**
"""

from __future__ import annotations
import concurrent.futures, json, logging, os, re, tempfile, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import folium, gradio as gr, pandas as pd, pdfplumber, requests
from bs4 import BeautifulSoup
from folium.plugins import MarkerCluster
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import inspect, text

from langchain_community.utilities import DuckDuckGoSearchAPIWrapper as DDS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from langchain_community.chat_models import ChatOpenAI   # ← for GPT enrichment

################################################################################
# DB model
################################################################################

class SolarProject(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str                                   # Tender ID or plant name
    capacity_mw: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    state: Optional[str] = None
    developer: Optional[str] = None             # winning bidder / owner
    year: Optional[int] = None
    project_type: Optional[str] = None
    cell_tech: Optional[str] = None             # Solar PV, Wind, Hybrid …
    bifacial: Optional[bool] = None
    grid_conn: Optional[str] = None
    manufacturers: Optional[str] = None
    offtake: Optional[str] = None
    financing: Optional[str] = None
    dispatch_url: Optional[str] = None
    raw_source: Optional[str] = None            # URL the row came from


DB_PATH = "solar_projects.db"
ENGINE  = create_engine(f"sqlite:///{DB_PATH}")

# ---------------------------------------------------------------------------
# lightweight SQLite schema migration
# ---------------------------------------------------------------------------
def _sqlite_type(col: str) -> str:
    floats = {"capacity_mw", "latitude", "longitude"}
    ints   = {"year", "bifacial"}
    return "REAL" if col in floats else "INTEGER" if col in ints else "TEXT"

def ensure_schema():
    insp = inspect(ENGINE)
    if "solarproject" not in insp.get_table_names():
        SQLModel.metadata.create_all(ENGINE)
        return

    existing = {c["name"] for c in insp.get_columns("solarproject")}
    missing  = [c for c in SolarProject.model_fields.keys() if c not in existing]

    if missing:
        with ENGINE.begin() as conn:
            for col in missing:
                conn.execute(
                    text(f"ALTER TABLE solarproject ADD COLUMN {col} {_sqlite_type(col)}")
                )
        logging.info("DB patched – added columns: %s", ", ".join(missing))

ensure_schema()
################################################################################
USER_AGENT = {"User-Agent": "solar-detective-bot"}

def fetch(url: str, binary: bool = False):
    logging.info("GET %s", url)
    r = requests.get(url, headers=USER_AGENT, timeout=30)
    r.raise_for_status()
    return r.content if binary else r.text

def parse_capacity(text: str) -> Optional[float]:
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*(MW|GW)", text, re.I)
    if not m:
        return None
    val, unit = m.groups()
    return float(val.replace(",", ".")) * (1000 if unit.lower() == "gw" else 1)

################################################################################
# geocode cache
################################################################################
GEOCACHE: Dict[str, Tuple[float, float]] = {}
def geocode(place: str):
    if place in GEOCACHE:
        return GEOCACHE[place]
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params=dict(q=place, format="json", limit=1),
                         headers=USER_AGENT, timeout=10)
        js = r.json()
        if js:
            lat, lon = float(js[0]["lat"]), float(js[0]["lon"])
            GEOCACHE[place] = (lat, lon)
            return lat, lon
    except Exception as e:
        logging.warning("geocode fail %s: %s", place, e)
    return None, None

################################################################################
# DDG helper
################################################################################
search = DDS()
def ddg_safe(query: str, retries: int = 1, delay: int = 5) -> str:
    try:
        return search.run(query)
    except DuckDuckGoSearchException as e:
        logging.warning("DDG rate‑limit – %s", e)
        if retries:
            time.sleep(delay)
            return ddg_safe(query, retries - 1, delay * 2)
        return ""

################################################################################
# ----------  SECI scraper (improved)  ----------------------------------------
################################################################################
SECI_URL = "https://www.seci.co.in/Bidder/view/tender/results/all-award/list/bidder"

GPT_ENABLED = bool(os.getenv("OPENAI_API_KEY"))

def gpt_enrich(title: str) -> dict:
    """
    Use GPT‑4o to turn an unstructured tender title into structured JSON.
    The model is only called if OPENAI_API_KEY is set.
    """
    if not GPT_ENABLED:
        return {}

    llm = ChatOpenAI(
        temperature=0,
        model_name="gpt-4o" if "gpt-4o" in ChatOpenAI.supported_models() else "gpt-4o-mini",
        max_tokens=128,
    )
    system = (
        "You are a data wrangler. Extract as much structured info as you can "
        "from the given Indian renewable tender title. "
        "Return *minified JSON* with keys: "
        '`capacity_mw` (number or null), `technology` (e.g. "Solar PV", '
        '"Wind", "Hybrid"), `storage_mwh` (number or null), '
        '`project_type` (e.g. "Utility", "Rooftop", "Manufacturing"), '
        '`location` (string or null). Use null if absent.'
    )
    user = f'Title: "{title}"'
    try:
        txt = llm.invoke([{"role": "system", "content": system},
                          {"role": "user",    "content": user}]).content
        return json.loads(txt)
    except Exception as e:
        logging.debug("GPT enrich failed – %s", e)
        return {}

def extract_seci() -> List[SolarProject]:
    """
    Scrape the SECI “View Tender Results” table.
    Improvements vs earlier version:
      * correct column mapping
      * capacity parsed from *title*
      * optional GPT pass for tech / type / location inferral
    """
    soup  = BeautifulSoup(fetch(SECI_URL), "html.parser")
    rows  = soup.select("table tr")[1:]        # skip header
    items = []

    for r in rows:
        tds = r.find_all("td")
        if len(tds) < 6:
            continue

        tender_id   = tds[1].get_text(strip=True)
        tender_ref  = tds[2].get_text(" ", strip=True)
        title       = tds[3].get_text(" ", strip=True)
        tender_type = tds[4].get_text(strip=True)

        cap = parse_capacity(title)            #  ❶ capacity from title
        extra = gpt_enrich(title)              #  ❷ optional GPT pass

        # fallbacks if GPT off / returns nothing
        tech = extra.get("technology") \
               or ("Solar PV" if "solar" in title.lower()
                   else "Wind" if "wind" in title.lower()
                   else "Hybrid" if "hybrid" in title.lower()
                   else None)

        ptype = extra.get("project_type") \
                or ("Utility" if "ISTS" in title.upper()
                    else "Manufacturing" if "Manufactur" in title
                    else tender_type.title() if tender_type else None)

        items.append(
            SolarProject(
                name=tender_id,
                developer=None,                # requires per‑tender API; left null
                capacity_mw=extra.get("capacity_mw", cap),
                project_type=ptype,
                cell_tech=tech,
                raw_source=SECI_URL,
            )
        )

    logging.info("SECI %d rows (post‑clean)", len(items))
    return items
################################################################################

# -------------------------  other extractors (unchanged)  --------------------
MNRE_URL      = "https://mnre.gov.in/en/development-of-solar-parks-and-ultra-mega-solar-power-projects/"
POSOCO_CSV    = "https://posoco.in/wp-content/plugins/re-dashboard/data/solar_list.csv"
NSEFI_MEMBERS = "https://www.nsefi.in/members"

def extract_mnre():
    soup = BeautifulSoup(fetch(MNRE_URL), "html.parser")
    items = []
    for blk in soup.select("div.accordion-item"):
        txt = blk.get_text(" ", strip=True)
        cap = parse_capacity(txt)
        if not cap:
            continue
        name = txt.split("–", 1)[0].strip()
        lat, lon = geocode(name + ", India")
        items.append(SolarProject(name=name, capacity_mw=cap, latitude=lat,
                                  longitude=lon, developer="Various",
                                  project_type="Utility", raw_source=MNRE_URL))
    logging.info("MNRE %d rows", len(items))
    return items

def extract_posoco():
    try:
        csv = fetch(POSOCO_CSV)
        df  = pd.read_csv(pd.compat.StringIO(csv))
    except Exception as e:
        logging.warning("POSOCO fail %s", e); return []
    items = []
    for _, r in df.iterrows():
        cap = parse_capacity(str(r.get("Capacity (MW)", "")))
        lat, lon = geocode(f"{r['Plant']} {r['State']}, India")
        items.append(SolarProject(name=r["Plant"], state=r["State"],
                                  capacity_mw=cap, latitude=lat, longitude=lon,
                                  developer=r.get("Owner"), raw_source=POSOCO_CSV))
    logging.info("POSOCO %d rows", len(items))
    return items

def extract_nsefi():
    soup = BeautifulSoup(fetch(NSEFI_MEMBERS), "html.parser")
    items = []
    for card in soup.select("div.member-info"):
        txt = card.get_text(" ", strip=True)
        cap = parse_capacity(txt)
        name = txt.split(" ")[0]
        if not cap:
            continue
        lat, lon = geocode(name + ", India")
        items.append(SolarProject(name=name, developer=name, capacity_mw=cap,
                                  latitude=lat, longitude=lon,
                                  raw_source=NSEFI_MEMBERS))
    logging.info("NSEFI %d rows", len(items))
    return items

PDF_PATTERNS = {
    "Adani": r"https://www\.adanigreenenergy\.com/[^\s]+\.pdf",
    "ReNew": r"https://www\.renew\.com/[^\s]+\.pdf",
    "Tata":  r"https://www\.tatapower\.com/[^\s]+\.pdf",
    "Azure": r"https://investors\.azurepower\.com/[^\s]+\.pdf",
}
def discover_pdfs() -> List[str]:
    urls = []
    for key, pat in PDF_PATTERNS.items():
        res  = ddg_safe(f"{key} investor presentation solar MW filetype:pdf")
        urls += re.findall(pat, res)
    return list(dict.fromkeys(urls))

def extract_pdf(url: str):
    rows = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(fetch(url, binary=True)); path = tmp.name
    with pdfplumber.open(path) as pdf:
        txt = "\n".join(p.extract_text() or "" for p in pdf.pages)
    os.unlink(path)
    for m in re.finditer(r"([A-Za-z \-]+?)\s+(\d+[,.]?\d*)\s*MW", txt):
        n, v = m.groups()
        cap  = parse_capacity(v + " MW")
        rows.append(SolarProject(name=n.strip(), capacity_mw=cap,
                                 developer=url.split("/")[2],
                                 raw_source=url))
    return rows

def discover_datasets() -> List[str]:
    html = ddg_safe("India solar project locations filetype:csv site:github.com")
    return re.findall(r'https://raw\.githubusercontent\.com/[^"\s]+\.csv', html)

def extract_dataset(url: str):
    try:
        df = pd.read_csv(url)
    except Exception:
        return []
    if not {"name", "capacity", "lat", "lon"}.issubset({c.lower() for c in df.columns}):
        return []
    return [SolarProject(name=str(r["name"]), capacity_mw=float(r["capacity"]),
                         latitude=float(r["lat"]), longitude=float(r["lon"]),
                         raw_source=url)
            for _, r in df.iterrows()]

EXTRACTORS = {
    "mnre":   extract_mnre,
    "seci":   extract_seci,
    "posoco": extract_posoco,
    "nsefi":  extract_nsefi,
}

################################################################################
# ingestion
################################################################################
def ingest(sources: List[str], auto: bool = False):
    with Session(ENGINE) as sess:
        new = 0
        for s in sources:
            for p in EXTRACTORS[s]():
                if not sess.exec(select(SolarProject).where(SolarProject.name == p.name)).first():
                    sess.add(p); new += 1
        if auto:
            for url in discover_pdfs():
                for p in extract_pdf(url):
                    if not sess.exec(select(SolarProject).where(SolarProject.name == p.name)).first():
                        sess.add(p); new += 1
            for csv in discover_datasets():
                for p in extract_dataset(csv):
                    if not sess.exec(select(SolarProject).where(SolarProject.name == p.name)).first():
                        sess.add(p); new += 1
        sess.commit()
        logging.info("ingested %d new rows", new)

################################################################################
# dashboard
################################################################################
def _popup(r): return f"<b>{r['name']}</b><br>{r.get('capacity_mw','?')} MW"

def build_map(df):
    m  = folium.Map(location=[22.6, 78.9], zoom_start=5)
    cl = MarkerCluster().add_to(m)
    for _, r in df.iterrows():
        lat, lon = r.get("latitude") or 0, r.get("longitude") or 0
        folium.Marker([lat, lon], popup=_popup(r)).add_to(cl)
    return m._repr_html_()

def dashboard():
    with Session(ENGINE) as s:
        df = pd.DataFrame([p.dict() for p in s.exec(select(SolarProject)).all()])
    if df.empty:
        print("No data – run ingest first"); return
    def filt(cap): d = df[df["capacity_mw"] >= cap]; return build_map(d), d
    with gr.Blocks() as app:
        gr.Markdown("# Solar Detective Map")
        cap  = gr.Slider(0, 2000, 0, label="Min MW")
        html = gr.HTML(); tbl = gr.Dataframe()
        cap.change(filt, cap, [html, tbl]); html.value, tbl.value = filt(0)
    app.launch()

################################################################################
# CLI
################################################################################
if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ap  = argparse.ArgumentParser("solar_detective"); sub = ap.add_subparsers(dest="cmd")
    p_i = sub.add_parser("ingest")
    p_i.add_argument("--auto", action="store_true",
                     help="also run PDF & GitHub discovery (uses DuckDuckGo)")
    p_i.add_argument("-s", "--source", action="append",
                     choices=list(EXTRACTORS) + ["all"],
                     default=["all"], help="extractors to run")
    sub.add_parser("dashboard")
    ns = ap.parse_args()

    if ns.cmd == "ingest":
        srcs = list(EXTRACTORS) if "all" in ns.source else ns.source
        ingest(srcs, auto=ns.auto)
    elif ns.cmd == "dashboard":
        dashboard()
    else:
        ap.print_help()