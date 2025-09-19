# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

st.set_page_config(page_title="AEP ZIP Market Analysis", layout="wide")

st.title("📊 Appalachian Power – ZIP Code Market Analysis")
st.caption("Explore establishments by sector across Virginia ZIP codes. Select ZIPs from the sidebar to highlight them on the map.")

# --- Paths ---
FILE_PATH = "AEP_Zips_Processed.xlsx"
GEOJSON_PATH = "VA_ZipCodes.geojson"

# --- Load Excel ---
@st.cache_data(show_spinner=False)
def load_data(path: str):
    pivot = pd.read_excel(path, sheet_name="ZIP x Sector")
    top5 = pd.read_excel(path, sheet_name="Top5 by ZIP")
    ee_map = pd.read_excel(path, sheet_name="With EE Mapping")

    for df in (pivot, top5, ee_map):
        if "ESTAB" in df.columns:
            df["ESTAB"] = pd.to_numeric(df["ESTAB"], errors="coerce").fillna(0).astype(int)

    # Extraer ZIP desde NAME
    ee_map["ZIP"] = ee_map["NAME"].str.extract(r"(\d{5})")
    ee_map = ee_map.dropna(subset=["ZIP"])
    ee_map["ZIP"] = ee_map["ZIP"].astype(str).str.zfill(5)

    return pivot, top5, ee_map

pivot, top5, ee_map = load_data(FILE_PATH)

# --- Load reduced GeoJSON ---
@st.cache_data(show_spinner=True)
def load_geojson(path: str):
    with open(path, "r") as f:
        geojson = json.load(f)
    return geojson

geojson_data = load_geojson(GEOJSON_PATH)

# --- Prepare totals ---
zip_totals = ee_map.groupby("ZIP", as_index=False)["ESTAB"].sum()
zip_totals["ZIP"] = zip_totals["ZIP"].astype(str).str.zfill(5)

# Extract centroid coordinates for labels
zip_centroids = {}
for feature in geojson_data["features"]:
    z = feature["properties"]["ZCTA5CE20"]
    lon = feature["properties"].get("INTPTLON20")
    lat = feature["properties"].get("INTPTLAT20")
    if lon and lat:
        zip_centroids[z] = (float(lon), float(lat))

zip_totals["lon"] = zip_totals["ZIP"].map(lambda z: zip_centroids.get(z, (None, None))[0])
zip_totals["lat"] = zip_totals["ZIP"].map(lambda z: zip_centroids.get(z, (None, None))[1])

# --- Sidebar filters ---
st.sidebar.header("Filters")
all_names = sorted(ee_map["NAME"].dropna().unique())
sidebar_selection = st.sidebar.multiselect("Choose ZIP Codes", all_names)

final_selected_zips = ee_map.loc[ee_map["NAME"].isin(sidebar_selection), "ZIP"].unique()

if not len(final_selected_zips):
    st.warning("Please select at least one ZIP from the sidebar.")
    st.stop()

multi_data = ee_map[ee_map["ZIP"].isin(final_selected_zips)]

# --- Map view ---
st.subheader("🗺️ Map – Selected ZIPs highlighted")

# Base map (all zips in gray)
fig_map = px.choropleth_mapbox(
    zip_totals,
    geojson=geojson_data,
    locations="ZIP",
    featureidkey="properties.ZCTA5CE20",
    color_discrete_sequence=["lightgray"],  # base in gray
    mapbox_style="carto-positron",
    center={"lat": 37.5, "lon": -79},
    zoom=6,
    opacity=0.3
)

# Overlay selected ZIPs with normal scale and global min/max
selected_totals = zip_totals[zip_totals["ZIP"].isin(final_selected_zips)]

fig_map.add_trace(go.Choroplethmapbox(
    geojson=geojson_data,
    locations=selected_totals["ZIP"],
    z=selected_totals["ESTAB"],   # escala normal
    featureidkey="properties.ZCTA5CE20",
    colorscale="YlOrRd",
    zmin=zip_totals["ESTAB"].min(),
    zmax=zip_totals["ESTAB"].max(),
    marker_opacity=0.8,
    marker_line_width=0.5,
    text=selected_totals["ZIP"],
    hovertemplate="ZIP: %{text}<br>Establishments: %{z}<extra></extra>",
    colorbar=dict(title="Establishments")
))

# Add labels for ALL ZIPs
fig_map.add_trace(go.Scattermapbox(
    lon=zip_totals["lon"],
    lat=zip_totals["lat"],
    text=zip_totals["ZIP"],
    mode="text",
    textfont=dict(size=10, color="black"),
    hoverinfo="none",
    showlegend=False  # evita que aparezca "trace 2"
))

# Bigger map
st.plotly_chart(fig_map, use_container_width=True, height=900)

# --- Top 5 sectors ---
st.subheader(f"🏆 Top 5 sectors in selected ZIPs ({len(final_selected_zips)})")
top5_chart = (
    multi_data.groupby("NAICS2017_LABEL", as_index=False)["ESTAB"].sum()
    .sort_values("ESTAB", ascending=False)
    .head(5)
)
fig_top5 = px.bar(
    top5_chart.sort_values("ESTAB"),
    x="ESTAB", y="NAICS2017_LABEL",
    orientation="h", text="ESTAB"
)
st.plotly_chart(fig_top5, use_container_width=True)

# --- Sector distribution pie ---
st.subheader(f"🥧 Sector distribution in selected ZIPs ({len(final_selected_zips)})")
sector_totals = (
    multi_data.groupby("NAICS2017_LABEL", as_index=False)["ESTAB"].sum()
    .sort_values("ESTAB", ascending=False)
)
fig_pie = px.pie(
    sector_totals,
    values="ESTAB", names="NAICS2017_LABEL",
    title="Sector distribution"
)
st.plotly_chart(fig_pie, use_container_width=True)

# --- EE Opportunities ---
st.subheader("⚡ EE Opportunities by sector (selected ZIPs)")
if "EE_Opportunity" in multi_data.columns:
    ee_summary = (
        multi_data.groupby(["NAICS2017_LABEL", "EE_Opportunity"], as_index=False)["ESTAB"].sum()
        .sort_values("ESTAB", ascending=False)
    )
    st.dataframe(ee_summary, use_container_width=True)
else:
    st.info("No EE mapping available in this dataset.")

# --- Heatmap table ---
st.subheader("🔥 Establishments by ZIP and Sector (selected ZIPs)")
heatmap_data = pd.pivot_table(
    multi_data,
    values="ESTAB",
    index="NAME",
    columns="NAICS2017_LABEL",
    aggfunc="sum",
    fill_value=0
)
st.dataframe(heatmap_data, use_container_width=True)

csv_data = heatmap_data.to_csv().encode("utf-8")
st.download_button(
    "Download selected ZIP data (CSV)",
    data=csv_data,
    file_name="zip_sector_data.csv",
    mime="text/csv"
)

# --- Footer ---
with st.expander("ℹ️ About this app"):
    st.markdown("""
    **Purpose:**  
    Provide Appalachian Power with a market sizing tool by ZIP code in Virginia.  

    **Features:**  
    - Highlight ZIPs by selecting them in the sidebar.  
    - Map shows all ZIPs in gray, with selected ZIPs highlighted in color.  
    - ZIP numbers are printed on the map for easy reference.  
    - Compare top sectors and see aggregated tables.  
    - Visualize distribution with bar and pie charts.  
    - EE Opportunities table (if available in dataset).  
    - Heatmap-style table with option to export CSV.  
    """)
