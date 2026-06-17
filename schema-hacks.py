
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO
from datetime import datetime

# =========================================================
# APP CONFIG
# =========================================================

st.set_page_config(
    page_title="Schema Comparator for SEO",
    page_icon="⚖️",
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

BUCKET_MIDPOINT = {
    "< 1K": 500,
    "1K - 10K": 5500,
    "10K - 100K": 55000,
    "100K - 1M": 550000,
    "> 1M": 1500000,
}

BUCKET_LABEL = {
    1: "< 1K domains",
    2: "1K - 10K domains",
    3: "10K - 100K domains",
    4: "100K - 1M domains",
    5: "> 1M domains",
}

# =========================================================
# GOOGLE RICH RESULT KNOWLEDGE LAYER
# =========================================================
# Keep this dictionary editable.
# It intentionally distinguishes:
# - Schema.org type
# - Google rich result documentation / Search feature
# - Search intent / industry relevance
# - Whether high adoption is likely inflated by CMS/plugin defaults

GOOGLE_RICH_RESULT_MAP = {
    "Article": {
        "google_status": "Documented rich result",
        "google_feature": "Article",
        "industries": ["Publisher", "News", "Education", "Healthcare", "SaaS"],
        "templates": ["Article page", "Blog post", "News article"],
        "intent": "Informational",
        "seo_value": 4,
        "cms_bias": "High",
        "gap_note": "Often implemented by publishers and CMS templates. Audit freshness, authorship, images, and duplicate Article/WebPage markup.",
    },
    "NewsArticle": {
        "google_status": "Documented rich result",
        "google_feature": "Article",
        "industries": ["Publisher", "News"],
        "templates": ["News article"],
        "intent": "Informational",
        "seo_value": 4,
        "cms_bias": "Medium",
        "gap_note": "Relevant for news content. Do not use for evergreen blog posts unless the page is truly news-oriented.",
    },
    "BlogPosting": {
        "google_status": "Related to documented Article markup",
        "google_feature": "Article",
        "industries": ["Publisher", "Education", "Healthcare", "SaaS"],
        "templates": ["Blog post", "Article page"],
        "intent": "Informational",
        "seo_value": 3,
        "cms_bias": "High",
        "gap_note": "Common in CMSs. Can be useful, but Article/BlogPosting alone rarely creates a competitive advantage.",
    },
    "BreadcrumbList": {
        "google_status": "Documented rich result",
        "google_feature": "Breadcrumb",
        "industries": ["Ecommerce", "Marketplace", "Publisher", "Local Business", "SaaS", "Education", "Healthcare", "Entertainment", "Travel"],
        "templates": ["All templates"],
        "intent": "Navigation",
        "seo_value": 5,
        "cms_bias": "High",
        "gap_note": "Foundational markup. High adoption is expected because CMSs and SEO plugins often generate it automatically.",
    },
    "Product": {
        "google_status": "Documented rich result",
        "google_feature": "Product snippets / Merchant listings",
        "industries": ["Ecommerce", "Marketplace", "SaaS"],
        "templates": ["Product page"],
        "intent": "Commercial",
        "seo_value": 5,
        "cms_bias": "High",
        "gap_note": "High actionability for ecommerce, but high adoption may be inflated by Shopify, WooCommerce, and SEO plugins.",
    },
    "Offer": {
        "google_status": "Required/related property type for Product",
        "google_feature": "Product snippets / Merchant listings",
        "industries": ["Ecommerce", "Marketplace"],
        "templates": ["Product page"],
        "intent": "Commercial",
        "seo_value": 5,
        "cms_bias": "Medium",
        "gap_note": "Important for Product eligibility. Price and availability must match visible page content.",
    },
    "AggregateRating": {
        "google_status": "Related to documented Review/Product markup",
        "google_feature": "Review snippets / Product snippets",
        "industries": ["Ecommerce", "Marketplace", "Local Business", "Entertainment", "Education", "Travel"],
        "templates": ["Product page", "Review page", "Location page", "Course page"],
        "intent": "Trust / evaluation",
        "seo_value": 4,
        "cms_bias": "Medium",
        "gap_note": "Valuable only when ratings are genuine and visible. Misuse can create quality and compliance risk.",
    },
    "Review": {
        "google_status": "Documented rich result",
        "google_feature": "Review snippet",
        "industries": ["Ecommerce", "Marketplace", "Local Business", "Entertainment", "Education", "Travel"],
        "templates": ["Product page", "Review page", "Location page"],
        "intent": "Trust / evaluation",
        "seo_value": 4,
        "cms_bias": "Medium",
        "gap_note": "Useful where review content is a primary part of the page. Avoid self-serving or invisible reviews.",
    },
    "LocalBusiness": {
        "google_status": "Documented rich result",
        "google_feature": "Local business",
        "industries": ["Local Business", "Healthcare", "Travel"],
        "templates": ["Homepage", "Location page"],
        "intent": "Local / navigational",
        "seo_value": 5,
        "cms_bias": "Medium",
        "gap_note": "Critical for location pages. Audit NAP, opening hours, address, geo, phone, and entity consistency.",
    },
    "Organization": {
        "google_status": "Documented rich result / structured data feature",
        "google_feature": "Organization / Logo",
        "industries": ["Ecommerce", "Marketplace", "Publisher", "News", "Local Business", "SaaS", "Education", "Healthcare", "Entertainment", "Travel"],
        "templates": ["Homepage", "About page"],
        "intent": "Entity clarity",
        "seo_value": 3,
        "cms_bias": "High",
        "gap_note": "Useful for entity disambiguation, but high adoption is often plugin-driven. Not usually a template-level growth lever.",
    },
    "Event": {
        "google_status": "Documented rich result",
        "google_feature": "Event",
        "industries": ["Local Business", "Education", "Entertainment", "Publisher", "Travel"],
        "templates": ["Event page"],
        "intent": "Event discovery",
        "seo_value": 5,
        "cms_bias": "Low",
        "gap_note": "Strong opportunity when event pages exist. Lower plugin-default bias makes gaps more meaningful.",
    },
    "JobPosting": {
        "google_status": "Documented rich result",
        "google_feature": "Job posting",
        "industries": ["Marketplace", "SaaS", "Education"],
        "templates": ["Job page", "Careers page"],
        "intent": "Jobs",
        "seo_value": 5,
        "cms_bias": "Low",
        "gap_note": "Highly actionable for job boards and career pages. Requires freshness and validThrough hygiene.",
    },
    "Course": {
        "google_status": "Documented rich result",
        "google_feature": "Course / Course list",
        "industries": ["Education"],
        "templates": ["Course page", "Course listing"],
        "intent": "Education",
        "seo_value": 5,
        "cms_bias": "Low",
        "gap_note": "High gap value for education websites. Adoption may be lower than its niche importance.",
    },
    "Recipe": {
        "google_status": "Documented rich result",
        "google_feature": "Recipe",
        "industries": ["Publisher", "Food"],
        "templates": ["Recipe page"],
        "intent": "Food / how-to",
        "seo_value": 5,
        "cms_bias": "Medium",
        "gap_note": "Highly relevant for recipe publishers; not relevant outside recipe content.",
    },
    "VideoObject": {
        "google_status": "Documented rich result",
        "google_feature": "Video",
        "industries": ["Publisher", "News", "Education", "Entertainment", "SaaS", "Ecommerce"],
        "templates": ["Video page", "Article page", "Product page", "Course page"],
        "intent": "Media",
        "seo_value": 4,
        "cms_bias": "Medium",
        "gap_note": "Often under-audited. Strong gap candidate when video is central to the page.",
    },
    "Movie": {
        "google_status": "Documented rich result / carousel-compatible feature",
        "google_feature": "Movie",
        "industries": ["Entertainment"],
        "templates": ["Movie page", "Listing page"],
        "intent": "Entertainment",
        "seo_value": 4,
        "cms_bias": "Low",
        "gap_note": "Strong niche fit for entertainment catalogs and streaming/library sites.",
    },
    "Dataset": {
        "google_status": "Documented rich result",
        "google_feature": "Dataset",
        "industries": ["Education", "Publisher", "SaaS", "Healthcare"],
        "templates": ["Dataset page", "Research page"],
        "intent": "Research / data",
        "seo_value": 3,
        "cms_bias": "Low",
        "gap_note": "Niche but valuable when real datasets exist. Low adoption does not imply low relevance.",
    },
    "SoftwareApplication": {
        "google_status": "Documented rich result",
        "google_feature": "Software app",
        "industries": ["SaaS", "Marketplace"],
        "templates": ["Software product page", "App page"],
        "intent": "Software / commercial",
        "seo_value": 4,
        "cms_bias": "Low",
        "gap_note": "Useful for SaaS tools, app pages, and software directories.",
    },
    "FAQPage": {
        "google_status": "Limited / reduced visibility",
        "google_feature": "FAQ",
        "industries": ["Ecommerce", "SaaS", "Education", "Healthcare", "Local Business"],
        "templates": ["FAQ page", "Support page", "Product page"],
        "intent": "Support / informational",
        "seo_value": 2,
        "cms_bias": "High",
        "gap_note": "Historically overused. Treat as semantic support, not a primary rich-result growth lever.",
    },
    "HowTo": {
        "google_status": "Limited / reduced visibility",
        "google_feature": "How-to",
        "industries": ["Publisher", "Education", "SaaS"],
        "templates": ["Guide page", "Support page"],
        "intent": "Instructional",
        "seo_value": 2,
        "cms_bias": "Medium",
        "gap_note": "Use only for genuine step-by-step content. Do not over-prioritize versus stronger rich-result types.",
    },
    "Person": {
        "google_status": "Not a standalone rich result",
        "google_feature": "Entity understanding",
        "industries": ["Publisher", "News", "Education", "Healthcare"],
        "templates": ["Author page", "Bio page", "Article page"],
        "intent": "Entity clarity",
        "seo_value": 3,
        "cms_bias": "Medium",
        "gap_note": "Important for authors, experts, doctors, instructors, and E-E-A-T/entity clarity, but not a direct rich-result target.",
    },
    "TVSeries": {
        "google_status": "Not a standalone rich result",
        "google_feature": "Entity understanding",
        "industries": ["Entertainment"],
        "templates": ["Series page"],
        "intent": "Entertainment entity",
        "seo_value": 3,
        "cms_bias": "Low",
        "gap_note": "Useful for entertainment entity architecture. Compare against VideoObject and Movie for richer Search features.",
    },
    "TVSeason": {
        "google_status": "Not a standalone rich result",
        "google_feature": "Entity understanding",
        "industries": ["Entertainment"],
        "templates": ["Season page"],
        "intent": "Entertainment entity",
        "seo_value": 2,
        "cms_bias": "Low",
        "gap_note": "Use when season pages exist. Lower adoption is not a problem if the template needs the entity.",
    },
    "TVEpisode": {
        "google_status": "Not a standalone rich result",
        "google_feature": "Entity understanding",
        "industries": ["Entertainment"],
        "templates": ["Episode page"],
        "intent": "Entertainment entity",
        "seo_value": 2,
        "cms_bias": "Low",
        "gap_note": "Use when episode pages exist. Pair with VideoObject when pages contain playable video.",
    },
}

INDUSTRY_RECOMMENDED_SETS = {
    "Ecommerce": ["Product", "Offer", "AggregateRating", "Review", "BreadcrumbList", "Organization", "VideoObject", "FAQPage"],
    "Marketplace": ["Product", "Offer", "AggregateRating", "Review", "BreadcrumbList", "Organization", "JobPosting", "SoftwareApplication"],
    "Publisher": ["Article", "NewsArticle", "BlogPosting", "Person", "Organization", "BreadcrumbList", "VideoObject", "FAQPage", "Dataset"],
    "News": ["NewsArticle", "Article", "Person", "Organization", "BreadcrumbList", "VideoObject"],
    "Local Business": ["LocalBusiness", "Organization", "BreadcrumbList", "Review", "AggregateRating", "Event", "FAQPage"],
    "SaaS": ["SoftwareApplication", "Product", "Organization", "Article", "VideoObject", "FAQPage", "HowTo", "BreadcrumbList"],
    "Education": ["Course", "Article", "Person", "Organization", "VideoObject", "Dataset", "FAQPage", "Event", "BreadcrumbList"],
    "Healthcare": ["LocalBusiness", "Person", "Article", "Organization", "FAQPage", "Review", "Dataset", "BreadcrumbList"],
    "Entertainment": ["Movie", "VideoObject", "TVSeries", "TVSeason", "TVEpisode", "Review", "AggregateRating", "BreadcrumbList"],
    "Travel": ["LocalBusiness", "Event", "Review", "AggregateRating", "BreadcrumbList", "Organization", "FAQPage"],
}

DEFAULT_COMPARE_BY_INDUSTRY = {
    "Ecommerce": ["Product", "Offer", "AggregateRating", "Review", "BreadcrumbList", "VideoObject"],
    "Marketplace": ["Product", "Offer", "Review", "AggregateRating", "JobPosting", "SoftwareApplication"],
    "Publisher": ["Article", "NewsArticle", "BlogPosting", "VideoObject", "FAQPage", "Dataset"],
    "News": ["NewsArticle", "Article", "VideoObject", "Person", "Organization", "BreadcrumbList"],
    "Local Business": ["LocalBusiness", "Review", "AggregateRating", "Event", "Organization", "BreadcrumbList"],
    "SaaS": ["SoftwareApplication", "Product", "VideoObject", "Article", "FAQPage", "HowTo"],
    "Education": ["Course", "VideoObject", "Article", "Person", "Dataset", "FAQPage"],
    "Healthcare": ["LocalBusiness", "Person", "Article", "Review", "FAQPage", "Dataset"],
    "Entertainment": ["TVSeries", "TVSeason", "TVEpisode", "Movie", "VideoObject", "Review"],
    "Travel": ["LocalBusiness", "Event", "Review", "AggregateRating", "BreadcrumbList", "FAQPage"],
}


# =========================================================
# DATA LOADING
# =========================================================

def normalize_bucket(value):
    value = str(value).strip()
    replacements = {
        "0-1K": "< 1K",
        "0 - 1K": "< 1K",
        "<1K": "< 1K",
        "< 1k": "< 1K",
        "1k-10k": "1K - 10K",
        "1K-10K": "1K - 10K",
        "10K-100K": "10K - 100K",
        "100K-1M": "100K - 1M",
        "1M+": "> 1M",
        ">1M": "> 1M",
    }
    return replacements.get(value, value)


def normalize_term(value):
    value = str(value).strip()
    value = value.replace("http://schema.org/", "")
    value = value.replace("https://schema.org/", "")
    value = value.replace("schema:", "")
    value = value.split("/")[-1]
    return value.strip()


@st.cache_data(ttl=3600)
def get_csv_files():
    try:
        response = requests.get(GITHUB_API_URL, timeout=20)
        if response.status_code != 200:
            return [FALLBACK_FILE]

        items = response.json()
        csv_files = sorted([
            item.get("name")
            for item in items
            if item.get("name", "").endswith(".csv")
        ])

        return csv_files if csv_files else [FALLBACK_FILE]

    except Exception:
        return [FALLBACK_FILE]


@st.cache_data(ttl=3600)
def load_month(file_name):
    url = RAW_BASE_URL + file_name
    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"Could not download {file_name}")

    df = pd.read_csv(StringIO(response.text))

    required_cols = ["Class", "Name", "Domain Bucket"]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise RuntimeError(f"Missing columns in {file_name}: {missing_cols}")

    df = df.copy()
    df["month"] = file_name.replace(".csv", "")
    df["term_type"] = df["Class"].astype(str).str.strip()
    df["term"] = df["Name"].apply(normalize_term)
    df["bucket"] = df["Domain Bucket"].apply(normalize_bucket)
    df["adoption_tier"] = df["bucket"].map(BUCKET_ORDER).fillna(0).astype(int)
    df["estimated_midpoint"] = df["bucket"].map(BUCKET_MIDPOINT).fillna(0).astype(int)

    return df[["month", "term_type", "term", "bucket", "adoption_tier", "estimated_midpoint"]]


