# -*- coding: utf-8 -*-
# --- Sidebar filters ---
st.sidebar.header("Filters")

all_zips = sorted(ee_map["ZIP"].dropna().unique())

# Checkbox to select/deselect all
select_all = st.sidebar.checkbox("Select/Deselect all ZIPs", value=False)

if select_all:
    zips_selected = st.sidebar.multiselect("Choose ZIP Codes", all_zips, default=all_zips)
else:
    zips_selected = st.sidebar.multiselect("Choose ZIP Codes", all_zips, default=[])

# If nothing selected, show a warning
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

    # Aggregate totals by ZIP for selected zips
    zip_totals = multi_data.groupby("ZIP", as_index=False)["ESTAB"].sum()
    zip_totals["ZIP"] = zip_totals["ZIP"].astype(str)

    # Force ZIP_CODE in GeoJSON to be string
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

