# solar_detective.py (v0.4.2)
"""
Solar Detective – Agentic crawler & dashboard  
Updated 2025‑05‑02 – adds optional `auto` parameter to `ingest()` and fixes
the CLI traceback.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import folium
import gradio as gr
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup
from folium.plugins import MarkerCluster
from sqlmodel import Field, Session, SQLModel, create_engine, select

from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool
from langchain_community.chat_models import ChatOpenAI
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper as DDS

################################################################################
# Database model
################################################################################

class SolarProject(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    capacity_mw: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    state: Optional[str] = None
    developer: Optional[str] = None
    year: Optional[int] = None
    project_type: Optional[str] = None
    cell_tech: Optional[str] = None
    bifacial: Optional[bool] = None
    grid_conn: Optional[str] = None
    manufacturers: Optional[str] = None
    offtake: Optional[str] = None
    financing: Optional[str] = None
    dispatch_url: Optional[str] = None
    raw_source: Optional[str] = None


DB_PATH = "solar_projects.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}")
SQLModel.metadata.create_all(ENGINE)

################################################################################
USER_AGENT = {"User-Agent": "solar-detective-bot"}


def fetch(url: str, binary: bool = False):
    logging.info(f"GET {url}")
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
# Simple geocode cache
################################################################################

GEOCACHE: Dict[str, Tuple[float, float]] = {}


def geocode(place: str):
    if place in GEOCACHE:
        return GEOCACHE[place]
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=dict(q=place, format="json", limit=1),
            headers=USER_AGENT,
            timeout=10,
        )
        js = r.json()
        if js:
            lat, lon = float(js[0]["lat"]), float(js[0]["lon"])
            GEOCACHE[place] = (lat, lon)
            return lat, lon
    except Exception as e:
        logging.warning(f"geocode fail {place}: {e}")
    return None, None

################################################################################
# Extractors
################################################################################

MNRE_URL = "https://mnre.gov.in/en/development-of-solar-parks-and-ultra-mega-solar-power-projects/"
SECI_URL = "https://www.seci.co.in/Bidder/view/tender/results/all-award/list/bidder"
POSOCO_CSV = "https://posoco.in/wp-content/plugins/re-dashboard/data/solar_list.csv"
NSEFI_MEMBERS = "https://www.nsefi.in/members"

search = DDS()


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
        items.append(
            SolarProject(
                name=name,
                capacity_mw=cap,
                latitude=lat,
                longitude=lon,
                developer="Various",
                project_type="Utility",
                raw_source=MNRE_URL,
            )
        )
    logging.info(f"MNRE {len(items)} rows")
    return items


def extract_seci():
    soup = BeautifulSoup(fetch(SECI_URL), "html.parser")
    items = []
    for row in soup.select("table tr"):
        t = [td.get_text(" ", strip=True) for td in row.find_all("td")]
        if len(t) < 5:
            continue
        cap = parse_capacity(" ".join(t))
        if not cap:
            continue
        items.append(
            SolarProject(
                name=t[1],
                developer=t[2],
                capacity_mw=cap,
                project_type="Utility",
                raw_source=SECI_URL,
            )
        )
    logging.info(f"SECI {len(items)} rows")
    return items


def extract_posoco():
    try:
        csv = fetch(POSOCO_CSV)
        df = pd.read_csv(pd.compat.StringIO(csv))
    except Exception as e:
        logging.warning(f"POSOCO fail {e}")
        return []
    items = []
    for _, r in df.iterrows():
        cap = parse_capacity(str(r.get("Capacity (MW)", "")))
        lat, lon = geocode(f"{r['Plant']} {r['State']}, India")
        items.append(
            SolarProject(
                name=r["Plant"],
                state=r["State"],
                capacity_mw=cap,
                latitude=lat,
                longitude=lon,
                developer=r.get("Owner"),
                raw_source=POSOCO_CSV,
            )
        )
    logging.info(f"POSOCO {len(items)} rows")
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
        items.append(
            SolarProject(
                name=name,
                developer=name,
                capacity_mw=cap,
                latitude=lat,
                longitude=lon,
                raw_source=NSEFI_MEMBERS,
            )
        )
    logging.info(f"NSEFI {len(items)} rows")
    return items


PDF_PATTERNS = {
    "Adani": r"https://www\.adanigreenenergy\.com/[^\s]+\.pdf",
    "ReNew": r"https://www\.renew\.com/[^\s]+\.pdf",
    "Tata": r"https://www\.tatapower\.com/[^\s]+\.pdf",
    "Azure": r"https://investors\.azurepower\.com/[^\s]+\.pdf",
}


def discover_pdfs():
    urls = []
    for key, p in PDF_PATTERNS.items():
        res = search.run(f"{key} investor presentation solar MW filetype:pdf")
        urls += re.findall(p, res)
    return list(dict.fromkeys(urls))  # dedupe while preserving order


def extract_pdf(url: str):
    rows = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(fetch(url, binary=True))
        path = tmp.name
    with pdfplumber.open(path) as pdf:
        txt = "\n".join(p.extract_text() or "" for p in pdf.pages)
    os.unlink(path)
    for m in re.finditer(r"([A-Za-z \-]+?)\s+(\d+[,.]?\d*)\s*MW", txt):
        n, v = m.groups()
        cap = parse_capacity(v + " MW")
        rows.append(
            SolarProject(
                name=n.strip(),
                capacity_mw=cap,
                developer=url.split("/")[2],
                raw_source=url,
            )
        )
    return rows


def discover_datasets():
    html = search.run("India solar project locations filetype:csv site:github.com")
    return re.findall(r'https://raw\.githubusercontent\.com/[^"\s]+\.csv', html)


def extract_dataset(url: str):
    try:
        df = pd.read_csv(url)
    except Exception:
        return []
    cols = [c.lower() for c in df.columns]
    if not {"name", "capacity", "lat", "lon"}.issubset(cols):
        return []
    items = []
    for _, r in df.iterrows():
        items.append(
            SolarProject(
                name=str(r["name"]),
                capacity_mw=float(r["capacity"]),
                latitude=float(r["lat"]),
                longitude=float(r["lon"]),
                raw_source=url,
            )
        )
    return items


EXTRACTORS = {
    "mnre": extract_mnre,
    "seci": extract_seci,
    "posoco": extract_posoco,
    "nsefi": extract_nsefi,
}

################################################################################
# Ingestion
################################################################################


def ingest(sources: List[str], auto: bool = False) -> None:
    """
    Ingest data for the given extractor keys.
    If *auto* is True, the function also runs the slow PDF and GitHub discovery
    pipelines.
    """
    with Session(ENGINE) as sess:
        new = 0

        # built‑in extractors
        for s in sources:
            for p in EXTRACTORS[s]():
                if not sess.exec(select(SolarProject).where(SolarProject.name == p.name)).first():
                    sess.add(p)
                    new += 1

        # optional web‑discovery
        if auto:
            for url in discover_pdfs():
                for p in extract_pdf(url):
                    if not sess.exec(select(SolarProject).where(SolarProject.name == p.name)).first():
                        sess.add(p)
                        new += 1

            for csv in discover_datasets():
                for p in extract_dataset(csv):
                    if not sess.exec(select(SolarProject).where(SolarProject.name == p.name)).first():
                        sess.add(p)
                        new += 1

        sess.commit()
        logging.info(f"ingested {new} new rows")

################################################################################
# Dashboard
################################################################################


def popup(r):
    return f"<b>{r['name']}</b><br>{r.get('capacity_mw','?')} MW"


def build_map(df):
    m = folium.Map(location=[22.6, 78.9], zoom_start=5)
    cl = MarkerCluster().add_to(m)
    for _, r in df.iterrows():
        lat = r.get("latitude") or 0
        lon = r.get("longitude") or 0
        folium.Marker([lat, lon], popup=popup(r)).add_to(cl)
    return m._repr_html_()


def dashboard():
    with Session(ENGINE) as s:
        df = pd.DataFrame([p.dict() for p in s.exec(select(SolarProject)).all()])

    if df.empty:
        print("No data – run ingest first")
        return

    def filt(cap):
        d = df[df["capacity_mw"] >= cap]
        return build_map(d), d

    with gr.Blocks() as app:
        gr.Markdown("# Solar Detective Map")
        cap = gr.Slider(0, 2000, 0, label="Min MW")
        html = gr.HTML()
        tbl = gr.Dataframe()
        cap.change(filt, cap, [html, tbl])
        html.value, tbl.value = filt(0)
    app.launch()

################################################################################
# CLI
################################################################################

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    ap = argparse.ArgumentParser("solar_detective")
    sub = ap.add_subparsers(dest="cmd")

    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("--auto", action="store_true", help="Also run PDF and GitHub discovery")
    p_ing.add_argument(
        "-s",
        "--source",
        action="append",
        choices=list(EXTRACTORS) + ["all"],
        default=["all"],
        help="Extractors to run (default: all)",
    )

    sub.add_parser("dashboard")

    ns = ap.parse_args()

    if ns.cmd == "ingest":
        srcs = list(EXTRACTORS) if "all" in ns.source else ns.source
        ingest(srcs, auto=ns.auto)
    elif ns.cmd == "dashboard":
        dashboard()
    else:
        ap.print_help()