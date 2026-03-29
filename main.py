import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="PSTC Grievance Dashboard", layout="wide")

# Custom UI Palette: Navy Blue (#0066A4) and Broom Yellow (#F2B200)
st.markdown("""
    <style>
    /* Nuke the useless top space */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        margin-top: 0rem !important;
    }
    
    footer {visibility: hidden;}
    
    .minute-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        font-size: 10px;
        color: #888888;
        background-color: #ffffff;
        padding: 10px 0px;
        z-index: 999;
    }
    @media (prefers-color-scheme: dark) {
        .minute-footer { background-color: #0e1117; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("Punjab State Traders Commission - Grievance Dashboard")

# -----------------------------------------------------------------------------
# 2. LIVE DATA LOADING FROM GOOGLE SHEETS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=6)  
def load_data():
    sheet_id = "1rGwwRllkS30zA6ieOWvGOkSZUWy4BB9ZyGg64VRosUA"
    sheet_name = "DATABASE FOR DASHBOARD"
    safe_sheet_name = sheet_name.replace(" ", "%20")
    
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={safe_sheet_name}"
    
    try:
        # Load without relying solely on parse_dates
        df = pd.read_csv(url)
        df.replace(['Nill', 'NILL', 'nill', 'Nil', 'nil'], pd.NA, inplace=True)
        
        # FIX: Force the column to be datetime. 
        # errors='coerce' turns any unreadable text/blanks into NaT (Not a Time) instead of crashing.
        df['Meeting Date'] = pd.to_datetime(df['Meeting Date'], errors='coerce', dayfirst=True)
        
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

# -----------------------------------------------------------------------------
# 3. DASHBOARD TABS & LOGIC
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Apex View (State)", "Meso View (District)", "Micro View (Actionable)"])

# Reusable function for the custom styling KPI Cards
def create_kpi_card(title, value):
    return f"""
    <div style="background: linear-gradient(135deg, #0066A4 0%, #002244 100%); 
                padding: 15px 5px; border-radius: 10px; border-bottom: 5px solid #F2B200;
                box-shadow: 0px 4px 10px rgba(0,0,0,0.1); text-align: center; margin-bottom: 15px;">
        <p style="color: #F2B200; font-size: 0.95rem; font-weight: bold; margin-bottom: 5px; text-transform: uppercase;">{title}</p>
        <h2 style="color: #FFFFFF; font-size: 2.2rem; font-weight: 800; margin: 0;">{value}</h2>
    </div>
    """

# ==========================================
# TIER 1: THE APEX VIEW (STATE-LEVEL)
# ==========================================
with tab1:
    st.header("State-Level Strategy & Overview")
    
    # Custom Styled KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(create_kpi_card("Total Grievances", f"{len(df):,}"), unsafe_allow_html=True)
    col2.markdown(create_kpi_card("Districts Covered", f"{df['District'].nunique():,}"), unsafe_allow_html=True)
    col3.markdown(create_kpi_card("Total Meetings Held", f"{df['Meeting_ID'].nunique():,}"), unsafe_allow_html=True)
    col4.markdown(create_kpi_card("Citizens Engaged", f"{df['Mobile No.'].nunique():,}"), unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        with st.container(border=True):
            st.markdown("📊 **State-Wide Resolution Rate**")
            res_counts = df['Resolution Status'].value_counts().reset_index()
            res_counts.columns = ['Status', 'Count']
            # Adapted to use the custom Navy and Yellow colors
            fig_pie = px.pie(res_counts, values='Count', names='Status', hole=0.4, 
                             color='Status', color_discrete_map={'Resolved':'#0066A4', 'Pending':'#F2B200'})
            fig_pie.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        with st.container(border=True):
            st.markdown("🏢 **Grievances by Department**")
            dept_counts = df['Department'].value_counts().reset_index()
            dept_counts.columns = ['Department', 'Count']
            fig_dept = px.bar(dept_counts, x='Count', y='Department', orientation='h')
            fig_dept.update_traces(marker_color='#0066A4')
            fig_dept.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig_dept, use_container_width=True)

    with st.container(border=True):
        st.markdown("📈 **Pace of Operations (Grievances Collected Over Time)**")
        time_df = df.groupby('Meeting Date').size().reset_index(name='Grievances Collected')
        fig_time = px.line(time_df, x='Meeting Date', y='Grievances Collected', markers=True, line_shape='spline', color_discrete_sequence=['#F2B200'])
        fig_time.update_traces(marker=dict(color='#0066A4', size=8))
        fig_time.update_layout(margin=dict(t=20, b=20, l=10, r=10))
        st.plotly_chart(fig_time, use_container_width=True)

# ==========================================
# TIER 2: THE MESO VIEW (DISTRICT/OPERATIONAL)
# ==========================================
with tab2:
    st.header("District & Operational Diagnostics")
    
    st.markdown("📋 **District Scorecard**")
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
        with st.container(border=True):
            st.markdown("📍 **Venue & Bazaar Hotspots**")
            selected_district = st.selectbox("Select District to Drill Down:", df['District'].unique())
            venue_df = df[df['District'] == selected_district]['Venue / Bazaar'].value_counts().reset_index()
            venue_df.columns = ['Venue', 'Grievances']
            fig_venue = px.bar(venue_df, x='Venue', y='Grievances', title=f"Grievance Volume in {selected_district}")
            fig_venue.update_traces(marker_color='#0066A4')
            fig_venue.update_layout(margin=dict(t=30, b=20, l=10, r=10))
            st.plotly_chart(fig_venue, use_container_width=True)
        
    with col_m2:
        with st.container(border=True):
            st.markdown("⏱️ **Meeting Efficiency**")
            meeting_eff = df.groupby(['District', 'Meeting_ID']).size().reset_index(name='Grievance Count')
            fig_eff = px.box(meeting_eff, x='District', y='Grievance Count', title="Distribution of Grievances per Meeting", color_discrete_sequence=['#F2B200'])
            fig_eff.update_traces(marker_color='#0066A4')
            fig_eff.update_layout(margin=dict(t=30, b=20, l=10, r=10))
            st.plotly_chart(fig_eff, use_container_width=True)

# ==========================================
# TIER 3: THE MICRO VIEW (GRANULAR/ACTIONABLE)
# ==========================================
with tab3:
    st.header("Granular & Actionable Insights")
    
    st.markdown("⏳ **30-Day Resolution Countdown (Pending Grievances)**")
    
    # Get all pending (or blank) statuses
    pending_df = df.copy()
    pending_df['Resolution Status'] = pending_df['Resolution Status'].fillna('Pending')
    
    # Now filter for Pending
    pending_df = pending_df[pending_df['Resolution Status'].str.contains('Pending', case=False, na=False)].copy()
    
    # Calculate days old AND Days Remaining (30-day SLA)
    pending_df['Days Since Meeting'] = (pd.Timestamp.now().normalize() - pending_df['Meeting Date']).dt.days
    pending_df['Days Remaining'] = 30 - pending_df['Days Since Meeting']
    
    # Sort so the most urgent (lowest or negative days remaining) appear at the absolute top
    pending_df = pending_df.sort_values('Days Remaining', ascending=True)
    
    # Define the columns we want to show
    display_cols = ['District', 'Name of Person', 'Mobile No.', 'Department', 'Meeting Date', 'Days Remaining', 'Grievance Details']
    
    # Filter widget to toggle between All Pending and strictly Overdue
    filter_option = st.radio("Filter List:", ["All Pending", "Overdue (0 or fewer days remaining)"], horizontal=True)
    
    if filter_option == "Overdue (0 or fewer days remaining)":
        display_df = pending_df[pending_df['Days Remaining'] <= 0]
    else:
        display_df = pending_df

    st.dataframe(display_df[display_cols], use_container_width=True)

    st.divider()
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("👥 **Frequent Complainants**")
        freq_comp = df.dropna(subset=['Mobile No.'])['Mobile No.'].value_counts().reset_index()
        freq_comp.columns = ['Mobile No.', 'Total Grievances Logged']
        freq_comp = freq_comp[freq_comp['Total Grievances Logged'] > 1]
        
        freq_names = pd.merge(freq_comp, df[['Mobile No.', 'Name of Person']].drop_duplicates('Mobile No.'), on='Mobile No.', how='left')
        st.dataframe(freq_names, use_container_width=True)

    with col_t2:
        st.markdown("📝 **'Other' Department Submissions**")
        other_dept = df[df['Department'].str.contains('Any other', na=False, case=False)]
        other_counts = other_dept['Other Dept. Name'].value_counts().reset_index()
        other_counts.columns = ['Manually Entered Department', 'Count']
        st.dataframe(other_counts, use_container_width=True)
        
    st.divider()
    
    st.markdown("🔍 **Grievance Keyword Search**")
    search_term = st.text_input("Filter grievances by specific text (e.g., 'streetlight', 'water'):")
    if search_term:
        theme_df = df[df['Grievance Details'].str.contains(search_term, na=False, case=False)]
        st.write(f"Found **{len(theme_df)}** records mentioning '{search_term}'")
        st.dataframe(theme_df[['District', 'Venue / Bazaar', 'Department', 'Grievance Details', 'Resolution Status']], use_container_width=True)

# -----------------------------------------------------------------------------
# 4. FOOTER
# -----------------------------------------------------------------------------
st.markdown('<div class="minute-footer">made with ❤️ by Jay Joshi</div>', unsafe_allow_html=True)

# ================================================================================================================================
# import streamlit as st
# import pandas as pd
# import plotly.express as px

# # --- PAGE CONFIG ---
# st.set_page_config(page_title="PSTC Grievance Dashboard", layout="wide")
# st.title("Punjab State Traders Commission - Grievance Dashboard")

# # --- LIVE DATA LOADING FROM GOOGLE SHEETS ---
# @st.cache_data(ttl=600)  
# def load_data():
#     sheet_id = "1rGwwRllkS30zA6ieOWvGOkSZUWy4BB9ZyGg64VRosUA"
#     sheet_name = "DATABASE FOR DASHBOARD"
#     safe_sheet_name = sheet_name.replace(" ", "%20")
    
#     url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={safe_sheet_name}"
    
#     try:
#         # Load without relying solely on parse_dates
#         df = pd.read_csv(url)
#         df.replace(['Nill', 'NILL', 'nill', 'Nil', 'nil'], pd.NA, inplace=True)
        
#         # FIX: Force the column to be datetime. 
#         # errors='coerce' turns any unreadable text/blanks into NaT (Not a Time) instead of crashing.
#         df['Meeting Date'] = pd.to_datetime(df['Meeting Date'], errors='coerce', dayfirst=True)
        
#         return df
#     except Exception as e:
#         st.error(f"Failed to load data from Google Sheets. Error: {e}")
#         return pd.DataFrame()

# df = load_data()

# if df.empty:
#     st.warning("No data found. Please make sure the 'DATABASE FOR DASHBOARD' sheet exists and has data.")
#     st.stop()

# # Create a unique meeting identifier based strictly on provided geography and date columns
# df['Meeting_ID'] = df['District'].astype(str) + "_" + \
#                    df['Halqa'].astype(str) + "_" + \
#                    df['Venue / Bazaar'].astype(str) + "_" + \
#                    df['Meeting Date'].astype(str)

# # --- DASHBOARD TABS ---
# tab1, tab2, tab3 = st.tabs(["Apex View (State)", "Meso View (District)", "Micro View (Actionable)"])

# # ==========================================
# # TIER 1: THE APEX VIEW (STATE-LEVEL)
# # ==========================================
# with tab1:
#     st.header("State-Level Strategy & Overview")
    
#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         st.metric("Total Grievances", len(df))
#     with col2:
#         st.metric("Districts Covered", df['District'].nunique())
#     with col3:
#         st.metric("Total Meetings Held", df['Meeting_ID'].nunique())
#     with col4:
#         st.metric("Citizens Engaged", df['Mobile No.'].nunique())
        
#     st.divider()
    
#     col_chart1, col_chart2 = st.columns(2)
    
#     with col_chart1:
#         st.subheader("State-Wide Resolution Rate")
#         res_counts = df['Resolution Status'].value_counts().reset_index()
#         res_counts.columns = ['Status', 'Count']
#         fig_pie = px.pie(res_counts, values='Count', names='Status', hole=0.4, 
#                          color='Status', color_discrete_map={'Resolved':'#2ca02c', 'Pending':'#d62728'})
#         st.plotly_chart(fig_pie, use_container_width=True)

#     with col_chart2:
#         st.subheader("Grievances by Department")
#         dept_counts = df['Department'].value_counts().reset_index()
#         dept_counts.columns = ['Department', 'Count']
#         fig_dept = px.bar(dept_counts, x='Count', y='Department', orientation='h')
#         fig_dept.update_layout(yaxis={'categoryorder':'total ascending'})
#         st.plotly_chart(fig_dept, use_container_width=True)

#     st.subheader("Pace of Operations (Grievances Collected Over Time)")
#     time_df = df.groupby('Meeting Date').size().reset_index(name='Grievances Collected')
#     fig_time = px.line(time_df, x='Meeting Date', y='Grievances Collected', markers=True)
#     st.plotly_chart(fig_time, use_container_width=True)

# # ==========================================
# # TIER 2: THE MESO VIEW (DISTRICT/OPERATIONAL)
# # ==========================================
# with tab2:
#     st.header("District & Operational Diagnostics")
    
#     st.subheader("District Scorecard")
#     dist_stats = df.groupby('District').agg(
#         Total_Grievances=('Sr.No', 'count'),
#         Pending=('Resolution Status', lambda x: (x == 'Pending').sum()),
#         Resolved=('Resolution Status', lambda x: (x == 'Resolved').sum())
#     ).reset_index()
    
#     # Handle division by zero safely
#     dist_stats['Resolution Rate (%)'] = (dist_stats['Resolved'] / dist_stats['Total_Grievances'] * 100).fillna(0).round(1)
#     st.dataframe(dist_stats.sort_values('Total_Grievances', ascending=False), use_container_width=True)

#     st.divider()

#     col_m1, col_m2 = st.columns(2)
    
#     with col_m1:
#         st.subheader("Venue & Bazaar Hotspots")
#         selected_district = st.selectbox("Select District to Drill Down:", df['District'].unique())
#         venue_df = df[df['District'] == selected_district]['Venue / Bazaar'].value_counts().reset_index()
#         venue_df.columns = ['Venue', 'Grievances']
#         fig_venue = px.bar(venue_df, x='Venue', y='Grievances', title=f"Grievance Volume by Venue in {selected_district}")
#         st.plotly_chart(fig_venue, use_container_width=True)
        
#     with col_m2:
#         st.subheader("Meeting Efficiency")
#         meeting_eff = df.groupby(['District', 'Meeting_ID']).size().reset_index(name='Grievance Count')
#         fig_eff = px.box(meeting_eff, x='District', y='Grievance Count', title="Distribution of Grievances per Meeting")
#         st.plotly_chart(fig_eff, use_container_width=True)

# # ==========================================
# # TIER 3: THE MICRO VIEW (GRANULAR/ACTIONABLE)
# # ==========================================
# with tab3:
#     st.header("Granular & Actionable Insights")
    
#     st.subheader("30-Day Resolution Countdown (Pending Grievances)")
    
#     # Get all pending (or blank) statuses
#     pending_df = df.copy()
#     pending_df['Resolution Status'] = pending_df['Resolution Status'].fillna('Pending')
    
#     # Now filter for Pending
#     pending_df = pending_df[pending_df['Resolution Status'].str.contains('Pending', case=False, na=False)].copy()
    
#     # Calculate days old AND Days Remaining (30-day SLA)
#     pending_df['Days Since Meeting'] = (pd.Timestamp.now().normalize() - pending_df['Meeting Date']).dt.days
#     pending_df['Days Remaining'] = 30 - pending_df['Days Since Meeting']
    
#     # Sort so the most urgent (lowest or negative days remaining) appear at the absolute top
#     pending_df = pending_df.sort_values('Days Remaining', ascending=True)
    
#     # Define the columns we want to show
#     display_cols = ['District', 'Name of Person', 'Mobile No.', 'Department', 'Meeting Date', 'Days Remaining', 'Grievance Details']
    
#     # Filter widget to toggle between All Pending and strictly Overdue
#     filter_option = st.radio("Filter List:", ["All Pending", "Overdue (0 or fewer days remaining)"], horizontal=True)
    
#     if filter_option == "Overdue (0 or fewer days remaining)":
#         display_df = pending_df[pending_df['Days Remaining'] <= 0]
#     else:
#         display_df = pending_df

#     st.dataframe(display_df[display_cols], use_container_width=True)

#     st.divider()
    
#     col_t1, col_t2 = st.columns(2)
    
#     with col_t1:
#         st.subheader("Frequent Complainants")
#         freq_comp = df.dropna(subset=['Mobile No.'])['Mobile No.'].value_counts().reset_index()
#         freq_comp.columns = ['Mobile No.', 'Total Grievances Logged']
#         freq_comp = freq_comp[freq_comp['Total Grievances Logged'] > 1]
        
#         freq_names = pd.merge(freq_comp, df[['Mobile No.', 'Name of Person']].drop_duplicates('Mobile No.'), on='Mobile No.', how='left')
#         st.dataframe(freq_names, use_container_width=True)

#     with col_t2:
#         st.subheader("'Other' Department Submissions")
#         other_dept = df[df['Department'].str.contains('Any other', na=False, case=False)]
#         other_counts = other_dept['Other Dept. Name'].value_counts().reset_index()
#         other_counts.columns = ['Manually Entered Department', 'Count']
#         st.dataframe(other_counts, use_container_width=True)
        
#     st.subheader("Grievance Keyword Search")
#     search_term = st.text_input("Filter grievances by specific text (e.g., 'streetlight', 'water'):")
#     if search_term:
#         theme_df = df[df['Grievance Details'].str.contains(search_term, na=False, case=False)]
#         st.write(f"Found **{len(theme_df)}** records mentioning '{search_term}'")
#         st.dataframe(theme_df[['District', 'Venue / Bazaar', 'Department', 'Grievance Details', 'Resolution Status']], use_container_width=True)