@st.cache_data(ttl=3600)
def load_all_months():
    files = get_csv_files()
    frames = []
    skipped = []

    for file_name in files:
        try:
            frames.append(load_month(file_name))
        except Exception as exc:
            skipped.append((file_name, str(exc)))

    if not frames:
        st.error("No Schema.org public usage statistics CSV files could be loaded.")
        st.stop()

    return pd.concat(frames, ignore_index=True), files, skipped


# =========================================================
# ENRICHMENT / SCORING
# =========================================================

def meta(term, field, default=None):
    return GOOGLE_RICH_RESULT_MAP.get(term, {}).get(field, default)


def google_status_points(status):
    if status == "Documented rich result":
        return 35
    if status == "Documented rich result / structured data feature":
        return 30
    if status == "Documented rich result / carousel-compatible feature":
        return 30
    if status == "Related to documented Review/Product markup":
        return 25
    if status == "Related to documented Article markup":
        return 22
    if status == "Required/related property type for Product":
        return 25
    if status == "Limited / reduced visibility":
        return 8
    if status == "Not a standalone rich result":
        return 5
    return 0


def cms_bias_penalty(bias):
    if bias == "High":
        return 15
    if bias == "Medium":
        return 8
    if bias == "Low":
        return 0
    return 4


def classify_gap(row):
    adoption = row["adoption_tier"]
    documented = row["is_google_documented"]
    niche = row["industry_relevant"]
    bias = row["cms_bias"]
    status = row["google_status"]

    if documented and niche and adoption <= 3:
        return "High-value niche gap"
    if documented and niche and adoption >= 4:
        return "Core implementation priority"
    if documented and not niche:
        return "Documented but low niche fit"
    if not documented and niche and adoption >= 3:
        return "Semantic niche opportunity"
    if adoption >= 4 and bias == "High":
        return "Popular but likely plugin-driven"
    if status == "Limited / reduced visibility":
        return "Use with caution"
    return "Low priority / investigate"


