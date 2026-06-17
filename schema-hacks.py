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
    page_title="Schema SEO Intelligence",
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

BUCKET_LABELS = {
    1: "< 1K domains",
    2: "1K - 10K domains",
    3: "10K - 100K domains",
    4: "100K - 1M domains",
    5: "> 1M domains",
}

# This is an editable SEO knowledge layer.
# It should be maintained over time as Google Search documentation changes.
SEO_SCHEMA_LIBRARY = {
    "Product": {
        "search_feature": "Product snippets / Merchant listings",
        "rich_result_status": "Supported",
        "business_value": 5,
        "plugin_bias": "High",
        "templates": ["Product page", "Category page"],
        "industries": ["Ecommerce", "Marketplace", "SaaS"],
        "why_it_matters": "Commercially important. Often tied to price, availability, reviews, and merchant experiences.",
        "implementation_note": "Prioritize completeness: name, image, description, offers, price, availability, brand, sku, aggregateRating when visible.",
    },
    "Offer": {
        "search_feature": "Product snippets / Merchant listings",
        "rich_result_status": "Supported",
        "business_value": 5,
        "plugin_bias": "Medium",
        "templates": ["Product page"],
        "industries": ["Ecommerce", "Marketplace"],
        "why_it_matters": "Essential for commercial pages where price and availability are visible.",
        "implementation_note": "Use inside Product where possible. Keep price and availability synchronized with visible page content.",
    },
    "AggregateRating": {
        "search_feature": "Review snippets / Product snippets",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "Medium",
        "templates": ["Product page", "Review page", "Location page"],
        "industries": ["Ecommerce", "Marketplace", "Local Business", "Entertainment", "Education"],
        "why_it_matters": "Can support review/rating visibility when ratings are genuine and visible.",
        "implementation_note": "Only mark up ratings that users can see on the page. Avoid self-serving review misuse.",
    },
    "Review": {
        "search_feature": "Review snippets",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "Medium",
        "templates": ["Product page", "Review page", "Location page"],
        "industries": ["Ecommerce", "Marketplace", "Local Business", "Entertainment"],
        "why_it_matters": "Useful where reviews are a core part of the page experience.",
        "implementation_note": "Reviews must be genuine, visible, and tied to the reviewed item.",
    },
    "BreadcrumbList": {
        "search_feature": "Breadcrumbs",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "High",
        "templates": ["All templates"],
        "industries": ["Ecommerce", "Marketplace", "Publisher", "Local Business", "SaaS", "Education", "Healthcare", "Entertainment"],
        "why_it_matters": "Foundational technical SEO markup for site architecture and SERP breadcrumb display.",
        "implementation_note": "Usually safe and high-coverage. Audit template consistency and canonical hierarchy.",
    },
    "Organization": {
        "search_feature": "Organization / Logo",
        "rich_result_status": "Supported",
        "business_value": 3,
        "plugin_bias": "High",
        "templates": ["Homepage", "About page"],
        "industries": ["Ecommerce", "Marketplace", "Publisher", "Local Business", "SaaS", "Education", "Healthcare", "Entertainment"],
        "why_it_matters": "Helps describe the brand/entity behind the site.",
        "implementation_note": "Use stable sameAs links, logo, name, url, contactPoint when appropriate.",
    },
    "LocalBusiness": {
        "search_feature": "Local business rich results",
        "rich_result_status": "Supported",
        "business_value": 5,
        "plugin_bias": "Medium",
        "templates": ["Homepage", "Location page"],
        "industries": ["Local Business", "Healthcare"],
        "why_it_matters": "Critical for businesses with physical locations or service areas.",
        "implementation_note": "Validate NAP consistency, openingHours, address, geo, telephone, and location-specific pages.",
    },
    "Article": {
        "search_feature": "Article rich results",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "High",
        "templates": ["Article page", "Blog post"],
        "industries": ["Publisher", "Education", "Healthcare", "SaaS"],
        "why_it_matters": "Core markup for editorial pages and blogs.",
        "implementation_note": "Audit headline, image, author, datePublished, dateModified, publisher.",
    },
    "NewsArticle": {
        "search_feature": "Article rich results",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "Medium",
        "templates": ["News article"],
        "industries": ["Publisher"],
        "why_it_matters": "Important for news publishers and timely editorial content.",
        "implementation_note": "Use only for actual news content. Keep dates and authors accurate.",
    },
    "VideoObject": {
        "search_feature": "Video rich results",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "Medium",
        "templates": ["Video page", "Article page", "Product page", "Course page"],
        "industries": ["Publisher", "Education", "Entertainment", "SaaS", "Ecommerce"],
        "why_it_matters": "High value when video is a meaningful page asset.",
        "implementation_note": "Audit thumbnailUrl, uploadDate, duration, name, description, embedUrl/contentUrl.",
    },
    "Event": {
        "search_feature": "Event rich results",
        "rich_result_status": "Supported",
        "business_value": 5,
        "plugin_bias": "Low",
        "templates": ["Event page"],
        "industries": ["Local Business", "Education", "Entertainment", "Publisher"],
        "why_it_matters": "Highly actionable when a site publishes real events.",
        "implementation_note": "Use for real events with dates, locations, ticket/offer data where visible.",
    },
    "JobPosting": {
        "search_feature": "Job posting rich results",
        "rich_result_status": "Supported",
        "business_value": 5,
        "plugin_bias": "Low",
        "templates": ["Job page"],
        "industries": ["Marketplace", "SaaS", "Education"],
        "why_it_matters": "Very actionable for career sites and job boards.",
        "implementation_note": "Audit hiringOrganization, jobLocation, datePosted, validThrough, employmentType, salary when visible.",
    },
    "Course": {
        "search_feature": "Course info",
        "rich_result_status": "Supported",
        "business_value": 5,
        "plugin_bias": "Low",
        "templates": ["Course page"],
        "industries": ["Education"],
        "why_it_matters": "High relevance for education businesses and course catalogs.",
        "implementation_note": "Keep course name, provider, description, and offer details aligned with visible content.",
    },
    "Recipe": {
        "search_feature": "Recipe rich results",
        "rich_result_status": "Supported",
        "business_value": 5,
        "plugin_bias": "Medium",
        "templates": ["Recipe page"],
        "industries": ["Publisher"],
        "why_it_matters": "Highly relevant for recipe publishers.",
        "implementation_note": "Audit ingredients, instructions, images, cookTime, prepTime, nutrition when visible.",
    },
    "SoftwareApplication": {
        "search_feature": "Software app rich results",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "Low",
        "templates": ["App page", "Software product page"],
        "industries": ["SaaS"],
        "why_it_matters": "Useful for SaaS, app stores, tools, and software directories.",
        "implementation_note": "Audit operatingSystem, applicationCategory, offers, aggregateRating when visible.",
    },
    "Dataset": {
        "search_feature": "Dataset search",
        "rich_result_status": "Supported",
        "business_value": 3,
        "plugin_bias": "Low",
        "templates": ["Dataset page", "Research page"],
        "industries": ["Education", "Publisher", "SaaS"],
        "why_it_matters": "Useful for public data, research, and downloadable datasets.",
        "implementation_note": "Use when there is a real dataset, not just a normal article.",
    },
    "FAQPage": {
        "search_feature": "FAQ rich results",
        "rich_result_status": "Limited / deprecated in many contexts",
        "business_value": 2,
        "plugin_bias": "High",
        "templates": ["FAQ page", "Support page"],
        "industries": ["Ecommerce", "SaaS", "Education", "Healthcare", "Local Business"],
        "why_it_matters": "Still semantically valid, but often overused and no longer a reliable rich-result lever.",
        "implementation_note": "Use only when FAQs are visible and useful. Do not prioritize over more actionable schema.",
    },
    "HowTo": {
        "search_feature": "How-to rich results",
        "rich_result_status": "Limited / deprecated in many contexts",
        "business_value": 2,
        "plugin_bias": "Medium",
        "templates": ["Guide page", "Support page"],
        "industries": ["Publisher", "Education", "SaaS"],
        "why_it_matters": "Useful for instructional content but not as strong as it once was for rich-result visibility.",
        "implementation_note": "Use only for genuine step-by-step content visible on the page.",
    },
    "Person": {
        "search_feature": "No direct Search enhancement",
        "rich_result_status": "Semantic only",
        "business_value": 3,
        "plugin_bias": "Medium",
        "templates": ["Author page", "Bio page", "Article page"],
        "industries": ["Publisher", "Education", "Healthcare"],
        "why_it_matters": "Useful for author/entity clarity, especially expert-led content.",
        "implementation_note": "Use for real authors, experts, doctors, instructors, and contributors.",
    },
    "TVSeries": {
        "search_feature": "No direct Search enhancement",
        "rich_result_status": "Semantic only",
        "business_value": 3,
        "plugin_bias": "Low",
        "templates": ["Series page"],
        "industries": ["Entertainment"],
        "why_it_matters": "Relevant for entertainment catalogs and entity architecture.",
        "implementation_note": "Pair with TVSeason, TVEpisode, VideoObject, Review, and AggregateRating where applicable.",
    },
    "TVSeason": {
        "search_feature": "No direct Search enhancement",
        "rich_result_status": "Semantic only",
        "business_value": 2,
        "plugin_bias": "Low",
        "templates": ["Season page"],
        "industries": ["Entertainment"],
        "why_it_matters": "Useful where season-level pages exist.",
        "implementation_note": "Do not implement unless the site has dedicated season pages or clear season entities.",
    },
    "TVEpisode": {
        "search_feature": "No direct Search enhancement",
        "rich_result_status": "Semantic only",
        "business_value": 2,
        "plugin_bias": "Low",
        "templates": ["Episode page"],
        "industries": ["Entertainment"],
        "why_it_matters": "Useful for episode-level catalogs.",
        "implementation_note": "Pair with VideoObject when pages include playable video or episode metadata.",
    },
    "Movie": {
        "search_feature": "Movie rich results",
        "rich_result_status": "Supported",
        "business_value": 4,
        "plugin_bias": "Low",
        "templates": ["Movie page"],
        "industries": ["Entertainment"],
        "why_it_matters": "Relevant for movie catalogs, streaming libraries, and entertainment databases.",
        "implementation_note": "Audit name, image, dateCreated, director, actor, aggregateRating when visible.",
    },
}

