import streamlit as st
import asyncio
from deepgram import Deepgram
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import dateparser

st.set_page_config(page_title="Fashion Retail App", layout="wide")

# Navigation sidebar
st.sidebar.title("Navigation")
section = st.sidebar.radio("Go to", ["Overview", "Dashboard", "Insights", "QnA"])

if section == "Overview":
    st.title("📊 Overview")
    st.markdown("This dashboard provides voice-controlled filtering and analytics on fashion retail sales data. \n\n **Here we will put the overview of the data. let us share the overview of the current data here:** \n\n The Fashion_Retail_Sales.csv dataset contains 3400 entries detailing fashion retail transactions. Each entry includes a Customer Reference ID, Item Purchased, Purchase Amount (USD), Date Purchase, Review Rating, and Payment Method.\n\nThe data spans purchases made between October 2, 2022, and October 1, 2023. While all customer IDs, items, dates, and payment methods are present, there are missing values in Purchase Amount (USD) (2750 non-null) and Review Rating (3076 non-null), suggesting incomplete transaction records or optional customer feedback.\n\nAnalysis of Item Purchased reveals a diverse range of fashion items, with Belt, Skirt, Shorts, Pants, and Tank Top being among the most frequently bought. Payment Method is split between Credit Card (1770 transactions) and Cash (1630 transactions).\n\nPurchase Amount (USD) varies significantly, ranging from a minimum of $10.00 to a maximum of $4932.00, with a mean of approximately $156.71. The distribution shows that 75% of purchases are below $155.75, but a few high-value transactions skew the average. Review Rating, on a scale of 1 to 5, averages around 3.00, with a fairly even distribution across the range, indicating varied customer satisfaction.")