def priority_label(score):
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def enrich(df, industry):
    df = df.copy()

    recommended_set = set(INDUSTRY_RECOMMENDED_SETS.get(industry, []))

    df["google_status"] = df["term"].apply(lambda x: meta(x, "google_status", "Not mapped"))
    df["google_feature"] = df["term"].apply(lambda x: meta(x, "google_feature", "No known Google rich result mapping"))
    df["search_intent"] = df["term"].apply(lambda x: meta(x, "intent", "Unknown"))
    df["seo_value"] = df["term"].apply(lambda x: meta(x, "seo_value", 1))
    df["cms_bias"] = df["term"].apply(lambda x: meta(x, "cms_bias", "Unknown"))
    df["gap_note"] = df["term"].apply(lambda x: meta(x, "gap_note", "No curated SEO note yet. Treat this as raw Schema.org adoption data."))
    df["industry_relevant"] = df["term"].apply(lambda x: industry in meta(x, "industries", []))
    df["recommended_for_industry"] = df["term"].apply(lambda x: x in recommended_set)

    df["is_google_documented"] = df["google_status"].apply(
        lambda x: (
            "Documented rich result" in x
            or "Related to documented" in x
            or "Required/related" in x
        )
    )

    df["google_gap_type"] = df.apply(classify_gap, axis=1)

    df["gap_score"] = (
        df["adoption_tier"] * 8
        + df["seo_value"] * 8
        + df["google_status"].apply(google_status_points)
        + df["industry_relevant"].astype(int) * 15
        + df["recommended_for_industry"].astype(int) * 15
        - df["cms_bias"].apply(cms_bias_penalty)
    ).clip(lower=0, upper=100).round(0).astype(int)

    df["priority"] = df["gap_score"].apply(priority_label)

    return df


