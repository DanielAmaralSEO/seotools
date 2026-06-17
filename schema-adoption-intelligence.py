import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

st.set_page_config(
    page_title="Schema Adoption Intelligence",
    page_icon="🧠",
    layout="wide"
)

GITHUB_API_URL = "https://api.github.com/repos/schemaorg/schemaorg/contents/data/public_stats/google?ref=main"
RAW_BASE_URL = "https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/public_stats/google/"
FALLBACK_FILE = "2026_05.csv"

BUCKET_ORDER = {
    "< 1K": 1,
    "1K - 10K": 2,
    "10K - 100K": 3,
    "100K - 1M": 4,
    "> 1M": 5,
}

RICH_RESULT_TYPES = {
    "Article",
    "BreadcrumbList",
    "Course",
    "Dataset",
    "Event",
    "FAQPage",
    "HowTo",
    "JobPosting",
    "LocalBusiness",
    "Movie",
    "Organization",
    "Product",
    "Recipe",
    "Review",
    "VideoObject",
    "SoftwareApplication",
}

PLUGIN_BIAS_TYPES = {
    "Organization",
    "WebSite",
    "WebPage",
    "BreadcrumbList",
    "Article",
    "Product",
    "FAQPage",
    "Person",
}

INDUSTRY_SETS = {
    "Ecommerce": [
        "Product",
        "Offer",
        "AggregateRating",
        "Review",
        "BreadcrumbList",
        "Organization",
        "FAQPage",
    ],
    "Publisher": [
        "Article",
        "NewsArticle",
        "Person",
        "Organization",
        "BreadcrumbList",
        "VideoObject",
        "FAQPage",
    ],
    "Local Business": [
        "LocalBusiness",
        "Organization",
        "Review",
        "AggregateRating",
        "BreadcrumbList",
        "Event",
    ],
    "SaaS": [
        "SoftwareApplication",
        "Organization",
        "Product",
        "FAQPage",
        "HowTo",
        "VideoObject",
        "BreadcrumbList",
    ],
    "Education": [
        "Course",
        "Article",
        "Person",
        "Organization",
        "FAQPage",
        "VideoObject",
        "Dataset",
        "BreadcrumbList",
    ],
    "Entertainment": [
        "TVSeries",
        "TVSeason",
        "TVEpisode",
        "Movie",
        "VideoObject",
        "Review",
        "AggregateRating",
        "BreadcrumbList",
    ],
}


def normalize_bucket(value):
    value = str(value).strip()

    replacements = {
        "0-1K": "< 1K",
        "0 - 1K": "< 1K",
        "<1K": "< 1K",
        "1K-10K": "1K - 10K",
        "10K-100K": "10K - 100K",
        "100K-1M": "100K - 1M",
        ">1M": "> 1M",
        "1M+": "> 1M",
    }

    return replacements.get(value, value)


def normalize_term(value):
    value = str(value).strip()
    value = value.replace("http://schema.org/", "")
    value = value.replace("https://schema.org/", "")
    value = value.replace("schema:", "")
    return value


@st.cache_data(ttl=3600)
def get_csv_files():
    try:
        response = requests.get(GITHUB_API_URL, timeout=20)

        if response.status_code != 200:
            return [FALLBACK_FILE]

        files = response.json()

        csv_files = [
            item["name"]
            for item in files
            if item.get("name", "").endswith(".csv")
        ]

        csv_files = sorted(csv_files)

        if not csv_files:
            return [FALLBACK_FILE]

        return csv_files

    except Exception:
        return [FALLBACK_FILE]


@st.cache_data(ttl=3600)
def load_month(file_name):
    url = RAW_BASE_URL + file_name

    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"Could not download: {file_name}")

    df = pd.read_csv(StringIO(response.text))

    required_cols = ["Class", "Name", "Domain Bucket"]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise RuntimeError(f"Missing columns: {missing}")

    df = df.copy()

    df["month"] = file_name.replace(".csv", "")
    df["term_type"] = df["Class"].astype(str).str.strip()
    df["term"] = df["Name"].apply(normalize_term)
    df["bucket"] = df["Domain Bucket"].apply(normalize_bucket)
    df["adoption_tier"] = df["bucket"].map(BUCKET_ORDER).fillna(0).astype(int)

    df["rich_result_signal"] = df["term"].apply(
        lambda x: "Known rich-result type" if x in RICH_RESULT_TYPES else "No direct mapping"
    )

    df["plugin_bias_signal"] = df["term"].apply(
        lambda x: "Possible CMS/plugin bias" if x in PLUGIN_BIAS_TYPES else "Lower default-bias risk"
    )

    df["seo_lens"] = df.apply(classify_seo_lens, axis=1)

    return df


def classify_seo_lens(row):
    term = row["term"]
    tier = row["adoption_tier"]

    has_rich = term in RICH_RESULT_TYPES
    has_bias = term in PLUGIN_BIAS_TYPES

    if has_rich and tier >= 4:
        return "Operational priority"
    if has_rich and tier <= 3:
        return "Hidden opportunity"
    if not has_rich and tier >= 4 and has_bias:
        return "Commodity / default markup"
    if not has_rich and tier >= 4:
        return "Widely adopted semantic type"
    if not has_rich and tier <= 2:
        return "Niche or emerging schema"
    return "Investigate"


