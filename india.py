'''
Solar Detective: Mapping India's Solar Infrastructure Using Agentic AI

Role: P = Programming and code guru
Verbosity Level: V = 2

Context:
- Unified dashboard using Folium for project mapping and ROI drawing.
- Refactored bounding-box display into `display_bbox` function.
'''

import streamlit as st
import pandas as pd
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode

# ========== Page Configuration ==========
st.set_page_config(page_title="Solar Detective", layout="wide")

# ========== Data Placeholder ==========
@st.cache_data
def build_dataset():
    data = [
        {'project_name': 'Example Solar Farm', 'capacity_mw': 100, 'lat': 26.8467, 'lon': 80.9462,
         'developer': 'Sample Developer', 'commissioning_year': 2022, 'type': 'Utility-scale'},
        {'project_name': 'Example Solar Farm2', 'capacity_mw': 1, 'lat': 26.9, 'lon': 81.0,
         'developer': 'Sample Developer', 'commissioning_year': 2022, 'type': 'Utility-scale'}
    ]
    return pd.DataFrame(data)

# ========== Helper Function ==========
def display_bbox(min_lat, max_lat, min_lon, max_lon):
    """Display bounding-box coordinates and placeholder GIS info."""
    st.write("**ROI Bounding Box Coordinates:**")
    st.write(f"Latitude: {min_lat:.4f} to {max_lat:.4f}")
    st.write(f"Longitude: {min_lon:.4f} to {max_lon:.4f}")
    st.info("Satellite imagery integration placeholder: feed these coords to your GIS API.")

# ========== Main ==========
def main():
    st.title("🌞 Solar Detective: India's Solar Infrastructure")

    # Load & filter dataset
    df = build_dataset()
    st.sidebar.header("Filters")
    years = sorted(df['commissioning_year'].unique())
    types = sorted(df['type'].unique())
    devs = sorted(df['developer'].unique())

    sel_y = st.sidebar.multiselect("Year", years, default=[])
    sel_t = st.sidebar.multiselect("Type", types, default=[])
    sel_d = st.sidebar.multiselect("Developer", devs, default=[])
    sel_y = sel_y or years
    sel_t = sel_t or types
    sel_d = sel_d or devs
    cap_min, cap_max = float(df['capacity_mw'].min()), float(df['capacity_mw'].max())
    sel_c = st.sidebar.slider("Capacity (MW)", cap_min, cap_max, (cap_min, cap_max))

    filtered = df[
        df['commissioning_year'].isin(sel_y) &
        df['type'].isin(sel_t) &
        df['developer'].isin(sel_d) &
        df['capacity_mw'].between(sel_c[0], sel_c[1])
    ]

    # Project Data Table & Selection
    st.subheader("Project Data")
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    grid_opts = gb.build()
    grid_resp = AgGrid(
        filtered,
        gridOptions=grid_opts,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        height=200,
        theme='streamlit'
    )
    selected = grid_resp.get('selected_rows', [])

    # Determine initial map center & zoom
    if isinstance(selected, list) and len(selected) > 0:
        center = [selected[0]['lat'], selected[0]['lon']]
        zoom = 8
    elif not filtered.empty:
        center = [filtered['lat'].mean(), filtered['lon'].mean()]
        zoom = 5
    else:
        center = [20, 80]
        zoom = 5

    # Build Folium Map
    m = folium.Map(location=center, zoom_start=zoom)

    # Add project markers
    for _, row in filtered.iterrows():
        folium.CircleMarker(
            location=(row['lat'], row['lon']),
            radius=10,
            color='orange', fill=True, fill_opacity=0.7,
            popup=f"{row['project_name']} ({row['capacity_mw']} MW)"
        ).add_to(m)

    # Add Draw plugin for ROI
    draw = Draw(
        draw_options={'rectangle': True, 'polygon': False, 'polyline': False, 'circle': False, 'marker': False},
        edit_options={'edit': True}
    )
    draw.add_to(m)

    # Render map & capture drawing events
    st.subheader("Interactive Map & ROI Selection")
    map_data = st_folium(m, height=500, width=800)
    drawings = map_data.get('all_drawings', [])

    # If ROI drawn, extract & display via helper
    if drawings:
        last = drawings[-1]
        coords = last['geometry']['coordinates'][0]
        lons = [pt[0] for pt in coords]
        lats = [pt[1] for pt in coords]
        display_bbox(min(lats), max(lats), min(lons), max(lons))

    # Data export
    st.download_button(
        label="Export filtered data as CSV",
        data=filtered.to_csv(index=False).encode('utf-8'),
        file_name='solar_projects_filtered.csv',
        mime='text/csv'
    )

if __name__ == '__main__':
    main()