def make_explanation(row, industry):
    term = row["term"]

    lines = [
        f"### {term}",
        "",
        f"- **Adoption:** Tier {row['adoption_tier']} ({row['bucket']})",
        f"- **Google documentation status:** {row['google_status']}",
        f"- **Google feature mapping:** {row['google_feature']}",
        f"- **Industry fit for {industry}:** {'Yes' if row['industry_relevant'] else 'No'}",
        f"- **CMS/plugin bias:** {row['cms_bias']}",
        f"- **Gap type:** {row['google_gap_type']}",
        f"- **Priority:** {row['priority']} ({row['gap_score']}/100)",
        "",
        f"**SEO interpretation:** {row['gap_note']}",
    ]

    if row["google_gap_type"] == "High-value niche gap":
        lines.append("**Recommended action:** prioritize this as a niche opportunity. It is documented by Google but not yet broadly adopted across the public web.")
    elif row["google_gap_type"] == "Core implementation priority":
        lines.append("**Recommended action:** audit this across your main templates. It is both relevant to the niche and aligned with Google-documented structured data features.")
    elif row["google_gap_type"] == "Popular but likely plugin-driven":
        lines.append("**Recommended action:** validate quality, but do not treat popularity alone as evidence of competitive advantage.")
    elif row["google_gap_type"] == "Semantic niche opportunity":
        lines.append("**Recommended action:** use when it improves entity architecture, but do not sell it as a direct rich-result lever.")
    elif row["google_gap_type"] == "Use with caution":
        lines.append("**Recommended action:** use only when it genuinely matches visible page content. Do not over-prioritize for rich-result visibility.")

    return "\n".join(lines)