@st.cache_data(ttl=3600)
def load_all_data():
    files = get_csv_files()
    frames = []

    for file_name in files:
        try:
            frames.append(load_month(file_name))
        except Exception:
            pass

    if not frames:
        st.error("No Schema.org CSV files could be loaded.")
        st.stop()

    return pd.concat(frames, ignore_index=True), files


all_df, available_files = load_all_data()

available_months = sorted(all_df["month"].unique(), reverse=True)

st.title("🧠 Schema Adoption Intelligence")

st.markdown(
    """
Turn Schema.org public usage data into practical SEO decisions.

This app does not treat popularity as SEO value. It separates adoption, rich-result potential,
plugin-default bias, and industry relevance.
"""
)

st.sidebar.header("Settings")

selected_month = st.sidebar.selectbox(
    "Dataset month",
    available_months,
    key="selected_month",
)

selected_industry = st.sidebar.selectbox(
    "Industry / Site Type",
    list(INDUSTRY_SETS.keys()),
    key="selected_industry",
)

df = all_df[all_df["month"] == selected_month].copy()

with st.sidebar.expander("Dataset health check"):
    st.write("Rows loaded:", len(df))
    st.write("Available months:", len(available_months))
    st.write("Term types:", df["term_type"].dropna().unique().tolist())
    st.write("Buckets:", df["bucket"].dropna().unique().tolist())
    st.write("Sample terms:", df["term"].head(10).tolist())

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Adoption Explorer",
        "Compare Terms",
        "Bucket Distribution",
        "SEO Lens",
        "Industry Benchmark",
        "Trend Watch",
    ]
)

with tab1:
    st.header("Adoption Explorer")

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_types = st.multiselect(
            "Term type",
            sorted(df["term_type"].dropna().unique()),
            default=sorted(df["term_type"].dropna().unique()),
            key="explorer_term_type",
        )

    with col2:
        selected_buckets = st.multiselect(
            "Adoption bucket",
            list(BUCKET_ORDER.keys()),
            default=list(BUCKET_ORDER.keys()),
            key="explorer_bucket",
        )

    with col3:
        search_term = st.text_input(
            "Search term",
            value="TVSeries",
            key="explorer_search",
        )

    explorer_df = df[
        df["term_type"].isin(selected_types)
        & df["bucket"].isin(selected_buckets)
    ].copy()

    if search_term:
        explorer_df = explorer_df[
            explorer_df["term"].str.contains(search_term, case=False, na=False)
        ]

    st.dataframe(
        explorer_df[
            [
                "term",
                "term_type",
                "bucket",
                "adoption_tier",
                "rich_result_signal",
                "plugin_bias_signal",
                "seo_lens",
            ]
        ].sort_values(["adoption_tier", "term"], ascending=[False, True]),
        use_container_width=True,
    )

with tab2:
    st.header("Compare Terms")

    default_terms = "TVSeries, TVSeason, TVEpisode, VideoObject"

    terms_input = st.text_area(
        "Enter Schema.org terms separated by commas",
        value=default_terms,
        key="compare_terms_input",
    )

    terms = [
        normalize_term(term)
        for term in terms_input.split(",")
        if term.strip()
    ]

    compare_df = df[df["term"].isin(terms)].copy()

    missing = [term for term in terms if term not in compare_df["term"].tolist()]

    if compare_df.empty:
        st.warning("No matching terms found in the selected dataset month.")
    else:
        fig = px.bar(
            compare_df.sort_values("adoption_tier", ascending=False),
            x="term",
            y="adoption_tier",
            color="bucket",
            hover_data=["term_type", "seo_lens", "rich_result_signal"],
            title="Schema Term Adoption Comparison",
            labels={
                "term": "Schema.org Term",
                "adoption_tier": "Adoption Tier",
            },
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            compare_df[
                [
                    "term",
                    "term_type",
                    "bucket",
                    "adoption_tier",
                    "rich_result_signal",
                    "plugin_bias_signal",
                    "seo_lens",
                ]
            ].sort_values("adoption_tier", ascending=False),
            use_container_width=True,
        )

    if missing:
        st.info(f"Terms not found in this month: {', '.join(missing)}")

with tab3:
    st.header("Bucket Distribution")

    bucket_df = (
        df.groupby(["bucket", "term_type"])
        .size()
        .reset_index(name="count")
    )

    bucket_df["bucket_order"] = bucket_df["bucket"].map(BUCKET_ORDER)
    bucket_df = bucket_df.sort_values("bucket_order")

    fig = px.bar(
        bucket_df,
        x="bucket",
        y="count",
        color="term_type",
        title="Schema.org Term Distribution by Adoption Bucket",
        labels={
            "bucket": "Domain Count Bucket",
            "count": "Number of Terms",
        },
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        bucket_df[["bucket", "term_type", "count"]],
        use_container_width=True,
    )

