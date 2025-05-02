'''
Solar Detective: Mapping India's Solar Infrastructure Using Agentic AI

Role: P = Programming and code guru
Verbosity Level: V = 2

Context and Assumptions:
- Single-page Streamlit app using tabs: Dashboard & Surveying.
- Surveying tab uses Folium with Leaflet Draw plugin via streamlit_folium to visually select an ROI.
- After drawing, extracts bounding box lat/lon and displays placeholders for satellite imagery.
'''

import streamlit as st
import pandas as pd
import pydeck as pdk
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode

# ========== Page Configuration ==========
st.set_page_config(page_title="Solar Detective", layout="wide")

# ========== Data Ingestion Placeholders ==========
@st.cache_data
def build_dataset():
    data = [
        {'project_name':'Example Solar Farm','capacity_mw':100,'lat':26.8467,'lon':80.9462,
         'developer':'Sample Developer','commissioning_year':2022,'type':'Utility-scale',
         'cell_technology':'c-Si','bifacial':True,'ppa':'PPA'},
        {'project_name':'Example Solar Farm2','capacity_mw':1,'lat':26.8467,'lon':80.9462,
         'developer':'Sample Developer','commissioning_year':2022,'type':'Utility-scale',
         'cell_technology':'c-Si','bifacial':True,'ppa':'PPA'}
    ]
    return pd.DataFrame(data)

# ========== Main Application ==========
def main():
    st.title("🌞 Solar Detective: India's Solar Infrastructure")
    tab1, tab2 = st.tabs(["Dashboard", "Surveying"])

    # Load data once
    df = build_dataset()

    # --- Dashboard Tab ---
    with tab1:
        st.subheader("Project Dashboard")
        # Filters in columns
        col1, col2, col3, col4 = st.columns([1,1,1,2])
        years = sorted(df['commissioning_year'].unique())
        types = sorted(df['type'].unique())
        devs = sorted(df['developer'].unique())
        sel_y = col1.multiselect("Year", years)
        sel_y = sel_y if sel_y else years
        sel_t = col2.multiselect("Type", types)
        sel_t = sel_t if sel_t else types
        sel_d = col3.multiselect("Developer", devs)
        sel_d = sel_d if sel_d else devs
        cap_min, cap_max = float(df['capacity_mw'].min()), float(df['capacity_mw'].max())
        sel_c = col4.slider("Capacity (MW)", cap_min, cap_max, (cap_min, cap_max))

        # Apply filters
        filtered = df[
            df['commissioning_year'].isin(sel_y) &
            df['type'].isin(sel_t) &
            df['developer'].isin(sel_d) &
            df['capacity_mw'].between(sel_c[0], sel_c[1])
        ]

        # Project table with selection via row click
        st.markdown("**Select a project to recenter the map:**")
        gb = GridOptionsBuilder.from_dataframe(filtered)
        gb.configure_selection(selection_mode="single", use_checkbox=False)
        grid_options = gb.build()
        grid_response = AgGrid(
            filtered,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=True,
            height=250,
            theme='streamlit'
        )
        selected_rows = grid_response.get('selected_rows', [])

        # Determine map center and zoom
        if isinstance(selected_rows, list) and len(selected_rows) > 0:
            sel = selected_rows[0]
            center = [sel['lat'], sel['lon']]
            zoom = 8
        else:
            if not filtered.empty:
                center = [filtered['lat'].mean(), filtered['lon'].mean()]
                zoom = 5
            else:
                center = [0, 0]
                zoom = 2

        # Tooltip configuration
        tooltip = {
            "html": "<b>{project_name}</b><br/>Capacity: {capacity_mw} MW<br/>Developer: {developer}",
            "style": {"backgroundColor": "#333333", "color": "#FFFFFF", "fontSize": "12px", "padding": "5px"}
        }

        # Map visualization
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=filtered,
            get_position='[lon, lat]',
            get_radius=8000,
            pickable=True,
            get_fill_color='[255,165,0,200]'
        )
        view_state = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=zoom)
        st.subheader("Interactive Map View")
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip), use_container_width=True)

        # Export filtered data
        st.download_button(
            label="Export filtered data as CSV",
            data=filtered.to_csv(index=False).encode('utf-8'),
            file_name='solar_projects_filtered.csv',
            mime='text/csv'
        )

    # --- Surveying Tab ---
    with tab2:
        st.subheader("Surveying: Draw Region of Interest")
        st.markdown("Use the draw tool on the map to create a rectangle bounding box. Coordinates will appear below.")

        # Initialize Folium map with draw controls
        m = folium.Map(location=[20,80], zoom_start=5)
        draw = Draw(
            draw_options={'rectangle': True, 'polygon': False, 'polyline': False, 'circle': False, 'marker': False, 'circlemarker': False},
            edit_options={'edit': True}
        )
        draw.add_to(m)

        # Render map and capture draw events
        map_data = st_folium(m, height=500, width=800)
        drawings = map_data.get('all_drawings')
        if drawings:
            last = drawings[-1]
            coords = last['geometry']['coordinates'][0]  # rectangle coords
            lons = [pt[0] for pt in coords]
            lats = [pt[1] for pt in coords]
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            st.write(f"**Bounding Box Coordinates:**")
            st.write(f"Latitude: {min_lat:.4f} to {max_lat:.4f}")
            st.write(f"Longitude: {min_lon:.4f} to {max_lon:.4f}")
            st.info("Satellite imagery integration placeholder: feed these coords to your GIS API.")

if __name__ == '__main__':
    main()
