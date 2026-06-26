from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from bri_engine.core.theme_extraction import extract_top_terms
from bri_engine.settings import get_settings


SETTINGS = get_settings()
DATA_PATH = SETTINGS.output_parquet_path
CSV_FALLBACK_PATH = SETTINGS.output_csv_path
SUMMARY_PATH = SETTINGS.summary_path
SENTIMENT_COLORS = {
    "Positive": "#1f9d55",
    "Neutral": "#6b7280",
    "Negative": "#d64545",
}
AXIS_LABELS = {
    "reputation_driver": "Reputation driver",
    "sub_driver": "Reputation sub-driver",
    "source_name": "Source",
    "term": "Theme",
    "mentions": "Number of mentions",
    "score": "Theme strength",
}


def apply_page_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 1.5rem;
            max-width: 1440px;
        }
        [data-testid="stMetric"] {
            background: transparent;
            border: 1px solid rgba(49, 51, 63, 0.18);
            border-radius: 8px;
            padding: 0.85rem 0.95rem;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.78rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.55rem;
        }
        div[data-testid="stExpander"] {
            border: 1px solid rgba(49, 51, 63, 0.18);
            border-radius: 8px;
            background: transparent;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_mentions(path: str, csv_fallback_path: str) -> pd.DataFrame:
    source_path = Path(path)
    if source_path.exists():
        df = pd.read_parquet(source_path)
    elif Path(csv_fallback_path).exists():
        df = pd.read_csv(csv_fallback_path)
    else:
        raise FileNotFoundError(source_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data
def load_summary(path: str) -> dict:
    summary_file = Path(path)
    if not summary_file.exists():
        return {}
    return json.loads(summary_file.read_text(encoding="utf-8"))


def _multiselect(label: str, values: pd.Series) -> list[str]:
    options = sorted(value for value in values.dropna().unique().tolist() if str(value).strip())
    return st.sidebar.multiselect(label, options)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    drivers = _multiselect("Reputation driver", filtered["reputation_driver"])
    sub_drivers = _multiselect("Sub-driver", filtered["sub_driver"])
    sentiments = _multiselect("Sentiment", filtered["sentiment"])
    sources = _multiselect("Source", filtered["source_name"])
    search = st.sidebar.text_input("Search content").strip().lower()

    if drivers:
        filtered = filtered[filtered["reputation_driver"].isin(drivers)]
    if sub_drivers:
        filtered = filtered[filtered["sub_driver"].isin(sub_drivers)]
    if sentiments:
        filtered = filtered[filtered["sentiment"].isin(sentiments)]
    if sources:
        filtered = filtered[filtered["source_name"].isin(sources)]
    if search:
        searchable = (
            filtered["title"].fillna("")
            + " "
            + filtered["opening_text"].fillna("")
            + " "
            + filtered["hit_sentence"].fillna("")
        ).str.lower()
        filtered = filtered[searchable.str.contains(search, regex=False, na=False)]

    if filtered["date"].notna().any():
        min_date = filtered["date"].min().date()
        max_date = filtered["date"].max().date()
        selected = st.sidebar.date_input("Date range", value=(min_date, max_date))
        include_undated = st.sidebar.checkbox("Include undated records", value=True)
        if isinstance(selected, tuple) and len(selected) == 2:
            start, end = selected
            date_mask = (filtered["date"].dt.date >= start) & (filtered["date"].dt.date <= end)
            if include_undated:
                date_mask = date_mask | filtered["date"].isna()
            filtered = filtered[date_mask]

    return filtered


def plot_count_bar(
    df: pd.DataFrame,
    column: str,
    title: str,
    limit: int | None = None,
) -> None:
    counts = df[column].fillna("Unknown").value_counts().reset_index()
    counts.columns = [column, "mentions"]
    if limit:
        counts = counts.head(limit)
    fig = px.bar(
        counts.sort_values("mentions"),
        x="mentions",
        y=column,
        orientation="h",
        title=title,
        text="mentions",
        labels={
            "mentions": AXIS_LABELS["mentions"],
            column: AXIS_LABELS.get(column, column.replace("_", " ").title()),
        },
    )
    fig.update_layout(
        height=max(320, 36 * len(counts)),
        margin=dict(l=8, r=8, t=48, b=8),
        xaxis_title=AXIS_LABELS["mentions"],
        yaxis_title=AXIS_LABELS.get(column, column.replace("_", " ").title()),
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")


def render_kpis(df: pd.DataFrame, summary: dict) -> None:
    total_analyzed = summary.get("raw_rows", len(df))
    duplicates_removed = summary.get("duplicates_removed", 0)
    irrelevant_removed = summary.get("irrelevant_removed", 0)
    top_driver = df["reputation_driver"].mode().iat[0] if not df.empty else "None"
    negative_count = int((df["sentiment"] == "Negative").sum())
    positive_count = int((df["sentiment"] == "Positive").sum())

    cols = st.columns(6)
    cols[0].metric("Analyzed", f"{total_analyzed:,}")
    cols[1].metric("Relevant", f"{len(df):,}")
    cols[2].metric("Duplicates", f"{duplicates_removed:,}")
    cols[3].metric("Irrelevant", f"{irrelevant_removed:,}")
    cols[4].metric("Positive", f"{positive_count:,}")
    cols[5].metric("Negative", f"{negative_count:,}", help=f"Top driver: {top_driver}")


def render_methodology_note(summary: dict) -> None:
    duplicates_removed = summary.get("duplicates_removed", "n/a")
    irrelevant_removed = summary.get("irrelevant_removed", "n/a")

    with st.expander("Methodology and scoring, in brief", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(
            "**Source resolution**  \n"
            "Source names are standardized with `source_mapping.yml`; blanks are inferred from URL domains."
        )
        col2.markdown(
            "**Cleaning**  \n"
            f"Dates, sentiment casing, text fields, and URLs are normalized; {duplicates_removed} duplicates were removed."
        )
        col3.markdown(
            "**Relevance**  \n"
            f"Brand, leadership, product, app, and service signals are retained; {irrelevant_removed} records were filtered out."
        )
        col4.markdown(
            "**Scoring**  \n"
            "Driver and sub-driver scores come from taxonomy keyword matches, tie-break rules, confidence, and rationale."
        )


def render_insights(df: pd.DataFrame) -> None:
    st.subheader("Insights")
    if df.empty:
        st.info("No records match the current filters.")
        return

    by_driver = df.groupby("reputation_driver").size().sort_values(ascending=False)
    sentiment_driver = (
        df.pivot_table(
            index="reputation_driver",
            columns="sentiment",
            values="source_row_id",
            aggfunc="count",
            fill_value=0,
        )
        .reindex(columns=["Positive", "Neutral", "Negative"], fill_value=0)
        .sort_values("Negative", ascending=False)
    )
    themes = extract_top_terms(df["clean_text"].dropna().tolist(), n_terms=8)

    top_driver = by_driver.index[0]
    top_driver_count = int(by_driver.iloc[0])
    top_negative_count = int(sentiment_driver["Negative"].max())
    top_negative = sentiment_driver["Negative"].idxmax() if top_negative_count else "None"
    top_positive_count = int(sentiment_driver["Positive"].max())
    top_positive = sentiment_driver["Positive"].idxmax() if top_positive_count else "None"

    insight_cols = st.columns(3)
    insight_cols[0].metric(
        "Most Discussed Driver",
        f"{top_driver_count:,}",
        top_driver,
        delta_color="off",
    )
    insight_cols[1].metric(
        "Largest Negative Cluster",
        f"{top_negative_count:,}",
        top_negative,
        delta_color="off",
    )
    insight_cols[2].metric(
        "Strongest Positive Cluster",
        f"{top_positive_count:,}",
        top_positive,
        delta_color="off",
    )

    col1, col2 = st.columns([1.15, 0.85])
    with col1:
        sentiment_mix = (
            df.groupby(["reputation_driver", "sentiment"])
            .size()
            .unstack(fill_value=0)
            .reindex(columns=["Positive", "Neutral", "Negative"], fill_value=0)
        )
        fig = px.imshow(
            sentiment_mix,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues",
            title="Sentiment Intensity by Driver",
            labels={
                "x": "Sentiment label",
                "y": "Reputation driver",
                "color": "Number of mentions",
            },
        )
        fig.update_layout(
            height=360,
            margin=dict(l=8, r=8, t=48, b=8),
            xaxis_title="Sentiment label",
            yaxis_title="Reputation driver",
            coloraxis_colorbar_title="Mentions",
        )
        fig.update_traces(hovertemplate="%{y}<br>%{x}: %{z} mentions<extra></extra>")
        st.plotly_chart(fig, width="stretch")

    with col2:
        if themes:
            theme_df = pd.DataFrame(themes)
            fig = px.bar(
                theme_df.sort_values("score"),
                x="score",
                y="term",
                orientation="h",
                title="Top Discussion Themes",
                labels={
                    "score": "Theme strength",
                    "term": "Theme",
                },
            )
            fig.update_layout(
                height=320,
                margin=dict(l=8, r=8, t=48, b=8),
                xaxis_title="Theme strength",
                yaxis_title="Theme",
            )
            st.plotly_chart(fig, width="stretch")


def render_footer(df: pd.DataFrame, summary: dict) -> None:
    source_input = summary.get("source_input", "processed dataset")
    processed_output = summary.get("output_parquet") or summary.get("output_csv", "")
    raw_rows = summary.get("raw_rows", "n/a")

    st.divider()
    st.caption(
        " | ".join(
            [
                f"Source workbook: {Path(source_input).name}",
                f"Records shown: {len(df):,}",
                f"Raw records: {raw_rows}",
                f"Processed file: {Path(processed_output).name if processed_output else 'n/a'}",
            ]
        )
    )


def render_dashboard(df: pd.DataFrame, summary: dict) -> None:
    st.title("BFSI Reputation Intelligence")
    render_kpis(df, summary)
    render_methodology_note(summary)

    if df.empty:
        st.info("No records match the current filters.")
        render_footer(df, summary)
        return

    monthly_source = df.assign(
        month=lambda frame: frame["date"].dt.strftime("%Y-%m").fillna("Undated")
    )
    month_order = sorted(month for month in monthly_source["month"].unique() if month != "Undated")
    if "Undated" in monthly_source["month"].unique():
        month_order.append("Undated")

    monthly = (
        monthly_source
        .groupby(["month", "sentiment"])
        .size()
        .reset_index(name="mentions")
    )
    if not monthly.empty:
        fig = px.bar(
            monthly,
            x="month",
            y="mentions",
            color="sentiment",
            color_discrete_map=SENTIMENT_COLORS,
            title="Monthly and Undated Mentions by Sentiment",
            labels={
                "month": "Month",
                "mentions": AXIS_LABELS["mentions"],
                "sentiment": "Sentiment label",
            },
            category_orders={"month": month_order},
        )
        fig.update_layout(
            barmode="stack",
            bargap=0.28,
            margin=dict(l=8, r=8, t=48, b=8),
            legend_title_text="Sentiment",
            xaxis_title="Month (YYYY-MM; Undated means no source date)",
            yaxis_title=AXIS_LABELS["mentions"],
            xaxis_tickangle=0,
            hovermode="x unified",
        )
        st.plotly_chart(fig, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        sentiment_counts = df["sentiment"].value_counts().reset_index()
        sentiment_counts.columns = ["sentiment", "mentions"]
        fig = px.pie(
            sentiment_counts,
            names="sentiment",
            values="mentions",
            title="Sentiment Distribution",
            color="sentiment",
            color_discrete_map=SENTIMENT_COLORS,
            labels={
                "sentiment": "Sentiment label",
                "mentions": AXIS_LABELS["mentions"],
            },
        )
        fig.update_layout(margin=dict(l=8, r=8, t=48, b=8))
        st.plotly_chart(fig, width="stretch")
    with col2:
        plot_count_bar(df, "reputation_driver", "Reputation Driver Distribution")

    col3, col4 = st.columns(2)
    with col3:
        plot_count_bar(df, "sub_driver", "Sub-driver Distribution")
    with col4:
        plot_count_bar(df, "source_name", "Top Sources", limit=10)

    render_insights(df)

    st.subheader("Content Explorer")
    display_columns = [
        "date",
        "source_name",
        "title",
        "opening_text",
        "hit_sentence",
        "reputation_driver",
        "sub_driver",
        "sentiment",
        "classification_confidence",
        "classification_reason",
        "url",
    ]
    table = df[display_columns].copy()
    table["_sort_date"] = pd.to_datetime(table["date"], errors="coerce")
    table = table.sort_values(
        ["_sort_date", "source_name"],
        ascending=[False, True],
        na_position="last",
    )
    table["date"] = table["_sort_date"].dt.strftime("%Y-%m-%d").fillna("")
    table = table.drop(columns="_sort_date")
    st.dataframe(table, width="stretch", hide_index=True)
    render_footer(df, summary)


def main() -> None:
    st.set_page_config(
        page_title="BFSI Reputation Intelligence",
        page_icon=":bar_chart:",
        layout="wide",
    )
    apply_page_style()

    if not DATA_PATH.exists() and not CSV_FALLBACK_PATH.exists():
        st.error("Processed data not found. Run `uv run python -m bri_engine.pipeline` first.")
        st.stop()

    data = load_mentions(str(DATA_PATH), str(CSV_FALLBACK_PATH))
    summary = load_summary(str(SUMMARY_PATH))
    st.sidebar.header("Filters")
    filtered = apply_filters(data)
    render_dashboard(filtered, summary)


if __name__ == "__main__":
    main()
