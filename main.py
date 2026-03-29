import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="PSTC Grievance Dashboard", layout="wide")
st.title("Punjab State Traders Commission - Grievance Dashboard")

# --- LIVE DATA LOADING FROM GOOGLE SHEETS ---
@st.cache_data(ttl=600)  
def load_data():
    sheet_id = "1rGwwRllkS30zA6ieOWvGOkSZUWy4BB9ZyGg64VRosUA"
    sheet_name = "DATABASE FOR DASHBOARD"
    
    # FIX: Replace spaces with %20 so the URL is valid
    safe_sheet_name = sheet_name.replace(" ", "%20")
    
    # Use the safe_sheet_name in the URL
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={safe_sheet_name}"
    
    try:
        df = pd.read_csv(url, parse_dates=["Meeting Date"])
        df.replace(['Nill', 'NILL', 'nill', 'Nil', 'nil'], pd.NA, inplace=True)
        return df
    except Exception as e:
        st.error(f"Failed to load data from Google Sheets. Error: {e}")
        return pd.DataFrame()

# Load the data
df = load_data()

# Stop execution if data is empty (e.g., if the script hasn't run yet or sheet is empty)
if df.empty:
    st.warning("No data found. Please make sure the 'DATABASE FOR DASHBOARD' sheet exists and has data.")
    st.stop()

# Create a unique meeting identifier (District + Halqa + Venue + Date)
df['Meeting_ID'] = df['District'].astype(str) + "_" + \
                   df['Halqa'].astype(str) + "_" + \
                   df['Venue / Bazaar'].astype(str) + "_" + \
                   df['Meeting Date'].astype(str)

# --- DASHBOARD TABS ---
tab1, tab2, tab3 = st.tabs(["Tier 1: Apex View (State)", "Tier 2: Meso View (District)", "Tier 3: Micro View (Actionable)"])

# ==========================================
# TIER 1: THE APEX VIEW (STATE-LEVEL)
# ==========================================
with tab1:
    st.header("State-Level Strategy & Overview")
    
    # 1. Total Volume & Footprint
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Grievances", len(df))
    with col2:
        st.metric("Districts Covered", df['District'].nunique())
    with col3:
        st.metric("Total Meetings Held", df['Meeting_ID'].nunique())
    with col4:
        st.metric("Citizens Engaged", df['Mobile No.'].nunique()) # Proxied by unique mobile numbers
        
    st.divider()
    
    col_chart1, col_chart2 = st.columns(2)
    
    # 2. State-Wide Resolution Rate
    with col_chart1:
        st.subheader("Resolution Rate")
        res_counts = df['Resolution Status'].value_counts().reset_index()
        res_counts.columns = ['Status', 'Count']
        fig_pie = px.pie(res_counts, values='Count', names='Status', hole=0.4, 
                         color='Status', color_discrete_map={'Resolved':'#2ca02c', 'Pending':'#d62728'})
        st.plotly_chart(fig_pie, use_container_width=True)

    # 3. The Departmental Heatmap
    with col_chart2:
        st.subheader("Grievances by Department")
        dept_counts = df['Department'].value_counts().reset_index()
        dept_counts.columns = ['Department', 'Count']
        fig_dept = px.bar(dept_counts, x='Count', y='Department', orientation='h')
        fig_dept.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_dept, use_container_width=True)

    # 4. Pace of Operations
    st.subheader("Pace of Operations (Grievances Over Time)")
    time_df = df.groupby('Meeting Date').size().reset_index(name='Grievances Collected')
    fig_time = px.line(time_df, x='Meeting Date', y='Grievances Collected', markers=True)
    st.plotly_chart(fig_time, use_container_width=True)


