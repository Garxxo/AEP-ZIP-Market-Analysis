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

    # Convert numeric
    for df in (pivot, top5, ee_map):
        if "ESTAB" in df.columns:
            df["ESTAB"] = pd.to_numeric(df["ESTAB"], errors="coerce").fillna(0).astype(int)

    # Extract clean ZIP
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
all_zips = sorted(ee_map["NAME"].dropna().unique())
zip_selected = st.sidebar.selectbox("Select a ZIP Code (detailed view)", all_zips)
multi_zips = st.sidebar.multiselect("Compare multiple ZIPs", all_zips, default=[all_zips[0]])

# --- Single ZIP detailed view ---
st.subheader(f"📍 Detailed view: {zip_selected}")
zip_data = ee_map[ee_map["NAME"] == zip_selected]

# Top 5 chart
top5_zip = top5[top5["NAME"] == zip_selected][["NAICS2017_LABEL", "ESTAB"]]
if not top5_zip.empty:
    fig_top5 = px.bar(
        top5_zip.sort_values("ESTAB"),
        x="ESTAB", y="NAICS2017_LABEL",
        orientation="h", text="ESTAB",
        title="Top 5 sectors by establishments"
    )
    st.plotly_chart(fig_top5, use_container_width=True)

# Pie chart
if not zip_data.empty:
    fig_pie = px.pie(
        zip_data, names="NAICS2017_LABEL", values="ESTAB",
        title="Sector distribution (all sectors)"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### ⚡ Energy Efficiency (EE) Opportunities")
    st.dataframe(zip_data[["NAICS2017_LABEL", "ESTAB", "EE_Opportunity"]]
                 .sort_values("ESTAB", ascending=False),
                 use_container_width=True)

# --- Multi-ZIP comparison ---
st.subheader("📊 Multi-ZIP comparison")
if multi_zips:
    multi_data = ee_map[ee_map["NAME"].isin(multi_zips)]
    sector_totals_multi = (multi_data.groupby("NAICS2017_LABEL", as_index=False)["ESTAB"].sum()
                           .sort_values("ESTAB", ascending=False))

    fig_multi = px.bar(
        sector_totals_multi.head(10).sort_values("ESTAB"),
        x="ESTAB", y="NAICS2017_LABEL",
        orientation="h", text="ESTAB",
        title=f"Top sectors across selected ZIPs ({len(multi_zips)} total)"
    )
    st.plotly_chart(fig_multi, use_container_width=True)

    st.markdown("#### Aggregated table for selected ZIPs")
    st.dataframe(sector_totals_multi, use_container_width=True)

# --- Aggregate across ALL ZIPs ---
st.subheader("📈 Aggregate across ALL ZIPs")
sector_totals = (ee_map.groupby("NAICS2017_LABEL", as_index=False)["ESTAB"].sum()
                 .sort_values("ESTAB", ascending=False))
fig_totals = px.bar(
    sector_totals.head(10).sort_values("ESTAB"),
    x="ESTAB", y="NAICS2017_LABEL",
    orientation="h", title="Top 10 sectors across all ZIPs"
)
st.plotly_chart(fig_totals, use_container_width=True)

st.markdown("### Heatmap preview — Establishments by ZIP and Sector")
st.dataframe(pivot.set_index("NAME"), use_container_width=True)

# --- Interactive Map ---
st.subheader("🗺️ Map view – Establishments by ZIP")

zip_totals = ee_map.groupby("ZIP", as_index=False)["ESTAB"].sum()

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

# --- Download filtered data ---
csv_bytes = zip_data.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download selected ZIP data (CSV)",
    data=csv_bytes,
    file_name=f"{zip_selected.replace(' ', '_')}_analysis.csv",
    mime="text/csv"
)

# --- Footer ---
with st.expander("ℹ️ About this app"):
    st.markdown("""
    **Purpose:**  
    Provide Appalachian Power with a market sizing tool by ZIP code in Virginia.  

    **Features:**  
    - Explore a single ZIP in detail (Top 5 sectors, distribution, EE opportunities).  
    - Compare multiple ZIPs at once.  
    - Aggregate analysis across all ZIPs.  
    - Interactive map of Virginia ZIP codes colored by total establishments.  
    - Download data for a selected ZIP as CSV.  

    **Usage:**  
    - Use the sidebar to select one or multiple ZIPs.  
    - Charts update automatically.  
    - Replace `AEP_Zips_Processed.xlsx` in the repo to refresh data.  
    - Replace `VA_Zip_Codes_VA.geojson` if updated boundaries are needed.  
    """)