# =========================================================
# APP DATA
# =========================================================

all_df, csv_files, skipped_files = load_all_months()
months = sorted(all_df["month"].unique(), reverse=True)

# =========================================================
# UI
# =========================================================

st.title("⚖️ Schema Comparator for SEO")
st.markdown(
    """
Compare up to **6 Schema.org types** against public adoption data and Google rich-result documentation.

The goal is to identify the gap between:
1. what is widely deployed on the public web,
2. what Google documents for rich results,
3. what matters in the selected niche.
"""
)

st.info(
    "Important: Google documentation indicates eligibility, not a guarantee that a rich result will appear. Use this as an audit prioritization tool, not as a ranking-impact calculator."
)

st.sidebar.header("Analysis Settings")

selected_month = st.sidebar.selectbox(
    "Schema.org usage dataset month",
    months,
    key="selected_month"
)

selected_industry = st.sidebar.selectbox(
    "Niche / industry",
    list(INDUSTRY_RECOMMENDED_SETS.keys()),
    key="selected_industry"
)

base_df = all_df[all_df["month"] == selected_month].copy()
df = enrich(base_df, selected_industry)

all_type_terms = sorted(df[df["term_type"].str.lower() == "type"]["term"].dropna().unique())
default_terms = [t for t in DEFAULT_COMPARE_BY_INDUSTRY[selected_industry] if t in all_type_terms]

