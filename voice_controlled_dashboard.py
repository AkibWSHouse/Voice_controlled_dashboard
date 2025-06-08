import streamlit as st
import asyncio
from deepgram import Deepgram
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import dateparser

st.set_page_config(page_title="Fashion Retail Dashboard", layout="wide")
st.title("🛍️ Fashion Retail Sales Dashboard")

# Load Deepgram API Key
try:
    DEEPGRAM_API_KEY = st.secrets["DEEPGRAM_API_KEY"]
except KeyError:
    st.error("Please set DEEPGRAM_API_KEY in Streamlit secrets.")
    st.stop()

# Initialize Deepgram
dg_client = Deepgram(DEEPGRAM_API_KEY)

# Async transcription
async def transcribe(audio_bytes):
    try:
        response = await dg_client.transcription.prerecorded(
            {
                'buffer': audio_bytes.getvalue(),
                'mimetype': "audio/webm"
            },
            {
                "smart_format": True,
                "model": "nova-2",
                "language": "en-US"
            }
        )
        return response["results"]["channels"][0]["alternatives"][0]["transcript"]
    except Exception as e:
        st.error(f"Deepgram transcription error: {e}")
        return None

@st.cache_data
def load_data():
    df = pd.read_csv("Fashion_Retail_Sales.csv")
    df['Date Purchase'] = pd.to_datetime(df['Date Purchase'], format="%d-%m-%Y", errors='coerce')
    df['Review Rating'] = pd.to_numeric(df['Review Rating'], errors='coerce')
    return df

df = load_data()

# Initialize filters in session state if they don't exist
if 'selected_items' not in st.session_state:
    st.session_state.selected_items = sorted(df["Item Purchased"].dropna().unique())
if 'selected_payments' not in st.session_state:
    st.session_state.selected_payments = sorted(df["Payment Method"].dropna().unique())
if 'date_range' not in st.session_state:
    st.session_state.date_range = [df["Date Purchase"].min(), df["Date Purchase"].max()]
if 'voice_transcript' not in st.session_state:
    st.session_state.voice_transcript = ""

# Sidebar UI for voice input and filters
with st.sidebar:
    st.header("🎤 Voice Control")
    st.info("Click to Record and speak your filter commands. e.g., 'Show me sales for dresses paid by credit card from January 2023 to March 2024.' You can also say 'Reset all filters'.")

    audio_bytes = st.audio_input("Click to Record Voice Command")

    if audio_bytes:
        with st.spinner("Transcribing..."):
            transcript = asyncio.run(transcribe(audio_bytes))
            if transcript:
                st.session_state.voice_transcript = transcript
                st.markdown(f"**You said:** *{transcript}*")
            else:
                st.session_state.voice_transcript = "" # Ensure it's cleared if transcription fails

    st.markdown("---") # Separator

    st.header("Filters")

    # Reset All Filters Button (Manual)
    min_date_data = df["Date Purchase"].min()
    max_date_data = df["Date Purchase"].max()

    if st.button("🔄 Reset All Filters"):
        st.session_state.selected_items = sorted(df["Item Purchased"].dropna().unique())
        st.session_state.selected_payments = sorted(df["Payment Method"].dropna().unique())
        st.session_state.date_range = [min_date_data, max_date_data]
        st.rerun() # Rerun to apply reset immediately

    # Manual Filters (can be overridden by voice)
    all_items = sorted(df["Item Purchased"].dropna().unique())
    st.session_state.selected_items = st.multiselect(
        "Filter by Item Purchased", options=all_items, default=st.session_state.selected_items)

    all_payments = sorted(df["Payment Method"].dropna().unique())
    st.session_state.selected_payments = st.multiselect(
        "Filter by Payment Method", options=all_payments, default=st.session_state.selected_payments)

    st.markdown("### 📅 Date Range")

    st.session_state.date_range = st.date_input(
        "Select a date range",
        value=st.session_state.date_range,
        min_value=min_date_data,
        max_value=max_date_data
    )