INDUSTRY_EXPECTED_SCHEMAS = {
    "Ecommerce": ["Product", "Offer", "AggregateRating", "Review", "BreadcrumbList", "Organization", "FAQPage", "VideoObject"],
    "Marketplace": ["Product", "Offer", "AggregateRating", "Review", "Organization", "BreadcrumbList", "JobPosting"],
    "Publisher": ["Article", "NewsArticle", "Person", "Organization", "BreadcrumbList", "VideoObject", "FAQPage", "Dataset"],
    "Local Business": ["LocalBusiness", "Organization", "BreadcrumbList", "Review", "AggregateRating", "Event", "FAQPage"],
    "SaaS": ["SoftwareApplication", "Organization", "Product", "FAQPage", "HowTo", "VideoObject", "BreadcrumbList", "Article"],
    "Education": ["Course", "Article", "Person", "Organization", "FAQPage", "VideoObject", "Dataset", "BreadcrumbList", "Event"],
    "Healthcare": ["LocalBusiness", "Person", "Article", "FAQPage", "BreadcrumbList", "Organization", "Review"],
    "Entertainment": ["TVSeries", "TVSeason", "TVEpisode", "Movie", "VideoObject", "Review", "AggregateRating", "BreadcrumbList"],
}

TEMPLATE_MAP = {
    "Homepage": ["Organization", "WebSite", "BreadcrumbList"],
    "Product page": ["Product", "Offer", "AggregateRating", "Review", "BreadcrumbList", "VideoObject", "FAQPage"],
    "Category page": ["BreadcrumbList", "ItemList", "CollectionPage", "Product"],
    "Article page": ["Article", "Person", "Organization", "BreadcrumbList", "VideoObject", "FAQPage"],
    "Location page": ["LocalBusiness", "Organization", "BreadcrumbList", "Review", "AggregateRating"],
    "Course page": ["Course", "Organization", "Person", "VideoObject", "BreadcrumbList", "FAQPage"],
    "Event page": ["Event", "Organization", "Offer", "BreadcrumbList"],
    "Job page": ["JobPosting", "Organization", "BreadcrumbList"],
    "Video page": ["VideoObject", "Organization", "BreadcrumbList"],
    "Series page": ["TVSeries", "TVSeason", "TVEpisode", "VideoObject", "BreadcrumbList"],
}

