import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

st.set_page_config(
    page_title="Schema Adoption Intelligence",
    page_icon="📊",
    layout="wide"
)

# ==========================================================
# CONFIG
# ==========================================================

CSV_URL = "https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/public_stats/google/latest.csv"

BUCKET_SCORE = {
    "< 1K": 1,
    "1K - 10K": 2,
    "10K - 100K": 3,
    "100K - 1M": 4,
    "> 1M": 5,
}

# ==========================================================
# LOAD DATA
# ==========================================================

@st.cache_data(ttl=3600)
def load_schema_stats():

    response = requests.get(CSV_URL, timeout=30)

    if response.status_code != 200:
        st.error("Could not download Schema.org statistics file.")
        st.stop()

    csv_data = StringIO(response.text)

    df = pd.read_csv(csv_data)

    cols = [c.lower() for c in df.columns]

    uri_col = None
    bucket_col = None
    type_col = None

    for col in df.columns:

        lower = col.lower()

        if "uri" in lower:
            uri_col = col

        if "bucket" in lower:
            bucket_col = col

        if "type" in lower:
            type_col = col

    if uri_col is None:
        st.error("URI column not found.")
        st.stop()

    if bucket_col is None:
        st.error("Bucket column not found.")
        st.stop()

    df["term"] = (
        df[uri_col]
        .astype(str)
        .str.replace("http://schema.org/", "", regex=False)
        .str.replace("https://schema.org/", "", regex=False)
    )

    df["bucket"] = df[bucket_col].astype(str)

    df["score"] = df["bucket"].map(BUCKET_SCORE)

    if type_col:
        df["term_type"] = df[type_col]
    else:
        df["term_type"] = "Unknown"

    return df


df = load_schema_stats()

# ==========================================================
# HEADER
# ==========================================================

st.title("📊 Schema Adoption Intelligence")

st.markdown("""
Analyze Schema.org adoption based on the official public usage statistics dataset.

Compare entities, discover opportunities, and prioritize structured data implementation using real-world adoption signals.
""")

# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.header("Filters")

selected_type = st.sidebar.multiselect(
    "Term Type",
    options=sorted(df["term_type"].unique()),
    default=sorted(df["term_type"].unique())
)

filtered_df = df[df["term_type"].isin(selected_type)]

# ==========================================================
# SEARCH
# ==========================================================

st.header("🔎 Search Schema Term")

search_term = st.text_input(
    "Search any Schema.org Type or Property",
    value="TVSeries"
)

if search_term:

    result = filtered_df[
        filtered_df["term"]
        .str.contains(search_term, case=False, na=False)
    ]

    if not result.empty:

        st.success(f"{len(result)} result(s) found")

        st.dataframe(
            result[["term", "term_type", "bucket", "score"]],
            use_container_width=True
        )

    else:
        st.warning("No matching term found.")

# ==========================================================
# COMPARE TERMS
# ==========================================================

st.header("⚔️ Compare Schema Terms")

col1, col2 = st.columns(2)

with col1:
    term1 = st.text_input(
        "Term 1",
        value="TVSeries"
    )

with col2:
    term2 = st.text_input(
        "Term 2",
        value="TVSeason"
    )

comparison = filtered_df[
    filtered_df["term"].isin([term1, term2])
]

if not comparison.empty:

    fig_compare = px.bar(
        comparison,
        x="term",
        y="score",
        color="bucket",
        title="Adoption Comparison"
    )

    st.plotly_chart(
        fig_compare,
        use_container_width=True
    )

    st.dataframe(
        comparison[
            ["term", "term_type", "bucket", "score"]
        ],
        use_container_width=True
    )

# ==========================================================
# TOP TERMS
# ==========================================================

st.header("🏆 Most Adopted Terms")

top_df = (
    filtered_df
    .sort_values(
        "score",
        ascending=False
    )
)

top_n = st.slider(
    "Number of terms",
    10,
    100,
    20
)

top_display = top_df.head(top_n)

fig_top = px.bar(
    top_display,
    x="term",
    y="score",
    color="bucket",
    title="Top Adopted Schema Terms"
)

st.plotly_chart(
    fig_top,
    use_container_width=True
)

# ==========================================================
# DISTRIBUTION
# ==========================================================

st.header("📈 Adoption Distribution")

bucket_dist = (
    filtered_df["bucket"]
    .value_counts()
    .reset_index()
)

bucket_dist.columns = [
    "bucket",
    "count"
]

fig_dist = px.pie(
    bucket_dist,
    names="bucket",
    values="count",
    title="Distribution by Adoption Bucket"
)

st.plotly_chart(
    fig_dist,
    use_container_width=True
)

# ==========================================================
# OPPORTUNITIES
# ==========================================================

st.header("💡 SEO Opportunity Finder")

low_adoption = filtered_df[
    filtered_df["score"] <= 2
]

st.info("""
Low adoption terms may represent:
- Emerging schema types
- Niche vertical opportunities
- Less competitive implementations
""")

st.dataframe(
    low_adoption[
        ["term", "term_type", "bucket"]
    ].head(50),
    use_container_width=True
)

# ==========================================================
# RECOMMENDATION ENGINE
# ==========================================================

st.header("🤖 SEO Recommendation")

selected_term = st.selectbox(
    "Choose a term",
    sorted(filtered_df["term"].unique())
)

row = filtered_df[
    filtered_df["term"] == selected_term
]

if not row.empty:

    bucket = row.iloc[0]["bucket"]
    score = row.iloc[0]["score"]

    st.subheader(selected_term)

    st.write(f"Adoption Bucket: **{bucket}**")

    if score >= 4:

        st.success(
            "Widely adopted. Recommended for implementation whenever relevant."
        )

    elif score == 3:

        st.info(
            "Moderately adopted. Valuable for SEO and structured data coverage."
        )

    else:

        st.warning(
            "Low adoption. Implement only if strongly aligned with your content."
        )

# ==========================================================
# RAW DATA
# ==========================================================

with st.expander("View Raw Dataset"):

    st.dataframe(
        filtered_df,
        use_container_width=True
    )

st.caption(
    "Source: Schema.org Public Usage Statistics Dataset"
)