if len(default_terms) < 6:
    fallback = [t for t in ["Product", "Article", "BreadcrumbList", "Organization", "VideoObject", "Review"] if t in all_type_terms]
    default_terms = (default_terms + fallback)[:6]

st.sidebar.subheader("Quick Start")

preset = st.sidebar.selectbox(
    "Industry preset",
    ["Custom"] + list(DEFAULT_COMPARE_BY_INDUSTRY.keys())
)

if preset != "Custom":
    default_selection = DEFAULT_COMPARE_BY_INDUSTRY[preset]
else:
    default_selection = []

selected_terms = st.sidebar.multiselect(
    "Select up to 6 schemas",
    options=all_type_terms,
    default=default_selection,
    max_selections=6,
    key="schema_selector"
)

with st.sidebar.expander("Dataset health"):
    st.write("Rows loaded:", len(df))
    st.write("Months available:", len(months))
    st.write("CSV files found:", len(csv_files))
    st.write("Skipped files:", len(skipped_files))
    st.write("Selected schemas:", selected_terms)

if not selected_terms:
    st.warning("Select at least one Schema.org type in the sidebar.")
    st.stop()

compare_df = df[df["term"].isin(selected_terms)].copy()

# Preserve selection order
compare_df["selection_order"] = compare_df["term"].apply(lambda x: selected_terms.index(x) if x in selected_terms else 999)
compare_df = compare_df.sort_values("selection_order")

# =========================================================
# HEADER KPIS
# =========================================================

k1, k2, k3, k4 = st.columns(4)

documented_count = int(compare_df["is_google_documented"].sum())
industry_count = int(compare_df["industry_relevant"].sum())
avg_gap_score = round(compare_df["gap_score"].mean(), 1)
highest = compare_df.sort_values("gap_score", ascending=False).iloc[0]["term"]