PLUGIN_DEFAULT_TYPES = {
    "Organization", "WebSite", "WebPage", "BreadcrumbList", "Article", "Product", "FAQPage", "Person", "SearchAction"
}

SUPPORTED_TYPES = {
    term for term, meta in SEO_SCHEMA_LIBRARY.items()
    if meta["rich_result_status"] == "Supported"
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

def parse_terms_from_text(text):
    if not text:
        return []
    separators = [",", "\n", ";", "|", "\t"]
    for sep in separators[1:]:
        text = text.replace(sep, ",")
    terms = [normalize_term(x) for x in text.split(",") if normalize_term(x)]
    return sorted(set(terms))

@st.cache_data(ttl=3600)
def get_csv_files():
    try:
        response = requests.get(GITHUB_API_URL, timeout=20)
        if response.status_code != 200:
            return [FALLBACK_FILE]
        files = response.json()
        csv_files = sorted([
            item.get("name")
            for item in files
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
    required = ["Class", "Name", "Domain Bucket"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    df = df.copy()
    df["month"] = file_name.replace(".csv", "")
    df["term_type"] = df["Class"].astype(str).str.strip()
    df["term"] = df["Name"].apply(normalize_term)
    df["bucket"] = df["Domain Bucket"].apply(normalize_bucket)
    df["adoption_tier"] = df["bucket"].map(BUCKET_ORDER).fillna(0).astype(int)

    return df[["month", "term_type", "term", "bucket", "adoption_tier"]]

@st.cache_data(ttl=3600)
def load_all_data():
    files = get_csv_files()
    frames = []
    failed = []

    for file_name in files:
        try:
            frames.append(load_month(file_name))
        except Exception as exc:
            failed.append((file_name, str(exc)))

    if not frames:
        st.error("No Schema.org public usage CSV could be loaded.")
        st.stop()

    return pd.concat(frames, ignore_index=True), files, failed

# =========================================================
# SEO ENRICHMENT
# =========================================================

def get_meta(term, key, default):
    return SEO_SCHEMA_LIBRARY.get(term, {}).get(key, default)

def bias_penalty(label):
    if label == "High":
        return 15
    if label == "Medium":
        return 8
    if label == "Low":
        return 0
    return 4

def rich_result_points(status):
    if status == "Supported":
        return 30
    if status.startswith("Limited"):
        return 10
    if status == "Semantic only":
        return 5
    return 0

def classify_score(score):
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"

def seo_bucket_label(row):
    term = row["term"]
    tier = row["adoption_tier"]
    status = row["rich_result_status"]
    bias = row["plugin_bias"]

    if status == "Supported" and tier >= 4:
        return "Operational priority"
    if status == "Supported" and tier <= 3:
        return "Hidden opportunity"
    if tier >= 4 and bias == "High":
        return "Commodity / plugin-default markup"
    if status.startswith("Limited"):
        return "Use with caution"
    if status == "Semantic only" and tier >= 3:
        return "Semantic architecture"
    if tier <= 2:
        return "Niche / emerging"
    return "Investigate"

def enrich(df, industry):
    df = df.copy()

    df["rich_result_status"] = df["term"].apply(lambda x: get_meta(x, "rich_result_status", "Unknown"))
    df["search_feature"] = df["term"].apply(lambda x: get_meta(x, "search_feature", "No known mapping"))
    df["business_value"] = df["term"].apply(lambda x: get_meta(x, "business_value", 1))
    df["plugin_bias"] = df["term"].apply(lambda x: get_meta(x, "plugin_bias", "High" if x in PLUGIN_DEFAULT_TYPES else "Unknown"))
    df["why_it_matters"] = df["term"].apply(lambda x: get_meta(x, "why_it_matters", "No curated SEO note yet. Treat this as raw adoption data."))
    df["implementation_note"] = df["term"].apply(lambda x: get_meta(x, "implementation_note", "Validate against page content, Google guidelines, and business relevance."))

    df["industry_match"] = df["term"].apply(
        lambda x: industry in get_meta(x, "industries", [])
    )
    df["expected_for_industry"] = df["term"].apply(
        lambda x: x in INDUSTRY_EXPECTED_SCHEMAS.get(industry, [])
    )

    df["seo_actionability_score"] = (
        df["adoption_tier"] * 8
        + df["business_value"] * 7
        + df["rich_result_status"].apply(rich_result_points)
        + df["industry_match"].astype(int) * 15
        + df["expected_for_industry"].astype(int) * 15
        - df["plugin_bias"].apply(bias_penalty)
    ).clip(lower=0, upper=100).round(0).astype(int)

    df["seo_priority"] = df["seo_actionability_score"].apply(classify_score)
    df["seo_lens"] = df.apply(seo_bucket_label, axis=1)

    return df

def generate_executive_recommendation(row, industry, detected_terms=None):
    detected_terms = detected_terms or []
    term = row["term"]
    status = row["rich_result_status"]
    tier = row["adoption_tier"]
    score = row["seo_actionability_score"]
    priority = row["seo_priority"]
    detected = term in detected_terms

    present_text = "already appears in your detected schema list" if detected else "does not appear in your detected schema list"

    recommendation = f"""
### {term}

**SEO Priority:** {priority}  
**SEO Actionability Score:** {score}/100  
**Public Web Adoption:** Tier {tier} ({BUCKET_LABELS.get(tier, "Unknown bucket")})  
**Google Search Feature Mapping:** {row["search_feature"]}  
**Rich Result Status:** {status}  
**Your Site Status:** {term} {present_text}

**Why this matters:**  
{row["why_it_matters"]}

**Recommended action:**  
{row["implementation_note"]}
"""

    if not detected and row["expected_for_industry"]:
        recommendation += "\n**Gap finding:** This schema is part of the expected benchmark set for this industry. Review the relevant templates.\n"
    elif detected:
        recommendation += "\n**Audit finding:** Since this schema is already detected, focus on completeness, validation errors, duplication, and alignment with visible content.\n"

    if row["plugin_bias"] == "High":
        recommendation += "\n**Caution:** High adoption may be inflated by CMS/plugin defaults. Do not treat popularity alone as proof of SEO value.\n"

    return recommendation.strip()

# =========================================================
# LOAD DATA
# =========================================================

all_df, available_files, failed_files = load_all_data()
available_months = sorted(all_df["month"].unique(), reverse=True)

# =========================================================
# UI
# =========================================================

st.title("🧠 Schema SEO Intelligence")
st.markdown(
    """
A decision-focused structured data audit tool for SEO professionals.

It combines Schema.org public usage buckets with an editable SEO knowledge layer:
rich-result relevance, implementation bias, template coverage, industry benchmarks, and audit recommendations.
"""
)

st.caption(
    "Note: Schema.org usage buckets show public-web adoption, not ranking impact or guaranteed rich results."
)

st.sidebar.header("Audit Settings")

selected_month = st.sidebar.selectbox(
    "Dataset month",
    available_months,
    key="selected_month"
)

selected_industry = st.sidebar.selectbox(
    "Industry / site type",
    list(INDUSTRY_EXPECTED_SCHEMAS.keys()),
    key="selected_industry"
)

selected_templates = st.sidebar.multiselect(
    "Templates to audit",
    list(TEMPLATE_MAP.keys()),
    default=["Homepage", "Product page"] if selected_industry == "Ecommerce" else ["Homepage", "Article page"],
    key="selected_templates"
)

raw_detected_schemas = st.sidebar.text_area(
    "Paste schemas already detected on the site",
    value="",
    placeholder="Example: Organization, WebSite, BreadcrumbList, Product",
    height=120,
    key="detected_schemas"
)

detected_terms = parse_terms_from_text(raw_detected_schemas)

base_df = all_df[all_df["month"] == selected_month].copy()
df = enrich(base_df, selected_industry)

with st.sidebar.expander("Dataset health"):
    st.write("Rows:", len(df))
    st.write("Months available:", len(available_months))
    st.write("CSV files found:", len(available_files))
    if failed_files:
        st.write("Files skipped:", len(failed_files))
    st.write("Sample terms:", df["term"].head(10).tolist())

# =========================================================
# KPI HEADER
# =========================================================

types_df = df[df["term_type"].str.lower() == "type"].copy()
known_df = df[df["term"].isin(SEO_SCHEMA_LIBRARY.keys())].copy()
supported_df = df[df["rich_result_status"] == "Supported"].copy()
expected_terms = INDUSTRY_EXPECTED_SCHEMAS[selected_industry]
expected_df = df[df["term"].isin(expected_terms)].copy()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("Schema terms loaded", f"{len(df):,}")
kpi2.metric("Types loaded", f"{len(types_df):,}")
kpi3.metric("Curated SEO mappings", f"{len(known_df):,}")
kpi4.metric("Industry benchmark terms", len(expected_terms))

tabs = st.tabs([
    "Executive Dashboard",
    "Template Gap Audit",
    "SEO Priority Matrix",
    "Opportunity Finder",
    "Compare Schemas",
    "Trend Watch",
    "Export Report",
    "Raw Explorer"
])

# =========================================================
# TAB 1 EXECUTIVE
# =========================================================

with tabs[0]:
    st.header("Executive Dashboard")

    st.markdown(
        """
Use this page to move from a generic schema discussion to an implementation roadmap.
The most useful question is not “which schema is most popular?”, but “which schema is missing from important templates and has a clear SEO use case?”
"""
    )

    priority_counts = (
        df.groupby("seo_priority")
        .size()
        .reset_index(name="count")
    )

    lens_counts = (
        df.groupby("seo_lens")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    col_a, col_b = st.columns(2)

    with col_a:
        fig_priority = px.bar(
            priority_counts,
            x="seo_priority",
            y="count",
            title="SEO Priority Distribution",
            labels={"seo_priority": "Priority", "count": "Terms"}
        )
        st.plotly_chart(fig_priority, use_container_width=True)

    with col_b:
        fig_lens = px.bar(
            lens_counts,
            x="seo_lens",
            y="count",
            title="SEO Lens Distribution",
            labels={"seo_lens": "SEO Lens", "count": "Terms"}
        )
        st.plotly_chart(fig_lens, use_container_width=True)

    st.subheader("Top action candidates")

    top_candidates = df[
        (df["term_type"].str.lower() == "type")
        & (df["seo_priority"].isin(["Critical", "High"]))
    ].sort_values("seo_actionability_score", ascending=False)

    st.dataframe(
        top_candidates[
            [
                "term", "bucket", "adoption_tier", "seo_priority",
                "seo_actionability_score", "rich_result_status",
                "search_feature", "plugin_bias", "seo_lens"
            ]
        ].head(50),
        use_container_width=True
    )

# =========================================================
# TAB 2 GAP AUDIT
# =========================================================

with tabs[1]:
    st.header("Template Gap Audit")

    st.markdown(
        """
Paste the schemas already detected on a site in the sidebar.
This tab compares them against the expected schema set for the selected industry and templates.
"""
    )

    template_expected = set()
    for template in selected_templates:
        template_expected.update(TEMPLATE_MAP.get(template, []))

    industry_expected = set(expected_terms)
    audit_expected = sorted(industry_expected.union(template_expected))

    audit_df = df[df["term"].isin(audit_expected)].copy()

    detected_set = set(detected_terms)
    audit_df["site_status"] = audit_df["term"].apply(
        lambda x: "Detected" if x in detected_set else "Missing"
    )

    missing_df = audit_df[audit_df["site_status"] == "Missing"].copy()
    detected_df = audit_df[audit_df["site_status"] == "Detected"].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected schemas", len(audit_expected))
    c2.metric("Detected", len(detected_df))
    c3.metric("Missing", len(missing_df))
    coverage = round((len(detected_df) / len(audit_expected)) * 100, 1) if audit_expected else 0
    c4.metric("Coverage", f"{coverage}%")

    st.subheader("Missing schemas prioritized by SEO value")

    if missing_df.empty:
        st.success("No missing schemas from the selected benchmark set.")
    else:
        st.dataframe(
            missing_df[
                [
                    "term", "seo_priority", "seo_actionability_score",
                    "bucket", "rich_result_status", "search_feature",
                    "plugin_bias", "seo_lens", "implementation_note"
                ]
            ].sort_values("seo_actionability_score", ascending=False),
            use_container_width=True
        )

    st.subheader("Detected schemas to audit for quality")

    if detected_df.empty:
        st.info("No detected schemas were provided in the sidebar.")
    else:
        st.dataframe(
            detected_df[
                [
                    "term", "seo_priority", "seo_actionability_score",
                    "bucket", "rich_result_status", "search_feature",
                    "plugin_bias", "implementation_note"
                ]
            ].sort_values("seo_actionability_score", ascending=False),
            use_container_width=True
        )

# =========================================================
# TAB 3 MATRIX
# =========================================================

with tabs[2]:
    st.header("SEO Priority Matrix")

    matrix_df = df[df["term_type"].str.lower() == "type"].copy()

    fig_matrix = px.scatter(
        matrix_df,
        x="adoption_tier",
        y="seo_actionability_score",
        size="business_value",
        color="seo_lens",
        hover_name="term",
        hover_data=["bucket", "rich_result_status", "search_feature", "plugin_bias", "seo_priority"],
        title="Adoption vs SEO Actionability",
        labels={
            "adoption_tier": "Public Web Adoption Tier",
            "seo_actionability_score": "SEO Actionability Score"
        }
    )
    st.plotly_chart(fig_matrix, use_container_width=True)

    st.info(
        "High adoption is not automatically high SEO value. Some types are common because CMSs and plugins ship them by default."
    )

# =========================================================
# TAB 4 OPPORTUNITY
# =========================================================

with tabs[3]:
    st.header("Opportunity Finder")

    st.subheader("Hidden opportunities")
    hidden = df[
        (df["term_type"].str.lower() == "type")
        & (df["seo_lens"] == "Hidden opportunity")
    ].sort_values("seo_actionability_score", ascending=False)

    st.dataframe(
        hidden[
            [
                "term", "bucket", "adoption_tier", "seo_priority",
                "seo_actionability_score", "rich_result_status",
                "search_feature", "implementation_note"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Operational priorities")
    operational = df[
        (df["term_type"].str.lower() == "type")
        & (df["seo_lens"] == "Operational priority")
    ].sort_values("seo_actionability_score", ascending=False)

    st.dataframe(
        operational[
            [
                "term", "bucket", "adoption_tier", "seo_priority",
                "seo_actionability_score", "rich_result_status",
                "search_feature", "plugin_bias"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Commodity / plugin-default markup")
    commodity = df[
        (df["term_type"].str.lower() == "type")
        & (df["seo_lens"] == "Commodity / plugin-default markup")
    ].sort_values("adoption_tier", ascending=False)

    st.dataframe(
        commodity[
            [
                "term", "bucket", "adoption_tier", "plugin_bias",
                "rich_result_status", "search_feature", "why_it_matters"
            ]
        ],
        use_container_width=True
    )

# =========================================================
# TAB 5 COMPARE
# =========================================================

with tabs[4]:
    st.header("Compare Schemas")

    compare_input = st.text_area(
        "Enter Schema.org terms separated by commas or new lines",
        value="TVSeries, TVSeason, TVEpisode, VideoObject, Movie",
        key="compare_input"
    )

    compare_terms = parse_terms_from_text(compare_input)
    compare_df = df[df["term"].isin(compare_terms)].copy()

    missing_compare = [term for term in compare_terms if term not in compare_df["term"].tolist()]

    if compare_df.empty:
        st.warning("No matching terms found.")
    else:
        fig_compare = px.bar(
            compare_df.sort_values("seo_actionability_score", ascending=False),
            x="term",
            y="seo_actionability_score",
            color="seo_lens",
            hover_data=["bucket", "adoption_tier", "rich_result_status", "search_feature", "plugin_bias"],
            title="Schema Comparison by SEO Actionability"
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        st.dataframe(
            compare_df[
                [
                    "term", "term_type", "bucket", "adoption_tier",
                    "seo_priority", "seo_actionability_score",
                    "rich_result_status", "search_feature",
                    "plugin_bias", "why_it_matters", "implementation_note"
                ]
            ].sort_values("seo_actionability_score", ascending=False),
            use_container_width=True
        )

    if missing_compare:
        st.info("Not found in selected dataset month: " + ", ".join(missing_compare))

# =========================================================
# TAB 6 TREND
# =========================================================

with tabs[5]:
    st.header("Trend Watch")

    all_terms = sorted(all_df["term"].dropna().unique())
    default_term = "Product" if "Product" in all_terms else all_terms[0]

    trend_term = st.selectbox(
        "Choose a term",
        all_terms,
        index=all_terms.index(default_term),
        key="trend_term"
    )

    trend_df = all_df[all_df["term"] == trend_term].sort_values("month").copy()
    trend_df = enrich(trend_df, selected_industry)

    if trend_df.empty:
        st.warning("No trend data available.")
    else:
        fig_trend = px.line(
            trend_df,
            x="month",
            y="adoption_tier",
            markers=True,
            title=f"Adoption Trend: {trend_term}",
            labels={"month": "Month", "adoption_tier": "Adoption Tier"}
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        st.dataframe(
            trend_df[
                [
                    "month", "term", "bucket", "adoption_tier",
                    "seo_lens", "seo_actionability_score", "rich_result_status"
                ]
            ],
            use_container_width=True
        )

        if len(trend_df) >= 2:
            first = trend_df.iloc[0]["adoption_tier"]
            last = trend_df.iloc[-1]["adoption_tier"]
            if last > first:
                st.success("Trend signal: adoption moved up a bucket.")
            elif last < first:
                st.warning("Trend signal: adoption moved down a bucket.")
            else:
                st.info("Trend signal: adoption remained in the same bucket.")

# =========================================================
# TAB 7 EXPORT
# =========================================================

with tabs[6]:
    st.header("Export Report")

    report_scope = st.radio(
        "Report scope",
        ["Industry benchmark", "Missing schemas", "All prioritized schemas"],
        horizontal=True,
        key="report_scope"
    )

    if report_scope == "Industry benchmark":
        report_df = df[df["term"].isin(expected_terms)].copy()
    elif report_scope == "Missing schemas":
        template_expected = set()
        for template in selected_templates:
            template_expected.update(TEMPLATE_MAP.get(template, []))
        audit_expected = sorted(set(expected_terms).union(template_expected))
        report_df = df[df["term"].isin(audit_expected)].copy()
        report_df = report_df[~report_df["term"].isin(detected_terms)]
    else:
        report_df = df[df["term_type"].str.lower() == "type"].copy()

    report_df = report_df.sort_values("seo_actionability_score", ascending=False)

    st.dataframe(
        report_df[
            [
                "term", "term_type", "bucket", "adoption_tier",
                "seo_priority", "seo_actionability_score",
                "rich_result_status", "search_feature",
                "plugin_bias", "seo_lens",
                "why_it_matters", "implementation_note"
            ]
        ],
        use_container_width=True
    )

    csv_data = report_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV report",
        data=csv_data,
        file_name=f"schema_seo_intelligence_{selected_industry}_{selected_month}.csv",
        mime="text/csv"
    )

    st.subheader("Markdown executive summary")

    summary_rows = report_df.head(10)
    markdown_parts = [
        f"# Schema SEO Intelligence Report",
        f"",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d')}",
        f"Industry: {selected_industry}",
        f"Dataset month: {selected_month}",
        f"",
        f"## Top Recommendations",
    ]

    for _, row in summary_rows.iterrows():
        markdown_parts.append(generate_executive_recommendation(row, selected_industry, detected_terms))
        markdown_parts.append("")

    markdown_report = "\n".join(markdown_parts)
    st.text_area("Copy report", markdown_report, height=420)

    st.download_button(
        "Download Markdown report",
        data=markdown_report.encode("utf-8"),
        file_name=f"schema_seo_intelligence_{selected_industry}_{selected_month}.md",
        mime="text/markdown"
    )

# =========================================================
# TAB 8 RAW
# =========================================================

with tabs[7]:
    st.header("Raw Explorer")

    raw_search = st.text_input("Search raw term", value="", key="raw_search")

    raw_df = df.copy()

    if raw_search:
        raw_df = raw_df[raw_df["term"].str.contains(raw_search, case=False, na=False)]

    st.dataframe(
        raw_df.sort_values(["adoption_tier", "term"], ascending=[False, True]),
        use_container_width=True
    )

st.caption(
    "Data source: Schema.org Public Usage Statistics. SEO mappings are editable and should be maintained against current Google Search documentation."
)