with tab4:
    st.header("SEO Lens")

    st.markdown(
        """
This view does not claim that popular schemas are always effective.
It separates real-world adoption from likely SEO actionability.
"""
    )

    seo_lens_filter = st.multiselect(
        "SEO lens category",
        sorted(df["seo_lens"].unique()),
        default=sorted(df["seo_lens"].unique()),
        key="seo_lens_filter",
    )

    lens_df = df[df["seo_lens"].isin(seo_lens_filter)].copy()

    fig = px.scatter(
        lens_df,
        x="adoption_tier",
        y="term_type",
        color="seo_lens",
        hover_name="term",
        hover_data=["bucket", "rich_result_signal", "plugin_bias_signal"],
        title="Adoption vs SEO Interpretation",
        labels={
            "adoption_tier": "Adoption Tier",
            "term_type": "Term Type",
        },
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Operational priorities")
    st.dataframe(
        df[df["seo_lens"] == "Operational priority"][
            [
                "term",
                "term_type",
                "bucket",
                "adoption_tier",
                "rich_result_signal",
                "plugin_bias_signal",
                "seo_lens",
            ]
        ].sort_values("adoption_tier", ascending=False),
        use_container_width=True,
    )

    st.subheader("Hidden opportunities")
    st.dataframe(
        df[df["seo_lens"] == "Hidden opportunity"][
            [
                "term",
                "term_type",
                "bucket",
                "adoption_tier",
                "rich_result_signal",
                "plugin_bias_signal",
                "seo_lens",
            ]
        ].sort_values("adoption_tier", ascending=False),
        use_container_width=True,
    )

    st.subheader("Commodity / default markup")
    st.dataframe(
        df[df["seo_lens"] == "Commodity / default markup"][
            [
                "term",
                "term_type",
                "bucket",
                "adoption_tier",
                "rich_result_signal",
                "plugin_bias_signal",
                "seo_lens",
            ]
        ].sort_values("adoption_tier", ascending=False),
        use_container_width=True,
    )

with tab5:
    st.header("Industry Benchmark")

    expected_terms = INDUSTRY_SETS[selected_industry]

    benchmark_df = df[df["term"].isin(expected_terms)].copy()

    detected_terms = benchmark_df["term"].dropna().unique().tolist()
    missing_terms = [term for term in expected_terms if term not in detected_terms]

    coverage = round((len(detected_terms) / len(expected_terms)) * 100, 1)

    col1, col2, col3 = st.columns(3)

    col1.metric("Expected schema types", len(expected_terms))
    col2.metric("Found in dataset", len(detected_terms))
    col3.metric("Benchmark coverage", f"{coverage}%")

    st.subheader(f"Expected schema set for {selected_industry}")

    st.dataframe(
        benchmark_df[
            [
                "term",
                "term_type",
                "bucket",
                "adoption_tier",
                "rich_result_signal",
                "plugin_bias_signal",
                "seo_lens",
            ]
        ].sort_values("adoption_tier", ascending=False),
        use_container_width=True,
    )

    if missing_terms:
        st.info("Expected terms not found in this dataset month:")
        st.write(missing_terms)

    if not benchmark_df.empty:
        fig = px.bar(
            benchmark_df.sort_values("adoption_tier", ascending=False),
            x="term",
            y="adoption_tier",
            color="seo_lens",
            title=f"{selected_industry} Schema Benchmark",
            labels={
                "term": "Schema Type",
                "adoption_tier": "Adoption Tier",
            },
        )

        st.plotly_chart(fig, use_container_width=True)

with tab6:
    st.header("Trend Watch")

    all_terms = sorted(all_df["term"].dropna().unique())

    default_trend_term = "TVSeries" if "TVSeries" in all_terms else all_terms[0]

    trend_term = st.selectbox(
        "Choose a Schema.org term",
        all_terms,
        index=all_terms.index(default_trend_term),
        key="trend_term",
    )

    trend_df = all_df[all_df["term"] == trend_term].copy()
    trend_df = trend_df.sort_values("month")

    if trend_df.empty:
        st.warning("No trend data found for this term.")
    else:
        fig = px.line(
            trend_df,
            x="month",
            y="adoption_tier",
            markers=True,
            title=f"Adoption Trend: {trend_term}",
            labels={
                "month": "Month",
                "adoption_tier": "Adoption Tier",
            },
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            trend_df[
                [
                    "month",
                    "term",
                    "term_type",
                    "bucket",
                    "adoption_tier",
                    "seo_lens",
                ]
            ],
            use_container_width=True,
        )

        if len(trend_df) >= 2:
            first = trend_df.iloc[0]["adoption_tier"]
            last = trend_df.iloc[-1]["adoption_tier"]

            if last > first:
                st.success("Trend signal: adoption bucket increased.")
            elif last < first:
                st.warning("Trend signal: adoption bucket decreased.")
            else:
                st.info("Trend signal: adoption stayed in the same bucket.")

st.caption(
    "Source: Schema.org Public Usage Statistics. SEO interpretation layer is intentionally lightweight and editable."
)
