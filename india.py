'''
Solar Detective: Mapping India's Solar Infrastructure Using Agentic AI

Role: P = Programming and code guru
Verbosity Level: V = 2

Context and Assumptions:
- This Streamlit app is a scaffold demonstrating the overall structure and UI/UX flow.
- Core data ingestion (web scraping, PDF parsing, satellite imagery) is represented by placeholder functions to be implemented.
- A sample DataFrame loader provides the structure; replace with actual ETL pipeline.
- Map visualization uses PyDeck for demonstration; ensure valid API tokens in streamlit secrets.
'''

import streamlit as st
import pandas as pd
import pydeck as pdk
from streamlit_folium import folium_static
import folium

# ========== Data Ingestion & ETL Placeholders ==========
@st.cache_data
def scrape_gov_portals():
    # TODO: implement scraping from MNRE, SECI, POSOCO/Grid India
    return pd.DataFrame()

@st.cache_data
def parse_investor_pdfs():
    # TODO: implement PDF parsing to extract project tables
    return pd.DataFrame()

@st.cache_data
def fetch_satellite_imagery():
    # TODO: integrate with GIS platforms for imagery-based feature extraction
    return pd.DataFrame()

@st.cache_data
def build_dataset():
    # Combine and standardize all sources
    data = [
        {
            'project_name': 'Example Solar Farm',
            'capacity_mw': 100,
            'lat': 26.8467,
            'lon': 80.9462,
            'developer': 'Sample Developer',
            'commissioning_year': 2022,
            'type': 'Utility-scale',
            'cell_technology': 'c-Si',
            'bifacial': True,
            'ppa': 'PPA',
        },
        {
            'project_name': 'Example Solar Farm2',
            'capacity_mw': 1,
            'lat': 26.8467,
            'lon': 80.9462,
            'developer': 'Sample Developer',
            'commissioning_year': 2022,
            'type': 'Utility-scale',
            'cell_technology': 'c-Si',
            'bifacial': True,
            'ppa': 'PPA',
        }
    ]
    return pd.DataFrame(data)

# ========== Main App ==========

def main():
    st.set_page_config(page_title="Solar Detective", layout="wide")
    st.title("🌞 Solar Detective: India's Solar Infrastructure")
    st.markdown("An AI-powered dashboard to explore and filter solar projects nationwide.")

    # Load data
    df = build_dataset()

    # Sidebar filters
    st.sidebar.header("Filters")
    year_opts = sorted(df['commissioning_year'].unique())
    selected_year = st.sidebar.multiselect("Commissioning Year", year_opts, default=year_opts)

    type_opts = df['type'].unique()
    selected_type = st.sidebar.multiselect("Project Type", type_opts, default=type_opts)

    dev_opts = df['developer'].unique()
    selected_dev = st.sidebar.multiselect("Developer", dev_opts, default=dev_opts)

    capacity_range = st.sidebar.slider(
        "Capacity (MW)", float(df['capacity_mw'].min()), float(df['capacity_mw'].max()),
        (float(df['capacity_mw'].min()), float(df['capacity_mw'].max()))
    )

    # Filter data
    filtered = df[
        (df['commissioning_year'].isin(selected_year)) &
        (df['type'].isin(selected_type)) &
        (df['developer'].isin(selected_dev)) &
        (df['capacity_mw'] >= capacity_range[0]) &
        (df['capacity_mw'] <= capacity_range[1])
    ]

    # Layout: map on left, table on right
    col1, col2 = st.columns((2, 1))

    with col1:
        st.subheader("Interactive Map")
        # PyDeck map with larger pins
        if not filtered.empty:
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=filtered,
                get_position='[lon, lat]',
                get_radius=5000,  # increased radius for better visibility
                pickable=True,
                get_fill_color='[255, 165, 0, 160]'
            )
            view_state = pdk.ViewState(
                latitude=filtered['lat'].mean(),
                longitude=filtered['lon'].mean(),
                zoom=5
            )
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
        else:
            st.write("No projects match the selected filters.")

    with col2:
        st.subheader("Project Data")
        st.write(f"Total projects: {len(filtered)}")
        st.dataframe(filtered)

    # Export button
    st.download_button(
        label="Export filtered data as CSV",
        data=filtered.to_csv(index=False).encode('utf-8'),
        file_name='solar_projects_filtered.csv',
        mime='text/csv'
    )

if __name__ == '__main__':
    main()
