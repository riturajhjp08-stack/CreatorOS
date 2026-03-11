import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from io import StringIO

# --- Page Config ---
st.set_page_config(
    page_title="Business Insight Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Theme Toggle ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# --- Home description & CSS (Canva-inspired with Light & Dark themes) ---
st.markdown("""
<div style="
background: linear-gradient(135deg, #2b6cb0 0%, #2c5282 100%);
text-align: center;
padding: 2rem 1rem;
border-radius: 20px;
margin-bottom: 1.5rem;
box-shadow: 0 10px 30px rgba(43, 108, 176, 0.2);
">
  <h1 style="margin: 0; color: white; font-size: 2rem; font-weight: 700;">📊 Insights Dashboard</h1>
</div>
""", unsafe_allow_html=True)

# Light Theme CSS
light_theme_css = """
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
    }
    
    .canva-metric-card:hover {
        transform: scale(1.02);
        box-shadow: var(--shadow-hover);
    }
    
    .canva-metric-card .metric-label {
        font-size: 0.875rem;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 8px;
    }
    
    .canva-metric-card .metric-value {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    
    /* Sidebar Styling */
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important;
        border-right: 1px solid var(--border) !important;
        padding: 24px 16px !important;
    }
    
    div[data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }
    
    div[data-testid="stSidebar"] h1, div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        margin-bottom: 16px !important;
    }
    
    div[data-testid="stSidebar"] .stRadio > label {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        margin-bottom: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="stSidebar"] .stRadio > label:hover {
        background: var(--gradient-primary) !important;
        color: white !important;
        border-color: transparent !important;
    }
    
    /* Form Elements */
    [data-testid="stSelectbox"], [data-testid="stMultiSelect"], [data-testid="stRadio"],
    [data-testid="stSlider"], [data-testid="stTextArea"] {
        padding: 12px 16px !important;
        border-radius: 12px !important;
        border: 2px solid var(--border) !important;
        background: var(--bg-main) !important;
        color: var(--text-primary) !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stSelectbox"]:focus, [data-testid="stMultiSelect"]:focus,
    [data-testid="stTextArea"]:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: var(--primary) !important;
        color: white !important;
        border: 1px solid var(--secondary) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        box-shadow: none !important;
        transition: background 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: var(--secondary) !important;
    }
    
    /* Expanders */
    .stExpander {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
        box-shadow: var(--shadow) !important;
        margin-bottom: 16px !important;
    }
    
    .stExpander > div:first-child {
        background: var(--gradient-secondary) !important;
        color: white !important;
        border-radius: 12px 12px 0 0 !important;
        font-weight: 600 !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
        box-shadow: var(--shadow) !important;
    }
    
    /* Plotly Charts */
    .js-plotly-plot {
        border-radius: 12px !important;
        box-shadow: var(--shadow) !important;
        background: var(--bg-card) !important;
    }
    
    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        margin-bottom: 16px !important;
    }
    
    h1 { font-size: 2.5rem !important; }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.5rem !important; }
    h4 { font-size: 1.25rem !important; }
    
    /* Theme Toggle Buttons */
    .theme-toggle-btn {
        background: var(--bg-card) !important;
        border: 2px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        text-align: center !important;
    }
    
    .theme-toggle-btn:hover {
        border-color: var(--primary) !important;
        background: rgba(124, 58, 237, 0.05) !important;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem !important;
        }
        
        .canva-metrics-grid {
            grid-template-columns: 1fr !important;
        }
        
        h1 { font-size: 2rem !important; }
        h2 { font-size: 1.5rem !important; }
    }
</style>
"""

# Dark Theme CSS
dark_theme_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');
    
    :root {
        --primary: #a78bfa;
        --secondary: #f472b6;
        --accent: #22d3ee;
        --bg-main: #1e293b;
        --bg-secondary: #0f172a;
        --bg-card: #334155;
        --text-primary: #f8fafc;
        --text-secondary: #cbd5e1;
        --text-muted: #94a3b8;
        --border: #475569;
        --border-light: #334155;
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
        --shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
        --gradient-primary: var(--primary);
        --gradient-secondary: var(--secondary);
        --gradient-accent: var(--accent);
    }
    
    * {
        font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
    }
    
    body {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        line-height: 1.6;
    }
    
    .block-container {
        padding: 2rem 3rem !important;
        max-width: 1400px !important;
    }
    
    /* Card Components */
    .canva-card {
        background: var(--bg-card);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: var(--shadow);
        border: 1px solid var(--border-light);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .canva-card:hover {
        box-shadow: var(--shadow-hover);
        transform: translateY(-2px);
    }
    
    .canva-card-header {
        background: var(--gradient-primary);
        color: white;
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        text-align: center;
        box-shadow: var(--shadow);
    }
    
    .canva-card-header h3 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    .canva-metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }
    
    .canva-metric-card {
        background: var(--gradient-primary);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
    }
    
    .canva-metric-card:hover {
        transform: scale(1.02);
        box-shadow: var(--shadow-hover);
    }
    
    .canva-metric-card .metric-label {
        font-size: 0.875rem;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 8px;
    }
    
    .canva-metric-card .metric-value {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    
    /* Sidebar Styling */
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid var(--border) !important;
        padding: 24px 16px !important;
    }
    
    div[data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
    }
    
    div[data-testid="stSidebar"] h1, div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        margin-bottom: 16px !important;
    }
    
    div[data-testid="stSidebar"] .stRadio > label {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        margin-bottom: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="stSidebar"] .stRadio > label:hover {
        background: var(--gradient-primary) !important;
        color: white !important;
        border-color: transparent !important;
    }
    
    /* Form Elements */
    [data-testid="stSelectbox"], [data-testid="stMultiSelect"], [data-testid="stRadio"],
    [data-testid="stSlider"], [data-testid="stTextArea"] {
        padding: 12px 16px !important;
        border-radius: 12px !important;
        border: 2px solid var(--border) !important;
        background: var(--bg-main) !important;
        color: var(--text-primary) !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stSelectbox"]:focus, [data-testid="stMultiSelect"]:focus,
    [data-testid="stTextArea"]:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: var(--primary) !important;
        color: white !important;
        border: 1px solid var(--secondary) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        box-shadow: none !important;
        transition: background 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: var(--secondary) !important;
    }
    
    /* Expanders */
    .stExpander {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
        box-shadow: var(--shadow) !important;
        margin-bottom: 16px !important;
    }
    
    .stExpander > div:first-child {
        background: var(--gradient-secondary) !important;
        color: white !important;
        border-radius: 12px 12px 0 0 !important;
        font-weight: 600 !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
        box-shadow: var(--shadow) !important;
    }
    
    /* Plotly Charts */
    .js-plotly-plot {
        border-radius: 12px !important;
        box-shadow: var(--shadow) !important;
        background: var(--bg-card) !important;
    }
    
    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        margin-bottom: 16px !important;
    }
    
    h1 { font-size: 2.5rem !important; }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.5rem !important; }
    h4 { font-size: 1.25rem !important; }
    
    /* Theme Toggle Buttons */
    .theme-toggle-btn {
        background: var(--bg-card) !important;
        border: 2px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        text-align: center !important;
    }
    
    .theme-toggle-btn:hover {
        border-color: var(--primary) !important;
        background: rgba(167, 139, 250, 0.1) !important;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem !important;
        }
        
        .canva-metrics-grid {
            grid-template-columns: 1fr !important;
        }
        
        h1 { font-size: 2rem !important; }
        h2 { font-size: 1.5rem !important; }
    }
