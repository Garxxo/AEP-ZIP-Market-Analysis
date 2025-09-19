# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import json
import numpy as np

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

    return pivot, top5, ee_map

pivot, top5, ee_map = load_data(FILE_PATH)

# --- Clean and validate ZIP codes from Excel ---
ee_map = ee_map.dropna(subset=["NAME"]).copy()

# Intentar extraer 5 dígitos seguidos
ee_map["ZIP"] = ee_map["NAME"].str.extract(r"(\d{5})")

# Si no encuentra, limpiar no-dígitos y tomar primeros 5
ee_map["ZIP"] = ee_map["ZIP"].fillna(
    ee_map["NAME"].str.replace(r"\D", "", regex=True).str[:5]
)

# Asegurar formato string de 5 dígitos
ee_map["ZIP"] = ee_map["ZIP"].astype(str).str.zfill(5)

# Filtrar solo Virginia (prefijos 201xx, 220xx–246xx)
va_prefixes = tuple(str(i) for i in range(201, 247))
ee_map = ee_map[ee_map["ZIP"].str[:3].isin(va_prefixes)].copy()

# Debug preview ZIPs
st.write("🔍 Preview cleaned ZIPs:", ee_map[["NAME", "ZIP"]].head(20))

# --- Load GeoJSON simplified ---
@st.cache_data(show_spinner=True)
def load_geojson():
    with open("VA_Zip_Codes_VA.geojson", "r") as f:
        geojson = json.load(f)
    return geojson

geojson_data = load_geojson()

# --- Sidebar filters ---
st.sidebar.header("Filters")

all_names = sorted(ee_map["NAME"].dropna().unique())
select_all = st.sidebar.checkbox("Select/Deselect all ZIPs", value=False)

if select_all:
    names_selected = st.sidebar.multiselect("Choose ZIP Codes", all_names, default=all_names)
else:
    names_selected = st.sidebar.multiselect("Choose ZIP Codes", all_names, default=[])

if not names_selected:
    st.warning("Please select at least one ZIP Code from the sidebar.")
else:
    # --- Multi-ZIP comparison ---
    st.subheader("📊 Multi-ZIP comparison")

    # Convertir nombres seleccionados a ZIPs
    selected_zips = ee_map.loc[ee_map["NAME"].isin(names_selected), "ZIP"].dropna().unique()
    if len(selected_zips) == 0:
        st.error("⚠️ No ZIP codes found for the selected entries. Check Excel column NAME vs sidebar.")
    else:
        multi_data = ee_map[ee_map["ZIP"].isin(selected_zips)]

        # Tabla de sectores agregados
        sector_totals_multi = (
            multi_data.groupby("NAICS2017_LABEL", as_index=False)["ESTAB"].sum()
            .sort_values("ESTAB", ascending=False)
        )

        fig_multi = px.bar(
            sector_totals_multi.head(10).sort_values("ESTAB"),
            x="ESTAB", y="NAICS2017_LABEL",
            orientation="h", text="ESTAB",
            title=f"Top sectors across selected ZIPs ({len(selected_zips)} total)"
        )
        st.plotly_chart(fig_multi, use_container_width=True)

        st.markdown("#### Aggregated table for selected ZIPs")
        st.dataframe(sector_totals_multi, use_container_width=True)

        # --- Interactive Map ---
        st.subheader("🗺️ Map view – Establishments by ZIP")

        # Aggregate totals by ZIP
        zip_totals = multi_data.groupby("ZIP", as_index=False)["ESTAB"].sum()
        zip_totals["ZIP"] = zip_totals["ZIP"].astype(str).str.zfill(5)

        # Crear copia del GeoJSON para no modificar el original
        geojson_copy = {"type": geojson_data["type"], "features": []}
        for feature in geojson_data["features"]:
            f = feature.copy()
            f["properties"]["ZIP_CODE"] = str(f["properties"]["ZIP_CODE"]).zfill(5)
            geojson_copy["features"].append(f)

        # Merge check para depuración
        merged_check = pd.merge(
            zip_totals,
            pd.DataFrame([f["properties"] for f in geojson_copy["features"]]),
            left_on="ZIP",
            right_on="ZIP_CODE",
            how="outer",
            indicator=True
        )
        st.write("🔎 Merge check sample:", merged_check.head(20))

        # Filtrar ZIPs presentes en el DataFrame
        valid_zips = set(zip_totals["ZIP"])
        geojson_copy["features"] = [
            f for f in geojson_copy["features"] if f["properties"]["ZIP_CODE"] in valid_zips
        ]

        # Escala logarítmica
        zip_totals["ESTAB_LOG"] = np.log1p(zip_totals["ESTAB"])

        # Mapa
        fig_map = px.choropleth_mapbox(
            zip_totals,
            geojson=geojson_copy,
            locations="ZIP",
            featureidkey="properties.ZIP_CODE",
            color="ESTAB_LOG",
            hover_name="ZIP",
            hover_data={"ESTAB": True, "ESTAB_LOG": False},
            color_continuous_scale="YlOrRd",
            mapbox_style="carto-positron",
            center={"lat": 37.5, "lon": -79},
            zoom=6,
            opacity=0.6,
            title="Total establishments by ZIP (log scale)"
        )

        st.plotly_chart(fig_map, use_container_width=True, height=700)

# --- Footer ---
with st.expander("ℹ️ About this app"):
    st.markdown("""
    **Purpose:**  
    Provide Appalachian Power with a market sizing tool by ZIP code in Virginia.  

    **Features:**  
    - Select one or multiple ZIPs in the sidebar (with Select/Deselect all option).  
    - Compare top sectors and see aggregated tables.  
    - Interactive choropleth map with establishments per ZIP (logarithmic scale, yellow → red).  
    - Replace Excel or GeoJSON file to refresh the data.  
    """)
