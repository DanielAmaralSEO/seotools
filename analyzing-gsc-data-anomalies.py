import streamlit as st
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import plotly.express as px

st.set_page_config(page_title="GSC Anomaly Detector (Upload CSV)", layout="wide")

# -----------------------------------------------------------
# HEADER
# -----------------------------------------------------------
st.title("🔍 GSC Anomaly Detector – Upload CSV")
st.write("Faça upload do CSV exportado do Google Search Console para identificar anomalias em *Queries*.")

st.info("📌 **Requisitos do CSV:** deve conter pelo menos as colunas: `Query`, `Date`, `Impressions`, `Clicks`.")

# -----------------------------------------------------------
# UPLOAD
# -----------------------------------------------------------
uploaded_file = st.file_uploader("Faça upload do arquivo CSV exportado do GSC", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Normalizar colunas (GSC às vezes exporta com nomes diferentes)
    df.columns = [col.strip().capitalize() for col in df.columns]

    # Verificação mínima
    required_cols = ["Query", "Date"]
    if not all(col in df.columns for col in required_cols):
        st.error("O CSV precisa ter pelo menos: Query, Date.")
        st.stop()

    # Garantir colunas de métricas
    if "Impressions" not in df.columns:
        df["Impressions"] = 0
    if "Clicks" not in df.columns:
        df["Clicks"] = 0

    df["Date"] = pd.to_datetime(df["Date"])

    st.success("Arquivo carregado com sucesso!")
    st.write("### Amostra do arquivo:")
    st.dataframe(df.head())

    # -----------------------------------------------------------
    # EXCLUSÕES
    # -----------------------------------------------------------
    st.header("🔎 Filtros e Exclusões")

    exclude_terms = st.text_input(
        "Excluir queries contendo (separadas por vírgula)", ""
    ).split(",")

    def apply_exclusions(df):
        df_f = df.copy()
        for term in exclude_terms:
            term = term.strip().lower()
            if term:
                df_f = df_f[~df_f["Query"].str.lower().str.contains(term)]
        return df_f

    df_filtered = apply_exclusions(df)

    # -----------------------------------------------------------
    # FUNÇÃO DE ANOMALIA (GENÉRICA)
    # -----------------------------------------------------------
    def detect_anomalies(df, metric, n_clusters=2):
        df = df.copy()
        df = df[df[metric] > 0]  # remove zeros

        if df.empty:
            return df

        z = (df[metric] - df[metric].mean()) / df[metric].std()
        df[f"{metric}_zscore"] = z

        kmeans = KMeans(n_clusters=n_clusters, n_init="auto")
        df["Cluster"] = kmeans.fit_predict(df[[f"{metric}_zscore"]])

        anomaly_cluster = df.groupby("Cluster")[metric].mean().idxmax()
        df["Anomaly"] = df["Cluster"] == anomaly_cluster

        return df

    # -----------------------------------------------------------
    # ABA DE IMPRESSIONS
    # -----------------------------------------------------------
    st.header("📈 Análise — Impressions")

    df_imp = detect_anomalies(df_filtered, "Impressions")

    if df_imp.empty:
        st.warning("Não há dados suficientes de impressions.")
    else:
        st.dataframe(df_imp[df_imp["Anomaly"]].head())

        fig_imp = px.scatter(
            df_imp,
            x="Date",
            y="Impressions",
            color="Anomaly",
            hover_data=["Query", "Impressions"],
            title="Anomalias em Impressions"
        )
        st.plotly_chart(fig_imp, use_container_width=True)

    # -----------------------------------------------------------
    # ABA DE CLICKS
    # -----------------------------------------------------------
    st.header("📈 Análise — Clicks")

    df_clicks = detect_anomalies(df_filtered, "Clicks")

    if df_clicks.empty:
        st.warning("Não há dados suficientes de clicks.")
    else:
        st.dataframe(df_clicks[df_clicks["Anomaly"]].head())

        fig_clicks = px.scatter(
            df_clicks,
            x="Date",
            y="Clicks",
            color="Anomaly",
            hover_data=["Query", "Clicks"],
            title="Anomalias em Clicks"
        )
        st.plotly_chart(fig_clicks, use_container_width=True)

    # -----------------------------------------------------------
    # DOWNLOAD DOS RESULTADOS
    # -----------------------------------------------------------
    st.header("📥 Baixar Resultados")

    df_imp_export = df_imp[["Query", "Date", "Impressions", "Anomaly"]]
    df_clicks_export = df_clicks[["Query", "Date", "Clicks", "Anomaly"]]

    st.download_button(
        "⬇ Baixar CSV — Anomalias em Impressions",
        df_imp_export.to_csv(index=False),
        file_name="anomalias_impressions.csv",
        mime="text/csv"
    )

    st.download_button(
        "⬇ Baixar CSV — Anomalias em Clicks",
        df_clicks_export.to_csv(index=False),
        file_name="anomalias_clicks.csv",
        mime="text/csv"
    )