</style>
"""

# Apply selected theme
if st.session_state.theme == 'light':
    st.markdown(light_theme_css, unsafe_allow_html=True)
else:
    st.markdown(dark_theme_css, unsafe_allow_html=True)

# --- Enhanced Canva-style Background ---
st.markdown("""
<style>
    body {
        background: linear-gradient(135deg, #f0f4ff 0%, #e0f2fe 50%, #fce7f3 100%) !important;
        min-height: 100vh !important;
    }
    
    .block-container {
        background: rgba(255, 255, 255, 0.85) !important;
        border-radius: 24px !important;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12) !important;
        backdrop-filter: blur(12px) !important;
        margin: 2rem auto !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    
    /* Enhanced card styling */
    .canva-card {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08) !important;
    }
    
    .canva-card:hover {
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.12) !important;
        transform: translateY(-3px) !important;
    }
    
    /* Enhanced sidebar */
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.95) 100%) !important;
        backdrop-filter: blur(10px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    
    /* Buttons kept simple for professionalism; no extra animation */
    .stButton > button {
        background: var(--primary) !important;
        color: white !important;
        border: 1px solid var(--secondary) !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: background 0.2s ease !important;
    }
    .stButton > button:hover {
        background: var(--secondary) !important;
    }
    
    /* Enhanced form elements */
    [data-testid="stSelectbox"], [data-testid="stMultiSelect"] {
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stSelectbox"]:hover, [data-testid="stMultiSelect"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    
    /* Loading animation for cards */
    .canva-card {
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Enhanced metric cards */
    .canva-metric-card {
        animation: slideInScale 0.5s ease-out;
        animation-fill-mode: both;
    }
    
    .canva-metric-card:nth-child(1) { animation-delay: 0.1s; }
    .canva-metric-card:nth-child(2) { animation-delay: 0.2s; }
    .canva-metric-card:nth-child(3) { animation-delay: 0.3s; }
    .canva-metric-card:nth-child(4) { animation-delay: 0.4s; }
    .canva-metric-card:nth-child(5) { animation-delay: 0.5s; }
    
    @keyframes slideInScale {
        from {
            opacity: 0;
            transform: scale(0.9) translateY(10px);
        }
        to {
            opacity: 1;
            transform: scale(1) translateY(0);
        }
    }
</style>
""", unsafe_allow_html=True)

# --- Load Data ---
@st.cache_data
# Make the loader flexible: either use the built-in sample file or accept an uploaded CSV
# Returns a cleaned DataFrame with parsed dates and additional columns used by the dashboard.
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        try:
            # streamlit provides a BytesIO-like object
            df = pd.read_csv(uploaded_file, encoding='latin1')
        except Exception:
            st.error("Could not read the uploaded file. Please make sure it's a valid CSV with the same structure as the sample.")
            return pd.DataFrame()
    else:
        df = pd.read_csv('Sample - Superstore.csv', encoding='latin1')

    # Ensure expected columns exist before converting datatypes
    for col in ['Order Date', 'Ship Date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    if 'Order Date' in df.columns:
        df['Year'] = df['Order Date'].dt.year
        df['Month'] = df['Order Date'].dt.to_period('M').astype(str)
    return df

# allow the user to upload their own dataset; falls back to sample
uploaded = st.sidebar.file_uploader("Upload CSV (optional)", type=["csv"])
df = load_data(uploaded)

if df.empty:
    st.error("No data available. Please upload a valid CSV or check the sample file.")
    st.stop()

# Ensure essential columns exist before proceeding. We prefer Sales/Profit/Order ID
required = ['Sales', 'Profit', 'Order ID']
missing = [c for c in required if c not in df.columns]
generic_mode = False
column_mapping = {}
if missing:
    st.warning(f"Dataset is missing preferred columns: {', '.join(missing)}.")
    st.markdown("#### Map your columns to the dashboard (optional)")
    # let user map their columns to the expected names
    cols_options = ["(none)"] + df.columns.tolist()
    for req in required:
        if req in df.columns:
            # already present, no mapping needed
            column_mapping[req] = req
        else:
            sel = st.selectbox(f"Map '{req}' to", options=cols_options, key=f"map_{req}")
            if sel and sel != "(none)":
                column_mapping[req] = sel

    # if the user mapped all required fields, create/alias them and use specialised dashboard
    if all(k in column_mapping for k in required):
        for req, colname in column_mapping.items():
            # copy or rename the column into the expected name
            try:
                df[req] = df[colname]
            except Exception:
                # if assignment fails, leave as-is and fall back to generic
                st.warning(f"Could not map {colname} to {req} - will use generic explorer.")
                generic_mode = True
                break
        else:
            st.success("All required fields mapped — switching to specialised dashboard.")
            generic_mode = False
    else:
        st.info("Not all required fields mapped — continuing in generic explorer mode.")
        generic_mode = True

# --- Sidebar Filters & Instructions ---
with st.sidebar:
    st.markdown("""
    <div style="
        background: #2d3748;
        color: white;
        padding: 16px 12px;
        border-radius: 12px;
        margin-bottom: 16px;
        text-align: center;
    ">
        <h2 style="margin: 0; font-size: 1.3rem; font-weight: 600;">Controls</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("Usage help", expanded=False):
        st.markdown(
            """
            • Upload CSV or use sample.
            • Apply filters and select view.
            • Overview is a good start.
            """
        )
    st.markdown("---")
    
    # Theme Toggle
    st.markdown("#### 🎨 Theme Selection")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("☀️ Light", use_container_width=True, key="light_btn"):
            st.session_state.theme = 'light'
            st.rerun()
    with col2:
        if st.button("🌙 Dark", use_container_width=True, key="dark_btn"):
            st.session_state.theme = 'dark'
            st.rerun()
    
    st.markdown("---")
    
    if generic_mode:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #f472b6 0%, #fb7185 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 16px;
            text-align: center;
        ">
            <h4 style="margin: 0; font-size: 1.1rem;">🔧 Generic Filters</h4>
        </div>
        """, unsafe_allow_html=True)
        # allow the user to pick a column to filter on and values for that column
        filter_col = st.selectbox("Pick a column to filter (optional)", options=[""] + df.columns.tolist())
        selected_values = []
        if filter_col and filter_col in df.columns:
            unique = sorted(df[filter_col].dropna().unique().tolist())
            selected_values = st.multiselect(f"Values for {filter_col}", options=unique)
        # store generic filter choices for later use
        generic_filter = (filter_col, selected_values)

        # still allow choosing a view, though it will be ignored in generic mode
        view_option = st.radio("📊 Choose a view", options=["Overview"])
    else:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 16px;
            text-align: center;
        ">
            <h4 style="margin: 0; font-size: 1.1rem;">🎛️ Data Filters</h4>
        </div>
        """, unsafe_allow_html=True)

    # use multiselect so beginners can select multiple or keep "All" automatically
    # Some uploaded files might not have these columns; handle missing keys gracefully.
    if 'Year' in df.columns:
        years = sorted(df['Year'].dropna().unique().tolist())
    else:
        years = []
        st.warning("Dataset does not contain a 'Year' column; year filtering will be skipped.")
    selected_year = st.multiselect(
        "📅 Year (pick one or more, blank = all)",
        options=years,
        default=years if len(years) <= 3 else []
    )

    if 'Region' in df.columns:
        regions = sorted(df['Region'].dropna().unique().tolist())
    else:
        regions = []
        st.warning("Dataset does not contain a 'Region' column; region filtering will be skipped.")
    selected_region = st.multiselect(
        "🌍 Region (pick one or more)",
        options=regions,
    )

    if 'Category' in df.columns:
        categories = sorted(df['Category'].dropna().unique().tolist())
    else:
        categories = []
        st.warning("Dataset does not contain a 'Category' column; category filtering will be skipped.")
    selected_category = st.multiselect(
        "📦 Category (pick one or more)",
        options=categories,
    )

    if 'Segment' in df.columns:
        segments = sorted(df['Segment'].dropna().unique().tolist())
    else:
        segments = []
        st.warning("Dataset does not contain a 'Segment' column; segment filtering will be skipped.")
    selected_segment = st.multiselect(
        "👥 Segment (pick one or more)",
        options=segments,
    )

    st.markdown("---")
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 16px;
        text-align: center;
    ">
        <h4 style="margin: 0; font-size: 1.1rem;">📊 Dashboard Views</h4>
    </div>
    """, unsafe_allow_html=True)

    view_option = st.radio(
        "Choose your analysis view:",  # radio makes it easier to see all options
        options=[
            "Overview",
            "Top Products",
            "Sales Trends",
            "Profit Analysis",
            "Regional Breakdown",
        ],
        label_visibility="collapsed"
    )

    # feedback after view selector
    with st.sidebar.expander("💬 Feedback", expanded=False):
        with st.form("feedback_form", clear_on_submit=True):
            rating = st.slider("Rate this dashboard", 1, 5, 3)
            comments = st.text_area("Comments (optional)")
            submitted = st.form_submit_button("Submit")
            if submitted:
                try:
                    import datetime
                    fb = pd.DataFrame([{"timestamp": datetime.datetime.now(),
                                        "rating": rating,
                                        "comments": comments}])
                    fb.to_csv("feedback.csv", mode="a", header=not pd.io.common.file_exists("feedback.csv"), index=False)
                    st.success("Thanks for your feedback!")
                except Exception:
                    st.error("Could not save feedback.")

# --- Apply Filters ---
filtered = df.copy()
if generic_mode:
    # apply simple generic filter if requested
    col, vals = generic_filter
    if col and vals:
        filtered = filtered[filtered[col].isin(vals)]
else:
    # each selection is a list; if it's non-empty, keep only those values,
    # but only if the underlying column exists in the dataframe.
    if selected_year and 'Year' in filtered.columns:
        filtered = filtered[filtered['Year'].isin(selected_year)]
    if selected_region and 'Region' in filtered.columns:
        filtered = filtered[filtered['Region'].isin(selected_region)]
    if selected_category and 'Category' in filtered.columns:
        filtered = filtered[filtered['Category'].isin(selected_category)]
    if selected_segment and 'Segment' in filtered.columns:
        filtered = filtered[filtered['Segment'].isin(selected_segment)]

# warn if no rows after filtering
if filtered.empty:
    st.warning("No records match the selected filters. Please adjust the year/region/category/segment selections or upload a different dataset.")

# if generic_mode, provide a friendly, visual explorer and stop
if generic_mode:
    st.markdown('<div class="canva-card-header"><h3>🔍 Dataset Explorer</h3></div>', unsafe_allow_html=True)
    
    # Basic KPIs (show product-focused metrics if a product-like column exists)
    n_rows, n_cols = filtered.shape
    num_cols = filtered.select_dtypes(include=['number']).columns.tolist()
    cat_cols = filtered.select_dtypes(exclude=['number']).columns.tolist()

    # detect a product-like column
    prod_col = None
    for c in filtered.columns:
        cl = c.lower()
        if any(k in cl for k in ['product', 'item', 'sku']):
            prod_col = c
            break

    # Metrics in card grid
    st.markdown('<div class="canva-metrics-grid">', unsafe_allow_html=True)
    if prod_col:
        # product-focused KPIs
        prod_count = int(filtered[prod_col].nunique())
        try:
            top_prod = filtered[prod_col].mode(dropna=True)[0]
        except Exception:
            top_prod = "-"
        st.markdown(f'''
            <div class="canva-metric-card">
                <div class="metric-label">Unique products</div>
                <div class="metric-value">{prod_count}</div>
            </div>
            <div class="canva-metric-card">
                <div class="metric-label">Top product</div>
                <div class="metric-value">{top_prod}</div>
            </div>
            <div class="canva-metric-card">
                <div class="metric-label">Rows</div>
                <div class="metric-value">{n_rows:,}</div>
            </div>
            <div class="canva-metric-card">
                <div class="metric-label">Columns</div>
                <div class="metric-value">{n_cols}</div>
            </div>
        ''', unsafe_allow_html=True)
    else:
        # generic KPIs
        st.markdown(f'''
            <div class="canva-metric-card">
                <div class="metric-label">Rows</div>
                <div class="metric-value">{n_rows:,}</div>
            </div>
            <div class="canva-metric-card">
                <div class="metric-label">Columns</div>
                <div class="metric-value">{n_cols}</div>
            </div>
            <div class="canva-metric-card">
                <div class="metric-label">Numeric fields</div>
                <div class="metric-value">{len(num_cols)}</div>
            </div>
            <div class="canva-metric-card">
                <div class="metric-label">Categorical fields</div>
                <div class="metric-value">{len(cat_cols)}</div>
            </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Sample data in card
    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📋 Sample Data Preview</h4>', unsafe_allow_html=True)
    st.dataframe(filtered.head(8))
    st.markdown('</div>', unsafe_allow_html=True)

    # Color palette for charts
    palette = ['#667eea', '#764ba2', '#f093fb', '#a8edea', '#ffb86b']

    # Show histograms for up to 3 numeric columns (most informative)
    if num_cols:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📊 Numeric Distributions</h4>', unsafe_allow_html=True)
        # pick up to 3 numeric cols with most non-null values
        sorted_num = sorted(num_cols, key=lambda c: filtered[c].count(), reverse=True)[:3]
        for col in sorted_num:
            fig = px.histogram(filtered, x=col, nbins=30, title=f"Distribution of {col}", color_discrete_sequence=[palette[0]])
            fig.update_layout(template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No numeric columns found to show distributions.")

    # Show bar/pie charts for up to 3 categorical columns
    if cat_cols:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📈 Top Categories</h4>', unsafe_allow_html=True)
        # choose categorical columns that have reasonable cardinality (not too many distinct)
        cand = [c for c in cat_cols if filtered[c].nunique() <= 20]
        cand = cand[:3]
        for col in cand:
            df_top = filtered[col].fillna("(missing)").value_counts().reset_index()
            df_top.columns = [col, 'count']
            # bar chart
            fig_bar = px.bar(df_top.head(10), x='count', y=col, orientation='h', title=f'Top values in {col}', color_discrete_sequence=palette)
            fig_bar.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'})
            st.plotly_chart(fig_bar, use_container_width=True)
            # pie chart of top 6
            fig_pie = px.pie(df_top.head(6), values='count', names=col, title=f'{col} composition (top 6)', color_discrete_sequence=palette)
            fig_pie.update_layout(template='plotly_white')
            st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No categorical columns found to show category breakdowns.")

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.caption('💡 Tip: Upload a dataset with numeric columns for histograms and categorical columns with limited unique values for bars and pies.')
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# allow user to download the current filtered data
try:
    csv = filtered.to_csv(index=False)
    st.download_button("📥 Download filtered data", data=csv, file_name="filtered_data.csv", mime="text/csv")
except Exception:
    # filtered may not exist yet if upload failed
    pass

# provide an expandable raw table for beginners who want to peek at the rows
with st.expander("🔍 View raw data (filtered)", expanded=False):
    st.dataframe(filtered)


# ======================= OVERVIEW =======================
if view_option == "Overview":
    st.markdown('<div class="canva-card-header"><h3>📊 Overview Dashboard</h3></div>', unsafe_allow_html=True)
    
    if 'Sales' not in filtered.columns:
        st.error("Cannot display overview: 'Sales' column missing.")
    else:
        total_sales = filtered['Sales'].sum() if 'Sales' in filtered.columns else 0
        total_profit = filtered['Profit'].sum() if 'Profit' in filtered.columns else 0
        total_orders = filtered['Order ID'].nunique() if 'Order ID' in filtered.columns else len(filtered)
        avg_discount = (filtered['Discount'].mean() * 100) if 'Discount' in filtered.columns else None
        profit_margin = (total_profit / total_sales * 100) if total_sales else 0

    # Metrics in card grid
    st.markdown('<div class="canva-metrics-grid">', unsafe_allow_html=True)
    st.markdown(f'''
        <div class="canva-metric-card">
            <div class="metric-label">Total Sales</div>
            <div class="metric-value">${total_sales:,.0f}</div>
        </div>
        <div class="canva-metric-card">
            <div class="metric-label">Total Profit</div>
            <div class="metric-value">${total_profit:,.0f}</div>
        </div>
        <div class="canva-metric-card">
            <div class="metric-label">Orders</div>
            <div class="metric-value">{total_orders:,}</div>
        </div>
        <div class="canva-metric-card">
            <div class="metric-label">Profit Margin</div>
            <div class="metric-value">{profit_margin:.1f}%</div>
        </div>
        <div class="canva-metric-card" style="grid-column: span 1;">
            <div class="metric-label">Avg Discount</div>
            <div class="metric-value">{f"{avg_discount:.1f}%" if avg_discount is not None else "N/A"}</div>
        </div>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Charts in cards
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📈 Sales & Profit by Category</h4>', unsafe_allow_html=True)
        if 'Category' in filtered.columns:
            cat_sales = filtered.groupby('Category')[['Sales', 'Profit']].sum().reset_index()
            fig = px.bar(
                cat_sales, x='Category', y=['Sales', 'Profit'],
                barmode='group', title='',
                color_discrete_sequence=['#667eea', '#764ba2'],
            )
            fig.update_layout(template='plotly_white', legend_title_text='', height=400, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Category column not available; skipping category breakdown.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">🥧 Sales by Segment</h4>', unsafe_allow_html=True)
        if 'Segment' in filtered.columns:
            seg_sales = filtered.groupby('Segment')['Sales'].sum().reset_index()
            fig = px.pie(
                seg_sales, values='Sales', names='Segment',
                title='',
                color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
                hole=0.4,
            )
            fig.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Segment column not available; skipping segment distribution.")
        st.markdown('</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📊 Sales & Profit by Region</h4>', unsafe_allow_html=True)
        if 'Region' in filtered.columns:
            region_data = filtered.groupby('Region')[['Sales', 'Profit']].sum().reset_index()
            fig = px.bar(
                region_data, x='Region', y=['Sales', 'Profit'],
                barmode='group', title='',
                color_discrete_sequence=['#667eea', '#764ba2'],
            )
            fig.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Region column not available; skipping regional breakdown.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">🚚 Sales by Ship Mode</h4>', unsafe_allow_html=True)
        if 'Ship Mode' in filtered.columns:
            ship_data = filtered.groupby('Ship Mode')['Sales'].sum().reset_index()
            fig = px.pie(
                ship_data, values='Sales', names='Ship Mode',
                title='',
                color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#a8edea'],
                hole=0.4,
            )
            fig.update_layout(template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ship Mode column not available; skipping shipping analysis.")
        st.markdown('</div>', unsafe_allow_html=True)


# ======================= TOP PRODUCTS =======================
elif view_option == "Top Products":
    st.markdown('<div class="canva-card-header"><h3>🏆 Top Products Analysis</h3></div>', unsafe_allow_html=True)
    
    # require Sales and Profit columns
    if 'Sales' not in filtered.columns:
        st.error("Cannot show top products: 'Sales' column missing.")
    else:
        n = st.slider("Number of products to display", 5, 20, 10)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown(f'<h4 style="text-align: center; margin-bottom: 20px;">💰 Top {n} Products by Sales</h4>', unsafe_allow_html=True)
        top_sales = (
            filtered.groupby('Product Name')['Sales'].sum()
            .sort_values(ascending=False).head(n).reset_index()
        )
        fig = px.bar(
            top_sales, x='Sales', y='Product Name',
            orientation='h', title='',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown(f'<h4 style="text-align: center; margin-bottom: 20px;">📈 Top {n} Products by Profit</h4>', unsafe_allow_html=True)
        top_profit = (
            filtered.groupby('Product Name')['Profit'].sum()
            .sort_values(ascending=False).head(n).reset_index()
        )
        fig = px.bar(
            top_profit, x='Profit', y='Product Name',
            orientation='h', title='',
            color='Profit', color_continuous_scale='Greens',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📊 Sub-Category Performance</h4>', unsafe_allow_html=True)
    subcat = filtered.groupby('Sub-Category')[['Sales', 'Profit']].sum().reset_index()
    subcat = subcat.sort_values('Sales', ascending=False)
    fig = px.bar(
        subcat, x='Sub-Category', y=['Sales', 'Profit'],
        barmode='group', title='',
        color_discrete_sequence=['#667eea', '#764ba2'],
    )
    fig.update_layout(template='plotly_white', height=450, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ======================= SALES TRENDS =======================
elif view_option == "Sales Trends":
    st.markdown('<div class="canva-card-header"><h3>📈 Sales Trends Over Time</h3></div>', unsafe_allow_html=True)
    
    if 'Order Date' not in filtered.columns or 'Sales' not in filtered.columns:
        st.error("Cannot show sales trends: 'Order Date' or 'Sales' column missing.")
    else:
        monthly = filtered.set_index('Order Date').resample('M')[['Sales', 'Profit']].sum().reset_index()

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📊 Monthly Sales & Profit Trend</h4>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly['Order Date'], y=monthly['Sales'],
        mode='lines+markers', name='Sales',
        line=dict(color='#667eea', width=2.5),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=monthly['Order Date'], y=monthly['Profit'],
        mode='lines+markers', name='Profit',
        line=dict(color='#764ba2', width=2.5),
        marker=dict(size=5),
    ))
    fig.update_layout(
        title='',
        template='plotly_white', height=450,
        xaxis_title='Date', yaxis_title='Amount ($)',
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📅 Yearly Sales</h4>', unsafe_allow_html=True)
        yearly = filtered.set_index('Order Date').resample('Y')[['Sales']].sum().reset_index()
        yearly['Year'] = yearly['Order Date'].dt.year
        fig = px.bar(
            yearly, x='Year', y='Sales', title='',
            color='Sales', color_continuous_scale='Purples', text_auto=',.0f',
        )
        fig.update_layout(template='plotly_white', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">💰 Yearly Profit</h4>', unsafe_allow_html=True)
        yearly_p = filtered.set_index('Order Date').resample('Y')[['Profit']].sum().reset_index()
        yearly_p['Year'] = yearly_p['Order Date'].dt.year
        fig = px.bar(
            yearly_p, x='Year', y='Profit', title='',
            color='Profit', color_continuous_scale='Greens', text_auto=',.0f',
        )
        fig.update_layout(template='plotly_white', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📊 Quarterly Breakdown</h4>', unsafe_allow_html=True)
    quarterly = filtered.set_index('Order Date').resample('Q')[['Sales', 'Profit']].sum().reset_index()
    quarterly['Quarter'] = quarterly['Order Date'].dt.to_period('Q').astype(str)
    fig = px.bar(
        quarterly, x='Quarter', y=['Sales', 'Profit'],
        barmode='group', title='',
        color_discrete_sequence=['#667eea', '#764ba2'],
    )
    fig.update_layout(template='plotly_white', height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ======================= PROFIT ANALYSIS =======================
elif view_option == "Profit Analysis":
    st.markdown('<div class="canva-card-header"><h3>💰 Profit Analysis & Insights</h3></div>', unsafe_allow_html=True)
    
    if 'Profit' not in filtered.columns:
        st.error("Cannot show profit analysis: 'Profit' column missing.")
    else:
        col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📊 Sales vs Profit Scatter</h4>', unsafe_allow_html=True)
        fig = px.scatter(
            filtered, x='Sales', y='Profit', color='Category',
            title='',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
            opacity=0.6, hover_data=['Product Name'],
        )
        fig.update_layout(template='plotly_white', height=450)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">🎯 Discount vs Profit Impact</h4>', unsafe_allow_html=True)
        fig = px.scatter(
            filtered, x='Discount', y='Profit', color='Category',
            title='',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
            opacity=0.6,
        )
        fig.update_layout(template='plotly_white', height=450)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">⚠️ Top Loss-Making Products</h4>', unsafe_allow_html=True)
    loss_products = (
        filtered.groupby('Product Name')['Profit'].sum()
        .sort_values().head(10).reset_index()
    )
    fig = px.bar(
        loss_products, x='Profit', y='Product Name',
        orientation='h', title='',
        color='Profit', color_continuous_scale='Reds_r',
    )
    fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📈 Profit Margin by Sub-Category</h4>', unsafe_allow_html=True)
    subcat_pm = filtered.groupby('Sub-Category')[['Sales', 'Profit']].sum().reset_index()
    subcat_pm['Profit Margin %'] = (subcat_pm['Profit'] / subcat_pm['Sales'] * 100).round(1)
    subcat_pm = subcat_pm.sort_values('Profit Margin %', ascending=True)
    colors = ['#e74c3c' if v < 0 else '#667eea' for v in subcat_pm['Profit Margin %']]
    fig = go.Figure(go.Bar(
        x=subcat_pm['Profit Margin %'], y=subcat_pm['Sub-Category'],
        orientation='h', marker_color=colors,
        text=subcat_pm['Profit Margin %'].apply(lambda x: f'{x:.1f}%'),
        textposition='outside',
    ))
    fig.update_layout(
        title='',
        template='plotly_white', height=450,
        xaxis_title='Profit Margin %',
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ======================= REGIONAL BREAKDOWN =======================
elif view_option == "Regional Breakdown":
    st.markdown('<div class="canva-card-header"><h3>🌍 Regional Performance Analysis</h3></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: var(--text-secondary); margin-bottom: 24px;">Compare performance across regions, states, and cities. The data table below gives an exact summary.</p>', unsafe_allow_html=True)
    
    if 'Region' not in filtered.columns or 'Sales' not in filtered.columns:
        st.error("Cannot show regional breakdown: required columns missing.")
    else:
        region_summary = filtered.groupby('Region').agg(
        Sales=('Sales', 'sum'),
        Profit=('Profit', 'sum'),
        Orders=('Order ID', 'nunique'),
        Quantity=('Quantity', 'sum'),
    ).reset_index()

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📊 Sales & Profit by Region</h4>', unsafe_allow_html=True)
    fig = px.bar(
        region_summary, x='Region', y=['Sales', 'Profit'],
        barmode='group', title='',
        color_discrete_sequence=['#667eea', '#764ba2'],
        text_auto=',.0f',
    )
    fig.update_layout(template='plotly_white', height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">🏆 Top States by Sales</h4>', unsafe_allow_html=True)
        state_sales = filtered.groupby('State')['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(
            state_sales, x='Sales', y='State',
            orientation='h', title='',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="canva-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">🏙️ Top Cities by Sales</h4>', unsafe_allow_html=True)
        city_sales = filtered.groupby('City')['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(
            city_sales, x='Sales', y='City',
            orientation='h', title='',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="canva-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center; margin-bottom: 20px;">📋 Regional Details Summary</h4>', unsafe_allow_html=True)
    st.dataframe(
        region_summary.style.format({'Sales': '${:,.0f}', 'Profit': '${:,.0f}', 'Orders': '{:,}', 'Quantity': '{:,}'}),
        use_container_width=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
