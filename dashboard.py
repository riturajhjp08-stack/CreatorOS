import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --- Page Config ---
st.set_page_config(
    page_title="Superstore Sales Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px 20px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    [data-testid="stMetric"] label { color: rgba(255,255,255,0.85) !important; font-size: 0.85rem !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: white !important; font-size: 1.8rem !important; }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] { color: rgba(255,255,255,0.9) !important; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); }
    div[data-testid="stSidebar"] * { color: white !important; }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 1rem 0 0.5rem 0;
        text-align: center;
        white-space: nowrap;
    }
    .sub-header { font-size: 1rem; color: #888; margin-bottom: 1.5rem; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_csv('Sample - Superstore.csv', encoding='latin1')
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Ship Date'] = pd.to_datetime(df['Ship Date'])
    df['Year'] = df['Order Date'].dt.year
    df['Month'] = df['Order Date'].dt.to_period('M').astype(str)
    return df

df = load_data()

# --- Sidebar Filters ---
with st.sidebar:
    st.markdown("## 🎛️ Filters")
    st.markdown("---")

    selected_year = st.selectbox(
        "📅 Select Year",
        options=["All"] + sorted(df['Year'].unique().tolist()),
    )

    selected_region = st.selectbox(
        "🌍 Select Region",
        options=["All"] + sorted(df['Region'].unique().tolist()),
    )

    selected_category = st.selectbox(
        "📦 Select Category",
        options=["All"] + sorted(df['Category'].unique().tolist()),
    )

    selected_segment = st.selectbox(
        "👥 Select Segment",
        options=["All"] + sorted(df['Segment'].unique().tolist()),
    )

    st.markdown("---")

    view_option = st.selectbox(
        "📊 Dashboard View",
        options=[
            "Overview",
            "Top Products",
            "Sales Trends",
            "Profit Analysis",
            "Regional Breakdown",
        ],
    )

# --- Apply Filters ---
filtered = df.copy()
if selected_year != "All":
    filtered = filtered[filtered['Year'] == selected_year]
if selected_region != "All":
    filtered = filtered[filtered['Region'] == selected_region]
if selected_category != "All":
    filtered = filtered[filtered['Category'] == selected_category]
if selected_segment != "All":
    filtered = filtered[filtered['Segment'] == selected_segment]

# --- Header ---
st.markdown('<div class="main-header">Superstore Sales Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Interactive analytics for sales, profit & product performance</div>', unsafe_allow_html=True)


# ======================= OVERVIEW =======================
if view_option == "Overview":
    total_sales = filtered['Sales'].sum()
    total_profit = filtered['Profit'].sum()
    total_orders = filtered['Order ID'].nunique()
    avg_discount = filtered['Discount'].mean() * 100
    profit_margin = (total_profit / total_sales * 100) if total_sales else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Sales", f"${total_sales:,.0f}")
    c2.metric("Total Profit", f"${total_profit:,.0f}")
    c3.metric("Orders", f"{total_orders:,}")
    c4.metric("Profit Margin", f"{profit_margin:.1f}%")
    c5.metric("Avg Discount", f"{avg_discount:.1f}%")

    st.markdown("####")

    col1, col2 = st.columns(2)

    with col1:
        cat_sales = filtered.groupby('Category')[['Sales', 'Profit']].sum().reset_index()
        fig = px.bar(
            cat_sales, x='Category', y=['Sales', 'Profit'],
            barmode='group', title='Sales & Profit by Category',
            color_discrete_sequence=['#667eea', '#764ba2'],
        )
        fig.update_layout(template='plotly_white', legend_title_text='', height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        seg_sales = filtered.groupby('Segment')['Sales'].sum().reset_index()
        fig = px.pie(
            seg_sales, values='Sales', names='Segment',
            title='Sales Distribution by Segment',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
            hole=0.4,
        )
        fig.update_layout(template='plotly_white', height=400)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        region_data = filtered.groupby('Region')[['Sales', 'Profit']].sum().reset_index()
        fig = px.bar(
            region_data, x='Region', y=['Sales', 'Profit'],
            barmode='group', title='Sales & Profit by Region',
            color_discrete_sequence=['#667eea', '#764ba2'],
        )
        fig.update_layout(template='plotly_white', height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        ship_data = filtered.groupby('Ship Mode')['Sales'].sum().reset_index()
        fig = px.pie(
            ship_data, values='Sales', names='Ship Mode',
            title='Sales by Ship Mode',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#a8edea'],
            hole=0.4,
        )
        fig.update_layout(template='plotly_white', height=400)
        st.plotly_chart(fig, use_container_width=True)


# ======================= TOP PRODUCTS =======================
elif view_option == "Top Products":
    n = st.slider("Number of products to display", 5, 20, 10)

    col1, col2 = st.columns(2)

    with col1:
        top_sales = (
            filtered.groupby('Product Name')['Sales'].sum()
            .sort_values(ascending=False).head(n).reset_index()
        )
        fig = px.bar(
            top_sales, x='Sales', y='Product Name',
            orientation='h', title=f'Top {n} Products by Sales',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_profit = (
            filtered.groupby('Product Name')['Profit'].sum()
            .sort_values(ascending=False).head(n).reset_index()
        )
        fig = px.bar(
            top_profit, x='Profit', y='Product Name',
            orientation='h', title=f'Top {n} Products by Profit',
            color='Profit', color_continuous_scale='Greens',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Sub-Category Performance")

    subcat = filtered.groupby('Sub-Category')[['Sales', 'Profit']].sum().reset_index()
    subcat = subcat.sort_values('Sales', ascending=False)
    fig = px.bar(
        subcat, x='Sub-Category', y=['Sales', 'Profit'],
        barmode='group', title='Sales & Profit by Sub-Category',
        color_discrete_sequence=['#667eea', '#764ba2'],
    )
    fig.update_layout(template='plotly_white', height=450, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


# ======================= SALES TRENDS =======================
elif view_option == "Sales Trends":
    monthly = filtered.set_index('Order Date').resample('M')[['Sales', 'Profit']].sum().reset_index()

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
        title='Monthly Sales & Profit Trend',
        template='plotly_white', height=450,
        xaxis_title='Date', yaxis_title='Amount ($)',
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        yearly = filtered.set_index('Order Date').resample('Y')[['Sales']].sum().reset_index()
        yearly['Year'] = yearly['Order Date'].dt.year
        fig = px.bar(
            yearly, x='Year', y='Sales', title='Yearly Sales',
            color='Sales', color_continuous_scale='Purples', text_auto=',.0f',
        )
        fig.update_layout(template='plotly_white', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        yearly_p = filtered.set_index('Order Date').resample('Y')[['Profit']].sum().reset_index()
        yearly_p['Year'] = yearly_p['Order Date'].dt.year
        fig = px.bar(
            yearly_p, x='Year', y='Profit', title='Yearly Profit',
            color='Profit', color_continuous_scale='Greens', text_auto=',.0f',
        )
        fig.update_layout(template='plotly_white', height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Quarterly Breakdown")
    quarterly = filtered.set_index('Order Date').resample('Q')[['Sales', 'Profit']].sum().reset_index()
    quarterly['Quarter'] = quarterly['Order Date'].dt.to_period('Q').astype(str)
    fig = px.bar(
        quarterly, x='Quarter', y=['Sales', 'Profit'],
        barmode='group', title='Quarterly Sales & Profit',
        color_discrete_sequence=['#667eea', '#764ba2'],
    )
    fig.update_layout(template='plotly_white', height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


# ======================= PROFIT ANALYSIS =======================
elif view_option == "Profit Analysis":
    col1, col2 = st.columns(2)

    with col1:
        fig = px.scatter(
            filtered, x='Sales', y='Profit', color='Category',
            title='Sales vs Profit',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
            opacity=0.6, hover_data=['Product Name'],
        )
        fig.update_layout(template='plotly_white', height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            filtered, x='Discount', y='Profit', color='Category',
            title='Discount vs Profit',
            color_discrete_sequence=['#667eea', '#764ba2', '#f093fb'],
            opacity=0.6,
        )
        fig.update_layout(template='plotly_white', height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    loss_products = (
        filtered.groupby('Product Name')['Profit'].sum()
        .sort_values().head(10).reset_index()
    )
    fig = px.bar(
        loss_products, x='Profit', y='Product Name',
        orientation='h', title='Top 10 Loss-Making Products',
        color='Profit', color_continuous_scale='Reds_r',
    )
    fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Profit Margin by Sub-Category")
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
        title='Profit Margin % by Sub-Category',
        template='plotly_white', height=450,
        xaxis_title='Profit Margin %',
    )
    st.plotly_chart(fig, use_container_width=True)


# ======================= REGIONAL BREAKDOWN =======================
elif view_option == "Regional Breakdown":
    region_summary = filtered.groupby('Region').agg(
        Sales=('Sales', 'sum'),
        Profit=('Profit', 'sum'),
        Orders=('Order ID', 'nunique'),
        Quantity=('Quantity', 'sum'),
    ).reset_index()

    fig = px.bar(
        region_summary, x='Region', y=['Sales', 'Profit'],
        barmode='group', title='Sales & Profit by Region',
        color_discrete_sequence=['#667eea', '#764ba2'],
        text_auto=',.0f',
    )
    fig.update_layout(template='plotly_white', height=400)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        state_sales = filtered.groupby('State')['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(
            state_sales, x='Sales', y='State',
            orientation='h', title='Top 10 States by Sales',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        city_sales = filtered.groupby('City')['Sales'].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(
            city_sales, x='Sales', y='City',
            orientation='h', title='Top 10 Cities by Sales',
            color='Sales', color_continuous_scale='Purples',
        )
        fig.update_layout(template='plotly_white', yaxis={'autorange': 'reversed'}, height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Regional Details")
    st.dataframe(
        region_summary.style.format({'Sales': '${:,.0f}', 'Profit': '${:,.0f}', 'Orders': '{:,}', 'Quantity': '{:,}'}),
        use_container_width=True,
    )
