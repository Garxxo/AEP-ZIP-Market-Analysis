# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="AEP ZIP Market Analysis", layout="wide")

st.title("📊 Appalachian Power – ZIP Code Market Analysis")
st.caption("Explore establishments by sector across Virginia ZIP codes. Dataset preloaded.")

# --- Load pre-processed Excel ---
FILE_PATH = "AEP_Zips_Processed.xlsx"

@st.cache_data(show_spinner=False)
def load_data(path: str):
    pivot = pd.read_excel(path, sheet_name="ZIP x Sector")
    top5 = pd.read_excel(path, sheet_name="Top5 by ZIP")
    ee_map = pd.read_excel(path, sheet_name="With EE Mapping")

    for df in (pivot, top5, ee_map):
        if "ESTAB" in df.columns:
            df["ESTAB"] = pd.to_numeric(df["ESTAB"], errors="coerce").fillna(0).astype(int)

    ee_map["ZIP"] = ee_map["NAME"].str.extract(r"(\d{5})")
    return pivot, top5, ee_map

pivot, top5, ee_map = load_data(FILE_PATH)

# --- Load GeoJSON simplified ---
@st.cache_data(show_spinner=True)
def load_geojson():
    with open("VA_Zip_Codes_VA.geojson", "r") as f:
        geojson = json.load(f)
    return geojson

geojson_data = load_geojson()

# --- Sidebar filters ---
st.sidebar.header("Filters")

all_zips = sorted(ee_map["ZIP"].dropna().unique())

select_all = st.sidebar.checkbox("Select/Deselect all ZIPs", value=False)

if select_all:
    zips_selected = st.sidebar.multiselect("Choose ZIP Codes", all_zips, default=all_zips)
else:
    zips_selected = st.sidebar.multiselect("Choose ZIP Codes", all_zips, default=[])

if not zips_selected:
    st.warning("Please select at least one ZIP Code from the sidebar.")
else:
    # --- Multi-ZIP comparison ---
    st.subheader("📊 Multi-ZIP comparison")
    multi_data = ee_map[ee_map["ZIP"].isin(zips_selected)]
    sector_totals_multi = (multi_data.groupby("NAICS2017_LABEL", as_index=False)["ESTAB"].sum()
                           .sort_values("ESTAB", ascending=False))

    fig_multi = px.bar(
        sector_totals_multi.head(10).sort_values("ESTAB"),
        x="ESTAB", y="NAICS2017_LABEL",
        orientation="h", text="ESTAB",
        title=f"Top sectors across selected ZIPs ({len(zips_selected)} total)"
    )
    st.plotly_chart(fig_multi, use_container_width=True)

    st.markdown("#### Aggregated table for selected ZIPs")
    st.dataframe(sector_totals_multi, use_container_width=True)

    # --- Interactive Map ---
    st.subheader("🗺️ Map view – Establishments by ZIP")

    zip_totals = multi_data.groupby("ZIP", as_index=False)["ESTAB"].sum()
    zip_totals["ZIP"] = zip_totals["ZIP"].astype(str)

    # Ensure GeoJSON ZIP_CODE is string
    for feature in geojson_data["features"]:
        feature["properties"]["ZIP_CODE"] = str(feature["properties"]["ZIP_CODE"])

    fig_map = px.choropleth_mapbox(
        zip_totals,
        geojson=geojson_data,
        locations="ZIP",
        featureidkey="properties.ZIP_CODE",
        color="ESTAB",
        hover_name="ZIP",
        mapbox_style="carto-positron",
        center={"lat": 37.5, "lon": -79},
        zoom=6,
        opacity=0.6,
        title="Total establishments by ZIP"
    )
    st.plotly_chart(fig_map, use_container_width=True)

# --- Footer ---
with st.expander("ℹ️ About this app"):
    st.markdown("""
    **Purpose:**  
    Provide Appalachian Power with a market sizing tool by ZIP code in Virginia.  

    **Features:**  
    - Select one or multiple ZIPs in the sidebar.  
    - Compare top sectors and see aggregated tables.  
    - Interactive choropleth map with establishments per ZIP.  
    - Replace Excel or GeoJSON file to refresh the data.  
    """)
