import streamlit as st
import pandas as pd
from mplsoccer import Sbopen, Pitch

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Python 360 - Objetivo Analista", layout="wide", page_icon="⚽")

# --- CACHED DATA LOADING ---
@st.cache_data
def load_competitions():
    return Sbopen().competition()

@st.cache_data
def load_matches(competition_id, season_id):
    df = Sbopen().match(competition_id=competition_id, season_id=season_id)
    df['display_name'] = df['home_team_name'] + " " + df['home_score'].astype(str) + "-" + df['away_score'].astype(str) + " " + df['away_team_name']
    return df

@st.cache_data
def load_event_data(match_id):
    return Sbopen().event(match_id)

# --- SIDEBAR ---
with st.sidebar:
    LOGO_URL = "https://objetivoanalista.com/wp-content/uploads/2026/01/logo_horizontal_verde-scaled-251x77.webp"
    st.image(LOGO_URL, use_container_width=True)

    st.title("Competition Selector")
    df_comp = load_competitions()
    comp_name = st.selectbox("Competition", df_comp['competition_name'].unique(), index=0)

    df_season = df_comp[df_comp['competition_name'] == comp_name]
    season_name = st.selectbox("Season", df_season['season_name'].unique())

    selected_row = df_season[df_season['season_name'] == season_name].iloc[0]
    st.divider()
    st.caption("Powered by Statsbomb Open Data")

# --- TABS ---
tab_statsbomb, tab_manual = st.tabs([":material/analytics: StatsBomb Data",
                                     ":material/upload_file: Manual Upload"])

with tab_statsbomb:
    with st.expander("Specific Filters", expanded=True):
        f_col1, f_col2, f_col3 = st.columns(3)
        df_matches = load_matches(selected_row.competition_id, selected_row.season_id)
        with f_col1:
            match_label = st.selectbox("Match", df_matches['display_name'])
            match_id = df_matches[df_matches['display_name'] == match_label].match_id.iloc[0]

        df_events, _, _, df_tactics = load_event_data(match_id)

        with f_col2:
            team_name = st.selectbox("Team", df_events['team_name'].unique())

        with f_col3:
            field_zones = ["Defensive", "Creative", "Attack"]
            zones = st.multiselect("Field Zones", field_zones, default=field_zones)

    # DATA PROCESSING
    all_passes = df_events[(df_events.type_name == 'Pass') & (df_events.team_name == team_name)].copy()
    conditions = []
    if "Defensive" in zones: conditions.append(all_passes['x'] < 40)
    if "Creative" in zones: conditions.append((all_passes['x'] >= 40) & (all_passes['x'] < 80))
    if "Attack" in zones: conditions.append(all_passes['x'] >= 80)

    if conditions:
        df_passes = all_passes[pd.concat(conditions, axis=1).any(axis=1)].copy()
    else:
        df_passes = pd.DataFrame(columns=all_passes.columns)

    completed_passes = df_passes['outcome_name'].isna().sum()   # Empty ones (success)
    failed_passes = df_passes['outcome_name'].notna().sum()     # Ones with text (failure)
    total_passes = len(df_passes) if len(df_passes) > 0 else 1  # Avoid zero division

    # --- VISUALIZATION ---
    col_info, col_pitch = st.columns([1.5, 2])

    with col_info:
        st.subheader("Pass Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total", total_passes, help="Passes in selected zones")
        m2.metric("Completed", completed_passes, delta=f"{int((completed_passes/total_passes)*100)}%", delta_color="normal")
        m3.metric("Missed", failed_passes, delta=f"{int((failed_passes/total_passes)*100)}%", delta_color="inverse")

        st.subheader("Starting Lineup")
        df_tactics = df_tactics[['jersey_number', 'player_name', 'position_name']]
        passes_count = df_passes.groupby('player_name').size().reset_index(name='Passes')
        df_tactics = df_tactics.merge(passes_count, on='player_name', how='left').fillna(0)
        df_tactics['Passes'] = df_tactics['Passes'].astype(int)
        df_tactics = df_tactics.drop_duplicates('player_name')
        st.dataframe(df_tactics.sort_values('jersey_number'), use_container_width=True, hide_index=True)

    with col_pitch:
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#1b4332', line_color='#f8f9fa', linewidth=1.2)
        fig, ax = pitch.draw(figsize=(6, 7.5))

        df_passes['outcome_label'] = df_passes['outcome_name'].fillna('Complete')
        legend_map = {'Complete': '#40916c', 'Incomplete': '#e63946'}

        for _, row in df_passes.iterrows():
            pitch.lines(row.x, row.y, row.end_x, row.end_y, lw=2, comet=True,
                        color=legend_map.get(row['outcome_label'], '#e63946'), alpha=0.5, ax=ax)

        st.pyplot(fig, use_container_width=True)



with tab_manual:
    st.subheader("📁 Local Data Upload")
    uploaded_file = st.file_uploader("Upload your file to preview (CSV)", type=['csv'])

    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            st.success(f"File loaded: {uploaded_file.name}")
            st.dataframe(df_upload, use_container_width=True)
        except Exception as e:
            st.error(f"Error reading file: {e}")
    else:
        st.info("Waiting for CSV file to display the table...")