k1.metric("Schemas compared", len(compare_df))
k2.metric("Google-documented", documented_count)
k3.metric("Relevant to niche", industry_count)
k4.metric("Top priority", highest)

tabs = st.tabs(
    [
        "Comparison Overview",
        "Google Rich Result Gap",
        "Niche Gap Finder",
        "Side-by-Side Detail",
        "Trend Comparison",
        "Export"
    ]
)

# =========================================================
# TAB 1 OVERVIEW
# =========================================================

with tabs[0]:
    st.header("Comparison Overview")

    col_a, col_b = st.columns([1.2, 1])

    with col_a:
        fig_score = px.bar(
            compare_df.sort_values("gap_score", ascending=False),
            x="term",
            y="gap_score",
            color="google_gap_type",
            hover_data=[
                "bucket", "adoption_tier", "google_status",
                "google_feature", "industry_relevant", "cms_bias"
            ],
            title="SEO Gap Score by Schema",
            labels={
                "term": "Schema.org Type",
                "gap_score": "SEO Gap Score",
                "google_gap_type": "Gap Type"
            }
        )
        st.plotly_chart(fig_score, use_container_width=True)

    with col_b:
        fig_adoption = px.bar(
            compare_df.sort_values("adoption_tier", ascending=False),
            x="term",
            y="adoption_tier",
            color="bucket",
            title="Public Web Adoption Tier",
            labels={
                "term": "Schema.org Type",
                "adoption_tier": "Adoption Tier"
            }
        )
        st.plotly_chart(fig_adoption, use_container_width=True)

    st.dataframe(
        compare_df[
            [
                "term", "bucket", "adoption_tier", "google_status",
                "google_feature", "industry_relevant", "cms_bias",
                "google_gap_type", "priority", "gap_score"
            ]
        ],
        use_container_width=True
    )

# =========================================================
# TAB 2 GOOGLE RICH RESULT GAP
# =========================================================

