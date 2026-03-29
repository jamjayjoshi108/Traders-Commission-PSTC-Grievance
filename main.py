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
    safe_sheet_name = sheet_name.replace(" ", "%20")
    
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={safe_sheet_name}"
    
    try:
        df = pd.read_csv(url, parse_dates=["Meeting Date"], dayfirst=True)
        df.replace(['Nill', 'NILL', 'nill', 'Nil', 'nil'], pd.NA, inplace=True)
        return df
    except Exception as e:
        st.error(f"Failed to load data from Google Sheets. Error: {e}")
        return pd.DataFrame() 

df = load_data()

if df.empty:
    st.warning("No data found. Please make sure the 'DATABASE FOR DASHBOARD' sheet exists and has data.")
    st.stop()

# Create a unique meeting identifier based strictly on provided geography and date columns
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
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Grievances", len(df))
    with col2:
        st.metric("Districts Covered", df['District'].nunique())
    with col3:
        st.metric("Total Meetings Held", df['Meeting_ID'].nunique())
    with col4:
        st.metric("Citizens Engaged", df['Mobile No.'].nunique())
        
    st.divider()
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("State-Wide Resolution Rate")
        res_counts = df['Resolution Status'].value_counts().reset_index()
        res_counts.columns = ['Status', 'Count']
        fig_pie = px.pie(res_counts, values='Count', names='Status', hole=0.4, 
                         color='Status', color_discrete_map={'Resolved':'#2ca02c', 'Pending':'#d62728'})
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.subheader("Grievances by Department")
        dept_counts = df['Department'].value_counts().reset_index()
        dept_counts.columns = ['Department', 'Count']
        fig_dept = px.bar(dept_counts, x='Count', y='Department', orientation='h')
        fig_dept.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_dept, use_container_width=True)

    st.subheader("Pace of Operations (Grievances Collected Over Time)")
    time_df = df.groupby('Meeting Date').size().reset_index(name='Grievances Collected')
    fig_time = px.line(time_df, x='Meeting Date', y='Grievances Collected', markers=True)
    st.plotly_chart(fig_time, use_container_width=True)

# ==========================================
# TIER 2: THE MESO VIEW (DISTRICT/OPERATIONAL)
# ==========================================
with tab2:
    st.header("District & Operational Diagnostics")
    
    st.subheader("District Scorecard")
    dist_stats = df.groupby('District').agg(
        Total_Grievances=('Sr.No', 'count'),
        Pending=('Resolution Status', lambda x: (x == 'Pending').sum()),
        Resolved=('Resolution Status', lambda x: (x == 'Resolved').sum())
    ).reset_index()
    
    # Handle division by zero safely
    dist_stats['Resolution Rate (%)'] = (dist_stats['Resolved'] / dist_stats['Total_Grievances'] * 100).fillna(0).round(1)
    st.dataframe(dist_stats.sort_values('Total_Grievances', ascending=False), use_container_width=True)

    st.divider()

    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.subheader("Venue & Bazaar Hotspots")
        selected_district = st.selectbox("Select District to Drill Down:", df['District'].unique())
        venue_df = df[df['District'] == selected_district]['Venue / Bazaar'].value_counts().reset_index()
        venue_df.columns = ['Venue', 'Grievances']
        fig_venue = px.bar(venue_df, x='Venue', y='Grievances', title=f"Grievance Volume by Venue in {selected_district}")
        st.plotly_chart(fig_venue, use_container_width=True)
        
    with col_m2:
        st.subheader("Meeting Efficiency")
        meeting_eff = df.groupby(['District', 'Meeting_ID']).size().reset_index(name='Grievance Count')
        fig_eff = px.box(meeting_eff, x='District', y='Grievance Count', title="Distribution of Grievances per Meeting")
        st.plotly_chart(fig_eff, use_container_width=True)

# ==========================================
# TIER 3: THE MICRO VIEW (GRANULAR/ACTIONABLE)
# ==========================================
with tab3:
    st.header("Granular & Actionable Insights")
    
    st.subheader("Actionable Follow-Up List (Pending Grievances)")
    days_old = st.slider("Show pending grievances raised more than X days ago:", 0, 60, 0)
    
    pending_df = df[df['Resolution Status'].str.contains('Pending', na=False, case=False)].copy()
    # Calculates age strictly based on the provided Meeting Date vs Today
    pending_df['Days Since Meeting'] = (pd.Timestamp.now().normalize() - pending_df['Meeting Date']).dt.days
    action_list = pending_df[pending_df['Days Since Meeting'] >= days_old]
    
    st.dataframe(action_list[['District', 'Name of Person', 'Mobile No.', 'Department', 'Grievance Details', 'Days Since Meeting']], use_container_width=True)

    st.divider()
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.subheader("Frequent Complainants")
        freq_comp = df.dropna(subset=['Mobile No.'])['Mobile No.'].value_counts().reset_index()
        freq_comp.columns = ['Mobile No.', 'Total Grievances Logged']
        freq_comp = freq_comp[freq_comp['Total Grievances Logged'] > 1]
        
        freq_names = pd.merge(freq_comp, df[['Mobile No.', 'Name of Person']].drop_duplicates('Mobile No.'), on='Mobile No.', how='left')
        st.dataframe(freq_names, use_container_width=True)

    with col_t2:
        st.subheader("'Other' Department Submissions")
        other_dept = df[df['Department'].str.contains('Any other', na=False, case=False)]
        other_counts = other_dept['Other Dept. Name'].value_counts().reset_index()
        other_counts.columns = ['Manually Entered Department', 'Count']
        st.dataframe(other_counts, use_container_width=True)
        
    st.subheader("Grievance Keyword Search")
    search_term = st.text_input("Filter grievances by specific text (e.g., 'streetlight', 'water'):")
    if search_term:
        theme_df = df[df['Grievance Details'].str.contains(search_term, na=False, case=False)]
        st.write(f"Found **{len(theme_df)}** records mentioning '{search_term}'")
        st.dataframe(theme_df[['District', 'Venue / Bazaar', 'Department', 'Grievance Details', 'Resolution Status']], use_container_width=True)