# ==========================================
# TIER 2: THE MESO VIEW (DISTRICT/OPERATIONAL)
# ==========================================
with tab2:
    st.header("District & Operational Diagnostics")
    
    # 1. District-by-District Scorecard
    st.subheader("District Scorecard")
    dist_stats = df.groupby('District').agg(
        Total_Grievances=('Sr.No', 'count'),
        Pending=('Resolution Status', lambda x: (x == 'Pending').sum()),
        Resolved=('Resolution Status', lambda x: (x == 'Resolved').sum())
    ).reset_index()
    dist_stats['Resolution Rate (%)'] = (dist_stats['Resolved'] / dist_stats['Total_Grievances'] * 100).round(1)
    st.dataframe(dist_stats.sort_values('Total_Grievances', ascending=False), use_container_width=True)

    st.divider()

    col_m1, col_m2 = st.columns(2)
    
    # 2. Department vs. Geography Intersections
    with col_m1:
        st.subheader("Department Hotspots by District")
        heatmap_data = pd.crosstab(df['District'], df['Department'])
        fig_heat = px.density_heatmap(df, x='Department', y='District', text_auto=True, color_continuous_scale="Blues")
        st.plotly_chart(fig_heat, use_container_width=True)

    # 3. Halqa & Bazaar Hotspots
    with col_m2:
        st.subheader("Venue Hotspots")
        selected_district = st.selectbox("Select District to Drill Down:", df['District'].unique())
        venue_df = df[df['District'] == selected_district]['Venue / Bazaar'].value_counts().reset_index()
        venue_df.columns = ['Venue', 'Grievances']
        fig_venue = px.bar(venue_df, x='Venue', y='Grievances', title=f"Hotspots in {selected_district}")
        st.plotly_chart(fig_venue, use_container_width=True)
        
    # 4. Meeting Efficiency
    st.subheader("Meeting Efficiency (Grievances per Meeting)")
    meeting_eff = df.groupby(['District', 'Meeting_ID']).size().reset_index(name='Grievance Count')
    fig_eff = px.box(meeting_eff, x='District', y='Grievance Count', points="all")
    st.plotly_chart(fig_eff, use_container_width=True)


# ==========================================
# TIER 3: THE MICRO VIEW (GRANULAR/ACTIONABLE)
# ==========================================
with tab3:
    st.header("Granular & Actionable Insights")
    
    # 1. Actionable Follow-up Lists
    st.subheader("Follow-Up Action List")
    days_old = st.slider("Show pending grievances older than (Days):", 0, 60, 7)
    
    # Filter for Pending and calculate age (assuming today's date for calculation)
    # Note: Streamlit recalculates on the fly, making this dynamic
    pending_df = df[df['Resolution Status'].str.contains('Pending', na=False, case=False)].copy()
    pending_df['Days_Old'] = (pd.Timestamp.now() - pending_df['Meeting Date']).dt.days
    action_list = pending_df[pending_df['Days_Old'] >= days_old]
    
    st.dataframe(action_list[['District', 'Name of Person', 'Mobile No.', 'Department', 'Grievance Details', 'Days_Old']], use_container_width=True)

    st.divider()
    
    col_t1, col_t2 = st.columns(2)
    
    # 2. Frequent Complainants
    with col_t1:
        st.subheader("Frequent Complainants (By Mobile No.)")
        freq_comp = df.dropna(subset=['Mobile No.'])['Mobile No.'].value_counts().reset_index()
        freq_comp.columns = ['Mobile No.', 'Times Complained']
        freq_comp = freq_comp[freq_comp['Times Complained'] > 1]
        
        # Merge back to get names
        freq_names = pd.merge(freq_comp, df[['Mobile No.', 'Name of Person']].drop_duplicates('Mobile No.'), on='Mobile No.', how='left')
        st.dataframe(freq_names, use_container_width=True)

    # 3. "Other" Department Audits
    with col_t2:
        st.subheader("'Other' Department Audit")
        other_dept = df[df['Department'].str.contains('Any other', na=False, case=False)]
        other_counts = other_dept['Other Dept. Name'].value_counts().reset_index()
        other_counts.columns = ['Manually Entered Department', 'Count']
        st.dataframe(other_counts, use_container_width=True)
        
    # 4. Text/Thematic Analysis
    st.subheader("Thematic Analysis of Grievances")
    search_term = st.text_input("Search Grievances for keywords (e.g., 'streetlight', 'drainage'):")
    if search_term:
        theme_df = df[df['Grievance Details'].str.contains(search_term, na=False, case=False)]
        st.write(f"Found **{len(theme_df)}** grievances mentioning '{search_term}'")
        st.dataframe(theme_df[['District', 'Department', 'Grievance Details']], use_container_width=True)