elif section == "Dashboard":
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

    if 'selected_items' not in st.session_state:
        st.session_state.selected_items = sorted(df["Item Purchased"].dropna().unique())
    if 'selected_payments' not in st.session_state:
        st.session_state.selected_payments = sorted(df["Payment Method"].dropna().unique())
    if 'date_range' not in st.session_state:
        st.session_state.date_range = [df["Date Purchase"].min(), df["Date Purchase"].max()]
    if 'voice_transcript' not in st.session_state:
        st.session_state.voice_transcript = ""

    with st.sidebar:
        st.header("🎤 Voice Control")
        st.info("Click to Record and speak your filter commands.")
        audio_bytes = st.audio_input("Click to Record Voice Command")

        if audio_bytes:
            with st.spinner("Transcribing..."):
                transcript = asyncio.run(transcribe(audio_bytes))
                if transcript:
                    st.session_state.voice_transcript = transcript
                    st.markdown(f"**You said:** *{transcript}*")
                else:
                    st.session_state.voice_transcript = ""

        st.markdown("---")
        st.header("Filters")
        min_date_data = df["Date Purchase"].min()
        max_date_data = df["Date Purchase"].max()

        if st.button("🔄 Reset All Filters"):
            st.session_state.selected_items = sorted(df["Item Purchased"].dropna().unique())
            st.session_state.selected_payments = sorted(df["Payment Method"].dropna().unique())
            st.session_state.date_range = [min_date_data, max_date_data]
            st.rerun()

        all_items = sorted(df["Item Purchased"].dropna().unique())
        st.session_state.selected_items = st.multiselect(
            "Filter by Item Purchased", options=all_items, default=st.session_state.selected_items)

        all_payments = sorted(df["Payment Method"].dropna().unique())
        st.session_state.selected_payments = st.multiselect(
            "Filter by Payment Method", options=all_payments, default=st.session_state.selected_payments)

        st.markdown("### 🗕️ Date Range")
        st.session_state.date_range = st.date_input(
            "Select a date range",
            value=st.session_state.date_range,
            min_value=min_date_data,
            max_value=max_date_data
        )

    if st.session_state.voice_transcript:
        transcript_lower = st.session_state.voice_transcript.lower()

        reset_keywords = ["reset all filters", "clear all filters", "reset dashboard", "clear dashboard"]
        if any(keyword in transcript_lower for keyword in reset_keywords):
            st.session_state.selected_items = sorted(df["Item Purchased"].dropna().unique())
            st.session_state.selected_payments = sorted(df["Payment Method"].dropna().unique())
            st.session_state.date_range = [df["Date Purchase"].min(), df["Date Purchase"].max()]
            st.success("Voice command: All filters have been reset.")
            st.session_state.voice_transcript = ""
            st.rerun()
            st.stop()

        potential_items = []
        for item in all_items:
            if item.lower() in transcript_lower or f"for {item.lower()}" in transcript_lower:
                potential_items.append(item)
        if potential_items:
            st.session_state.selected_items = potential_items
            st.success(f"Voice filter applied for Items: {', '.join(potential_items)}")

        potential_payments = []
        for payment in all_payments:
            if payment.lower() in transcript_lower or f"by {payment.lower()}" in transcript_lower:
                potential_payments.append(payment)
        if potential_payments:
            st.session_state.selected_payments = potential_payments
            st.success(f"Voice filter applied for Payment Methods: {', '.join(potential_payments)}")

        try:
            words = transcript_lower.split()
            from_index = words.index("from") if "from" in words else -1
            to_index = words.index("to") if "to" in words else -1

            if from_index != -1 and to_index != -1 and from_index < to_index:
                start_date_raw = " ".join(words[from_index + 1:to_index])
                end_date_raw = " ".join(words[to_index + 1:])

                parsed_start_date = dateparser.parse(start_date_raw)
                parsed_end_date = dateparser.parse(end_date_raw)

                if parsed_start_date and parsed_end_date:
                    st.session_state.date_range = [parsed_start_date, parsed_end_date]
                    st.success(f"Voice filter applied for Date Range: {parsed_start_date.date()} to {parsed_end_date.date()}")
            elif "last" in words:
                end_date = datetime.now()
                start_date = end_date
                if "month" in words:
                    start_date = end_date - timedelta(days=30)
                elif "week" in words:
                    start_date = end_date - timedelta(weeks=1)
                elif "year" in words:
                    start_date = end_date - timedelta(days=365)
                st.session_state.date_range = [start_date.date(), end_date.date()]
                st.success(f"Voice filter applied for Date Range: {start_date.date()} to {end_date.date()}")
        except Exception as e:
            st.warning(f"Error parsing date from voice command: {e}")

        st.session_state.voice_transcript = ""

    df_filtered = df[
        (df["Item Purchased"].isin(st.session_state.selected_items)) &
        (df["Payment Method"].isin(st.session_state.selected_payments)) &
        (df["Date Purchase"] >= pd.to_datetime(st.session_state.date_range[0])) &
        (df["Date Purchase"] <= pd.to_datetime(st.session_state.date_range[1]))
    ].dropna(subset=["Purchase Amount (USD)", "Date Purchase"])

    if df_filtered.empty:
        st.warning("\u26a0\ufe0f No data available for the selected filters.")
    else:
        st.markdown("### 📌 Key Metrics")
        total_sales = df_filtered["Purchase Amount (USD)"].sum()
        avg_rating = df_filtered["Review Rating"].mean()
        num_transactions = df_filtered.shape[0]
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 Total Sales", f"${total_sales:,.2f}")
        kpi2.metric("⭐ Avg Rating", f"{avg_rating:.2f}")
        kpi3.metric("🛍️ Transactions", f"{num_transactions}")

        with st.expander("📄 View Filtered Data"):
            st.dataframe(df_filtered, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 Avg Review Ratings per Item")
            avg_rating_df = df_filtered.groupby("Item Purchased")["Review Rating"].mean().reset_index()
            fig1 = px.bar(avg_rating_df.sort_values("Review Rating", ascending=False),
                         x="Item Purchased", y="Review Rating",
                         color="Review Rating", color_continuous_scale="viridis")
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.subheader("💳 Payment Method Distribution")
            payment_counts = df_filtered["Payment Method"].value_counts().reset_index()
            payment_counts.columns = ["Payment Method", "Count"]
            fig2 = px.pie(payment_counts, names="Payment Method", values="Count",
                         title="Payment Method Breakdown",
                         color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📈 Total Sales Over Time")
        sales_by_date = df_filtered.groupby("Date Purchase")["Purchase Amount (USD)"].sum().reset_index()
        fig3 = px.line(sales_by_date, x="Date Purchase", y="Purchase Amount (USD)",
                       markers=True, title="Total Sales Over Time",
                       color_discrete_sequence=["steelblue"])
        st.plotly_chart(fig3, use_container_width=True)

elif section == "Insights":
    st.title("📈 Insights")
    st.markdown("Add charts, trends or summary insights here.")

elif section == "QnA":
    st.title("❓ QnA")
    st.markdown("a chatbot and voice interface for asking questions about your data will be integrated here .")
    st.markdown("Ask questions about the dataset using voice or text.")

    # Record and transcribe using Deepgram
    st.subheader("🎤 Voice Input")
    audio_bytes_qna = st.audio_input("Click to record your question")

    transcript_qna = ""

    if audio_bytes_qna:
        with st.spinner("Transcribing your question..."):
            transcript_qna = asyncio.run(transcribe(audio_bytes_qna))
            if transcript_qna:
                st.success(f"🗣️ You said: *{transcript_qna}*")
            else:
                st.warning("Could not transcribe your voice.")

    # Text input fallback
    question = st.text_input("💬 Ask a question", value=transcript_qna if transcript_qna else "")

    if question:
        st.info(f"📌 You asked: {question}")
        st.success("🔍 Answer: This is a placeholder. LLM-based answers will appear here soon.")