# --- Voice Command Parsing Logic ---
# Process transcript ONLY if it's not empty
if st.session_state.voice_transcript:
    transcript_lower = st.session_state.voice_transcript.lower()

    # --- Check for Reset Command FIRST ---
    reset_keywords = ["reset all filters", "clear all filters", "reset dashboard", "clear dashboard"]
    if any(keyword in transcript_lower for keyword in reset_keywords):
        st.session_state.selected_items = sorted(df["Item Purchased"].dropna().unique())
        st.session_state.selected_payments = sorted(df["Payment Method"].dropna().unique())
        st.session_state.date_range = [df["Date Purchase"].min(), df["Date Purchase"].max()]
        st.success("Voice command: All filters have been reset.")
        st.session_state.voice_transcript = "" # IMPORTANT: Clear the transcript
        st.rerun() # IMPORTANT: Rerun immediately AFTER clearing the transcript
        # The 'return' here ensures no further parsing happens if a reset command is found
        st.stop() # Use st.stop() to immediately halt execution and prevent any further rendering/looping issues

    # If it's NOT a reset command, then proceed with other filter parsing
    # It's important that this section is NOT reached if a reset was triggered.

    # 1. Item Purchased Parsing
    potential_items = []
    for item in all_items:
        if item.lower() in transcript_lower or \
           f"for {item.lower()}" in transcript_lower or \
           f"item {item.lower()}" in transcript_lower:
            potential_items.append(item)
    if potential_items:
        st.session_state.selected_items = potential_items
        st.success(f"Voice filter applied for Items: {', '.join(potential_items)}")

    # 2. Payment Method Parsing
    potential_payments = []
    for payment in all_payments:
        if payment.lower() in transcript_lower or \
           f"by {payment.lower()}" in transcript_lower or \
           f"payment {payment.lower()}" in transcript_lower:
            potential_payments.append(payment)
    if potential_payments:
        st.session_state.selected_payments = potential_payments
        st.success(f"Voice filter applied for Payment Methods: {', '.join(potential_payments)}")

    # 3. Date Range Parsing
    date_keywords = ["from", "to", "between", "on", "in", "last", "next"]
    words = transcript_lower.split()

    start_date_str = None
    end_date_str = None

    try:
        from_index = words.index("from") if "from" in words else -1
        to_index = words.index("to") if "to" in words else -1

        if from_index != -1 and to_index != -1 and from_index < to_index:
            start_date_raw = " ".join(words[from_index + 1:to_index])
            end_date_raw = " ".join(words[to_index + 1:])

            parsed_start_date = dateparser.parse(start_date_raw, settings={'RETURN_AS_TIMEZONE_AWARE': False})
            parsed_end_date = dateparser.parse(end_date_raw, settings={'RETURN_AS_TIMEZONE_AWARE': False})

            if parsed_start_date and parsed_end_date:
                parsed_end_date = parsed_end_date.replace(hour=23, minute=59, second=59) # Inclusive end of day
                st.session_state.date_range = [parsed_start_date, parsed_end_date]
                st.success(f"Voice filter applied for Date Range: {parsed_start_date.strftime('%Y-%m-%d')} to {parsed_end_date.strftime('%Y-%m-%d')}")
            else:
                st.warning("Could not parse date range from voice command.")
        elif "last" in words:
            last_index = words.index("last")
            if last_index + 1 < len(words):
                time_period = words[last_index + 1]
                end_date = datetime.now()
                start_date = None

                if "day" in time_period:
                    start_date = end_date - timedelta(days=1)
                elif "week" in time_period:
                    start_date = end_date - timedelta(weeks=1)
                elif "month" in time_period:
                    start_date = end_date - timedelta(days=30) # Approximation
                elif "year" in time_period:
                    start_date = end_date - timedelta(days=365) # Approximation
                elif "days" in time_period and last_index + 2 < len(words) and words[last_index+2].isdigit():
                    num_days = int(words[last_index+2])
                    start_date = end_date - timedelta(days=num_days)
                elif "weeks" in time_period and last_index + 2 < len(words) and words[last_index+2].isdigit():
                    num_weeks = int(words[last_index+2])
                    start_date = end_date - timedelta(weeks=num_weeks)

                if start_date:
                    st.session_state.date_range = [start_date.date(), end_date.date()]
                    st.success(f"Voice filter applied for Date Range: Last {time_period} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                else:
                    st.warning("Could not parse 'last' time period from voice command.")
        else: # Try parsing a single date or general date phrase
            parsed_date = dateparser.parse(transcript_lower, settings={'RETURN_AS_TIMEZONE_AWARE': False})
            if parsed_date:
                parsed_date_end_of_day = parsed_date.replace(hour=23, minute=59, second=59)
                st.session_state.date_range = [parsed_date.date(), parsed_date_end_of_day.date()]
                st.success(f"Voice filter applied for Date: {parsed_date.strftime('%Y-%m-%d')}")

    except Exception as e:
        st.warning(f"Error parsing date from voice command: {e}")

    # IMPORTANT: Clear the transcript AFTER ALL parsing attempts for the current run are done.
    # This ensures it's not processed again on the next rerun unless new audio is recorded.
    st.session_state.voice_transcript = ""


# Apply filters to dataframe
df_filtered = df[
    (df["Item Purchased"].isin(st.session_state.selected_items)) &
    (df["Payment Method"].isin(st.session_state.selected_payments)) &
    (df["Date Purchase"] >= pd.to_datetime(st.session_state.date_range[0])) &
    (df["Date Purchase"] <= pd.to_datetime(st.session_state.date_range[1]))
].dropna(subset=["Purchase Amount (USD)", "Date Purchase"])

# Dashboard main area
if df_filtered.empty:
    st.warning("⚠️ No data available for the selected filters.")
else:
    st.markdown("### 📌 Key Metrics")
    total_sales = df_filtered["Purchase Amount (USD)"].sum()
    avg_rating = df_filtered["Review Rating"].mean()
    num_transactions = df_filtered.shape[0]
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("💰 Total Sales", f"${total_sales:,.2f}")
    kpi2.metric("⭐ Avg Rating", f"{avg_rating:.2f}")
    kpi3.metric("🛍️ Transactions", f"{num_transactions}")

    # Show raw data
    with st.expander("📄 View Filtered Data"):
        st.dataframe(df_filtered)

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Avg Review Ratings per Item")
        avg_rating_df = df_filtered.groupby("Item Purchased")["Review Rating"].mean().reset_index()
        fig1 = px.bar(
            avg_rating_df.sort_values("Review Rating", ascending=False),
            x="Item Purchased", y="Review Rating",
            color="Review Rating", color_continuous_scale="viridis"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("💳 Payment Method Distribution")
        payment_counts = df_filtered["Payment Method"].value_counts().reset_index()
        payment_counts.columns = ["Payment Method", "Count"]
        fig2 = px.pie(
            payment_counts, names="Payment Method", values="Count",
            title="Payment Method Breakdown",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 Total Sales Over Time")
    sales_by_date = df_filtered.groupby("Date Purchase")["Purchase Amount (USD)"].sum().reset_index()
    fig3 = px.line(
        sales_by_date, x="Date Purchase", y="Purchase Amount (USD)",
        markers=True, title="Total Sales Over Time",
        color_discrete_sequence=["steelblue"]
    )
    st.plotly_chart(fig3, use_container_width=True)