import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="AI Invoice Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 38px;
        font-weight: 700;
        color: #0081cf;
    }
    .main {
        background-color: #f8fafc;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Database Connection
def get_data():
    conn = sqlite3.connect("invoices.db")
    # Fetch Invoices
    query = """
    SELECT 
        id, 
        invoice_no, 
        invoice_date, 
        vendor, 
        vendor_gstin, 
        invoice_amount, 
        verification_status, 
        confidence_score, 
        file_name, 
        processed_at,
        error_message
    FROM invoices
    ORDER BY processed_at DESC
    """
    df = pd.read_sql_query(query, conn)
    
    # Fetch Line Item Counts for metrics
    line_counts = pd.read_sql_query("SELECT invoice_id, COUNT(*) as items FROM line_items GROUP BY invoice_id", conn)
    
    conn.close()
    return df, line_counts

# Header
st.title("📄 AI Invoice Processing Dashboard")
st.markdown("Monitor and audit your automated invoice extraction pipeline in real-time.")

try:
    df, line_counts = get_data()
    df['processed_at'] = pd.to_datetime(df['processed_at'])

    # Metrics Section
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Invoices", len(df))
    
    with col2:
        success_rate = (len(df[df['verification_status'] == 'VERIFIED']) / len(df) * 100) if len(df) > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
        
    with col3:
        total_value = df['invoice_amount'].sum()
        st.metric("Total Processed Value", f"₹{total_value:,.2f}")
        
    with col4:
        errors = len(df[df['verification_status'].isin(['CALCULATION ERROR', 'INCOMPLETE', 'FAILED OCR'])])
        st.metric("Alerts / Errors", errors, delta=-errors if errors == 0 else errors, delta_color="inverse")

    # Filters and Search
    st.divider()
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    
    with f_col1:
        search = st.text_input("🔍 Search by Invoice #, Vendor, or GSTIN", "")
        
    with f_col2:
        status_filter = st.multiselect("Status Filter", options=df['verification_status'].unique(), default=df['verification_status'].unique())
        
    with f_col3:
        sort_by = st.selectbox("Sort By", ["Newest First", "Oldest First", "Amount (High-Low)"])

    # Apply Filters
    filtered_df = df[df['verification_status'].isin(status_filter)]
    if search:
        filtered_df = filtered_df[
            filtered_df['invoice_no'].str.contains(search, case=False, na=False) |
            filtered_df['vendor'].str.contains(search, case=False, na=False) |
            filtered_df['vendor_gstin'].str.contains(search, case=False, na=False)
        ]
        
    if sort_by == "Oldest First":
        filtered_df = filtered_df.sort_values('processed_at', ascending=True)
    elif sort_by == "Amount (High-Low)":
        filtered_df = filtered_df.sort_values('invoice_amount', ascending=False)

    # Main Table
    st.subheader("Recent Activity")
    
    # Stylized column display
    display_df = filtered_df.copy()
    display_df['processed_at'] = display_df['processed_at'].dt.strftime('%Y-%m-%d %H:%M')
    
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "invoice_amount": st.column_config.NumberColumn("Amount (₹)", format="₹%.2f"),
            "confidence_score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%.0f%%"),
            "verification_status": st.column_config.TextColumn("Status"),
            "id": None # Hide ID
        },
        hide_index=True
    )

    # Detailed Audit Tool
    st.divider()
    st.subheader("🔍 Deep Audit")
    selected_invoice_no = st.selectbox("Select Invoice to inspect line items", filtered_df['invoice_no'].unique())
    
    if selected_invoice_no:
        selected_id = df[df['invoice_no'] == selected_invoice_no]['id'].iloc[0]
        conn = sqlite3.connect("invoices.db")
        li_df = pd.read_sql_query(f"SELECT * FROM line_items WHERE invoice_id = {selected_id}", conn)
        conn.close()
        
        st.write(f"Line items for Invoice: **{selected_invoice_no}**")
        st.dataframe(li_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Ensure the database has invoices and the schema is correct.")

st.sidebar.title("Settings")
st.sidebar.info("System is monitoring folder: `./invoices`")
if st.sidebar.button("Refresh Data"):
    st.rerun()
