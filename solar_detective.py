# solar_detective.py
"""
Solar Detective – Prototype pipeline and dashboard for the
“Mapping India’s Solar Infrastructure Using Agentic AI” challenge.

Author: ChatGPT (OpenAI o3)
Date: 2025‑05‑02 (patched)

Changelog 2025‑05‑02
--------------------
* **Fix dashboard crash** when DB rows → DataFrame – now builds via list‑of‑dicts so columns exist.
* **Graceful empty‑DB guard** prints a hint and exits early.
* **Row access** uses `row["latitude"]` to avoid attribute lookup edge‑cases.
* **LangChain v0.2 import paths** switched to `langchain_community.*` (removes warnings).
* Misc. typing + doc updates.
"""

################################################################################
# Stdlib & third‑party imports
################################################################################

import os
import re
import json
import time
import requests
import logging
from pathlib import Path
from typing import Optional, List, Tuple

import pandas as pd
from bs4 import BeautifulSoup
import pdfplumber
import folium
from folium.plugins import MarkerCluster
import gradio as gr
from sqlmodel import Field, SQLModel, Session, create_engine, select

# LangChain – community namespace (v0.2+)
from langchain_community.chat_models import ChatOpenAI
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool

################################################################################
# Database schema
################################################################################

class SolarProject(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    capacity_mw: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    developer: Optional[str] = None
    year: Optional[int] = None
    project_type: Optional[str] = None  # Utility, Rooftop, Floating, Hybrid
    cell_tech: Optional[str] = None     # e.g. c‑Si, CdTe …
    bifacial: Optional[bool] = None
    grid_conn: Optional[str] = None
    manufacturers: Optional[str] = None
    offtake: Optional[str] = None
    financing: Optional[str] = None
    dispatch_url: Optional[str] = None
    raw_source: Optional[str] = None    # URL or file reference

DB_PATH = "solar_projects.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SQLModel.metadata.create_all(ENGINE)

################################################################################
# Basic helpers
################################################################################

def fetch_html(url: str) -> str:
    logging.info(f"Fetching {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_capacity(text: str) -> Optional[float]:
    m = re.search(r"([0-9]+(?:\\.[0-9]+)?)\\s*(MW|GW)", text, re.I)
    if not m:
        return None
    val, unit = m.groups()
    return float(val) * (1000 if unit.lower() == "gw" else 1)


def geocode_location(place: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=dict(q=place, format="json", limit=1),
            headers={"User-Agent": "solar-detective-prototype"},
            timeout=10,
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        logging.warning(f"Geocoding failed for '{place}': {e}")
    return None, None

################################################################################
# Source‑specific mini‑extractors (placeholder stubs)
################################################################################

MNRE_SOLAR_PARKS_URL = (
    "https://mnre.gov.in/en/development-of-solar-parks-and-ultra-mega-solar-power-projects/"
)
SECI_TENDER_AWARD_URL = (
    "https://www.seci.co.in/Bidder/view/tender/results/all-award/list/bidder"
)


def discover_mnre_projects() -> List[SolarProject]:
    html = fetch_html(MNRE_SOLAR_PARKS_URL)
    soup = BeautifulSoup(html, "html.parser")
    projects: List[SolarProject] = []
    for row in soup.select("table tr"):
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 3 or not re.search(r"MW|GW", " ".join(cells)):
            continue
        name = cells[0]
        capacity = parse_capacity(" ".join(cells))
        loc_text = cells[1]
        lat, lon = geocode_location(loc_text + ", India")
        projects.append(
            SolarProject(
                name=name,
                capacity_mw=capacity,
                latitude=lat,
                longitude=lon,
                developer="N/A",
                year=None,
                project_type="Utility",
                raw_source=MNRE_SOLAR_PARKS_URL,
            )
        )
    return projects


def discover_seci_awards() -> List[SolarProject]:
    html = fetch_html(SECI_TENDER_AWARD_URL)
    soup = BeautifulSoup(html, "html.parser")
    projects: List[SolarProject] = []
    for row in soup.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        if len(cells) < 5:
            continue
        name = cells[1]
        capacity = parse_capacity(cells[4])
        projects.append(
            SolarProject(
                name=name,
                capacity_mw=capacity,
                latitude=None,
                longitude=None,
                developer=cells[2],
                year=None,
                project_type="Utility",
                raw_source=SECI_TENDER_AWARD_URL,
            )
        )
    return projects

SOURCE_FUNCS = {
    "mnre": discover_mnre_projects,
    "seci": discover_seci_awards,
}

################################################################################
# LangChain autonomous agent (optional)
################################################################################

def build_agent():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))
    search = DuckDuckGoSearchAPIWrapper()
    tools = [
        Tool(name="duckduckgo", func=lambda q: search.run(q), description="Search the internet"),
        Tool(name="fetch_html", func=fetch_html, description="GET raw HTML"),
    ]
    return initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

################################################################################
# Ingestion pipeline
################################################################################

def ingest(sources: List[str]):
    with Session(ENGINE) as sess:
        for src in sources:
            extractor = SOURCE_FUNCS.get(src)
            if not extractor:
                logging.warning(f"Unknown source '{src}', skipping.")
                continue
            for project in extractor():
                exists = sess.exec(select(SolarProject).where(SolarProject.name == project.name)).first()
                if not exists:
                    sess.add(project)
        sess.commit()

################################################################################
# Dashboard helpers
################################################################################

def make_popup_html(row) -> str:
    lines = [
        f"<b>Name:</b> {row['name']}",
        f"<b>Capacity:</b> {row['capacity_mw']} MW" if pd.notna(row['capacity_mw']) else "",
        f"<b>Developer:</b> {row['developer']}" if row.get('developer') else "",
        f"<b>Year:</b> {row['year']}" if pd.notna(row['year']) else "",
        f"<b>Type:</b> {row['project_type']}" if row.get('project_type') else "",
        f"<small>Source: {row['raw_source']}</small>",
    ]
    return "<br>".join([l for l in lines if l])


def build_map(df: pd.DataFrame) -> str:
    m = folium.Map(location=[22.5937, 78.9629], zoom_start=5)
    cluster = MarkerCluster().add_to(m)
    for _, r in df.dropna(subset=["latitude", "longitude"]).iterrows():
        folium.Marker(
            location=[r["latitude"], r["longitude"]],
            popup=folium.Popup(make_popup_html(r), max_width=250),
        ).add_to(cluster)
    return m._repr_html_()

################################################################################
# Dashboard entry point
################################################################################

def launch_dashboard():
    with Session(ENGINE) as sess:
        rows = sess.exec(select(SolarProject)).all()
        df = pd.DataFrame([p.dict() for p in rows])

    if df.empty:
        print("⚠️  Database is empty – run `python solar_detective.py ingest` first.")
        return

    def update(capacity, year, ptype):
        filtered = df.copy()
        if capacity:
            filtered = filtered[filtered["capacity_mw"] >= capacity]
        if year:
            if "year" in filtered.columns:
                filtered = filtered[filtered["year"].fillna(0).astype(int) >= year]
        if ptype != "Any":
            filtered = filtered[filtered["project_type"] == ptype]
        return build_map(filtered), filtered

    with gr.Blocks() as demo:
        gr.Markdown("# 🕵️‍♂️ Solar Detective – India Solar Project Map")
        with gr.Row():
            capacity = gr.Slider(minimum=0, maximum=2000, value=0, label="Min Capacity (MW)")
            year = gr.Slider(minimum=2000, maximum=2025, value=2000, label="From Year")
            ptype = gr.Dropdown(choices=["Any", "Utility", "Rooftop", "Floating", "Hybrid"], value="Any", label="Project Type")
        map_html = gr.HTML()
        table = gr.Dataframe(interactive=False)

        for ctl in (capacity, year, ptype):
            ctl.change(update, [capacity, year, ptype], [map_html, table])

        # initial render
        map_html.value, table.value = update(0, 2000, "Any")
    demo.launch()

################################################################################
# CLI driver
################################################################################

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")

    parser = argparse.ArgumentParser(description="Solar Detective prototype")
    sub = parser.add_subparsers(dest="cmd")

    p_ing = sub.add_parser("ingest", help="Ingest data from sources")
    p_ing.add_argument("--source", "-s", action="append", default=["mnre", "seci"], help="Source key(s)")

    sub.add_parser("dashboard", help="Launch Gradio dashboard")

    args = parser.parse_args()

    if args.cmd == "ingest":
        ingest(args.source)
    elif args.cmd == "dashboard":
        launch_dashboard()
    else:
        parser.print_help()