with tabs[1]:
    st.header("Google Rich Result Gap")

    st.markdown(
        """
This view highlights whether the selected schemas map to currently documented Google structured data features,
or whether they are mainly semantic Schema.org types without a direct rich-result target.
"""
    )

    status_summary = (
        compare_df.groupby(["google_status"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    fig_status = px.pie(
        status_summary,
        names="google_status",
        values="count",
        title="Google Documentation Status Among Selected Schemas"
    )
    st.plotly_chart(fig_status, use_container_width=True)

    st.subheader("Selected schemas by Google status")

    st.dataframe(
        compare_df[
            [
                "term", "google_status", "google_feature",
                "bucket", "adoption_tier", "priority",
                "gap_score", "gap_note"
            ]
        ].sort_values("gap_score", ascending=False),
        use_container_width=True
    )

    st.subheader("Interpretation")

    for _, row in compare_df.sort_values("gap_score", ascending=False).iterrows():
        st.markdown(make_explanation(row, selected_industry))
        st.divider()

# =========================================================
# TAB 3 NICHE GAP FINDER
# =========================================================

with tabs[2]:
    st.header("Niche Gap Finder")

    st.markdown(
        f"""
For **{selected_industry}**, this section compares your selected schemas against the recommended rich-result and structured data set for the niche.
"""
    )

    recommended = INDUSTRY_RECOMMENDED_SETS[selected_industry]
    recommended_df = df[df["term"].isin(recommended)].copy()
    selected_set = set(selected_terms)

    recommended_df["selected_for_comparison"] = recommended_df["term"].apply(lambda x: x in selected_set)

    missing_recommended = recommended_df[~recommended_df["selected_for_comparison"]].copy()
    selected_recommended = recommended_df[recommended_df["selected_for_comparison"]].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Recommended for niche", len(recommended))
    c2.metric("Selected from recommended set", len(selected_recommended))
    coverage = round((len(selected_recommended) / len(recommended)) * 100, 1) if recommended else 0
    c3.metric("Comparison coverage", f"{coverage}%")

    st.subheader("Recommended schemas for this niche")

    st.dataframe(
        recommended_df[
            [
                "term", "selected_for_comparison", "bucket",
                "adoption_tier", "google_status", "google_feature",
                "google_gap_type", "priority", "gap_score"
            ]
        ].sort_values(["selected_for_comparison", "gap_score"], ascending=[False, False]),
        use_container_width=True
    )

    st.subheader("Possible gaps not selected for comparison")

    if missing_recommended.empty:
        st.success("All recommended niche schemas are included in the comparison.")
    else:
        st.dataframe(
            missing_recommended[
                [
                    "term", "bucket", "adoption_tier", "google_status",
                    "google_feature", "google_gap_type", "priority",
                    "gap_score", "gap_note"
                ]
            ].sort_values("gap_score", ascending=False),
            use_container_width=True
        )

# =========================================================
# TAB 4 SIDE BY SIDE
# =========================================================

with tabs[3]:
    st.header("Side-by-Side Detail")

    cols = st.columns(len(compare_df))

    for idx, (_, row) in enumerate(compare_df.iterrows()):
        with cols[idx]:
            st.subheader(row["term"])
            st.metric("Gap Score", f"{row['gap_score']}/100")
            st.metric("Adoption Tier", int(row["adoption_tier"]))
            st.write(f"**Bucket:** {row['bucket']}")
            st.write(f"**Google:** {row['google_status']}")
            st.write(f"**Feature:** {row['google_feature']}")
            st.write(f"**Niche fit:** {'Yes' if row['industry_relevant'] else 'No'}")
            st.write(f"**CMS bias:** {row['cms_bias']}")
            st.write(f"**Gap type:** {row['google_gap_type']}")
            st.caption(row["gap_note"])

# =========================================================
# TAB 5 TRENDS
# =========================================================

with tabs[4]:
    st.header("Trend Comparison")

    trend_df = all_df[all_df["term"].isin(selected_terms)].copy()
    trend_df = enrich(trend_df, selected_industry)

    if trend_df.empty:
        st.warning("No trend data found for selected schemas.")
    else:
        fig_trend = px.line(
            trend_df.sort_values("month"),
            x="month",
            y="adoption_tier",
            color="term",
            markers=True,
            title="Adoption Tier Trend for Selected Schemas",
            labels={
                "month": "Month",
                "adoption_tier": "Adoption Tier",
                "term": "Schema"
            }
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        pivot = trend_df.pivot_table(
            index="month",
            columns="term",
            values="bucket",
            aggfunc="first"
        ).reset_index()

        st.dataframe(pivot, use_container_width=True)

# =========================================================
# TAB 6 EXPORT
# =========================================================

with tabs[5]:
    st.header("Export")

    export_df = compare_df[
        [
            "term", "term_type", "month", "bucket", "adoption_tier",
            "google_status", "google_feature", "search_intent",
            "industry_relevant", "recommended_for_industry",
            "cms_bias", "google_gap_type", "priority", "gap_score",
            "gap_note"
        ]
    ].sort_values("gap_score", ascending=False)

    st.dataframe(export_df, use_container_width=True)

    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download comparison CSV",
        data=csv,
        file_name=f"schema_comparison_{selected_industry}_{selected_month}.csv",
        mime="text/csv"
    )

    markdown = [
        "# Schema Rich Result Gap Comparison",
        "",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d')}",
        f"Industry: {selected_industry}",
        f"Dataset month: {selected_month}",
        "",
        "## Selected Schemas",
        ", ".join(selected_terms),
        "",
        "## Recommendations",
        "",
    ]

    for _, row in compare_df.sort_values("gap_score", ascending=False).iterrows():
        markdown.append(make_explanation(row, selected_industry))
        markdown.append("")

    markdown_text = "\n".join(markdown)

    st.text_area("Markdown report", markdown_text, height=420)

    st.download_button(
        "Download Markdown report",
        data=markdown_text.encode("utf-8"),
        file_name=f"schema_comparison_{selected_industry}_{selected_month}.md",
        mime="text/markdown"
    )

st.caption(
    "Data source: Schema.org Public Usage Statistics. Google rich-result mapping is an editable knowledge layer based on Google Search structured data documentation."
)
