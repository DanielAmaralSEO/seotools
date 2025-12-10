import streamlit as st
from oauth2client.client import OAuth2WebServerFlow
from googleapiclient.discovery import build
import pandas as pd
from sklearn.cluster import KMeans
import numpy as np
import plotly.express as px
import httplib2

st.set_page_config(page_title="GSC Anomaly Detector", layout="wide")

st.title("🔍 Google Search Console – Anomaly Detection (Clicks & Impressions)")
st.write("Detecte anomalias em consultas do Google Search Console usando K-Means.")

# -----------------------------------------------------------
# 1. CREDENCIAIS / AUTENTICAÇÃO
# -----------------------------------------------------------
st.header("1️⃣ Autenticação com Google Search Console")

CLIENT_ID = st.text_input("CLIENT_ID", "")
CLIENT_SECRET = st.text_input("CLIENT_SECRET", "", type="password")
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
OAUTH_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

if CLIENT_ID and CLIENT_SECRET:
    flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URI)
    authorize_url = flow.step1_get_authorize_url()

    st.markdown(f"[Clique para autenticar no Google]({authorize_url})")

    auth_code = st.text_input("Cole aqui o Authorization Code:")

    if auth_code:
        try:
            credentials = flow.step2_exchange(auth_code)
            http = httplib2.Http()
            creds = credentials.authorize(http)
            webmasters_service = build('searchconsole', 'v1', http=creds)
            st.success("✔ Autenticado com sucesso!")
        except Exception as e:
            st.error(f"Erro na autenticação: {e}")
            st.stop()

        # -----------------------------------------------------------
        # 2. LISTAR PROPRIEDADES DO GSC
        # -----------------------------------------------------------
        st.header("2️⃣ Selecione a propriedade do Search Console")

        try:
            site_list = webmasters_service.sites().list().execute()
            sites = [s["siteUrl"] for s in site_list["siteEntry"]]
            site_url = st.selectbox("Selecione o domínio:", sites)
        except:
            st.error("Erro ao carregar propriedades.")
            st.stop()

        # -----------------------------------------------------------
        # 3. INPUT DE DATAS E COLETA DE DADOS
        # -----------------------------------------------------------
        st.header("3️⃣ Carregar dados do GSC")

        col1, col2 = st.columns(2)
        start_date = col1.date_input("Data inicial")
        end_date = col2.date_input("Data final")

        def fetch_gsc_data(site_url, start_date, end_date):
            request = {
                'startDate': str(start_date),
                'endDate': str(end_date),
                'dimensions': ["query", "date"],
                'rowLimit': 25000
            }
            return webmasters_service.searchanalytics().query(
                siteUrl=site_url, body=request
            ).execute().get("rows", [])

        if st.button("Carregar Dados"):
            with st.spinner("Consultando API do Google Search Console..."):
                gsc_data = fetch_gsc_data(site_url, start_date, end_date)

            if not gsc_data:
                st.warning("Nenhum dado encontrado para o período selecionado.")
                st.stop()

            st.success(f"{len(gsc_data)} linhas carregadas!")

            # -----------------------------------------------------------
            # 4. PROCESSAMENTO - IMPRESSIONS
            # -----------------------------------------------------------
            st.header("4️⃣ Processar Impressions e detectar Anomalias")
            queries_to_exclude = st.text_area(
                "Queries para excluir (separadas por vírgula)", ""
            ).split(",")

            def process_gsc_data(gsc_data, exclude_queries):
                data = []
                for row in gsc_data:
                    q, d = row["keys"]
                    imp = row.get("impressions", 0)

                    if any(ex.strip().lower() in q.lower() for ex in exclude_queries if ex):
                        continue

                    data.append([q, d, imp])

                df = pd.DataFrame(data, columns=["Query", "Date", "Impressions"])
                df["Date"] = pd.to_datetime(df["Date"])
                return df

            df = process_gsc_data(gsc_data, queries_to_exclude)

            def identify_anomalies(df):
                df["zscore"] = (df["Impressions"] - df["Impressions"].mean()) / df["Impressions"].std()
                kmeans = KMeans(n_clusters=2, n_init="auto")
                df["Cluster"] = kmeans.fit_predict(df[["zscore"]])
                anomaly_cluster = df.groupby("Cluster")["Impressions"].mean().idxmax()
                df["Anomaly"] = df["Cluster"] == anomaly_cluster
                return df

            df_anom = identify_anomalies(df)

            st.subheader("📌 Amostras de anomalias detectadas")
            st.dataframe(df_anom[df_anom["Anomaly"]].head())

            # -----------------------------------------------------------
            # 5. VISUALIZAÇÃO IMPRESSIONS
            # -----------------------------------------------------------
            st.subheader("📈 Visualização – Anomalias em Impressions")
            fig_imp = px.scatter(
                df_anom,
                x="Date",
                y="Impressions",
                color="Anomaly",
                hover_data=["Query"],
                title="Anomalias em Impressions"
            )
            st.plotly_chart(fig_imp, use_container_width=True)

            # -----------------------------------------------------------
            # 6. VISUALIZAÇÃO CLICKS
            # -----------------------------------------------------------
            st.header("5️⃣ Processar Clicks e detectar Anomalias")

            def process_click_data(gsc_data, exclude_queries):
                data = []
                for row in gsc_data:
                    q, d = row["keys"]
                    clicks = row.get("clicks", 0)

                    if clicks <= 0:
                        continue
                    if any(ex.strip().lower() in q.lower() for ex in exclude_queries if ex):
                        continue

                    data.append([q, d, clicks])

                df = pd.DataFrame(data, columns=["Query", "Date", "Clicks"])
                df["Date"] = pd.to_datetime(df["Date"])
                return df

            df_clicks = process_click_data(gsc_data, queries_to_exclude)

            def identify_anomalies_clicks(df):
                df["zscore"] = (df["Clicks"] - df["Clicks"].mean()) / df["Clicks"].std()
                kmeans = KMeans(n_clusters=2, n_init="auto")
                df["Cluster"] = kmeans.fit_predict(df[["zscore"]])
                anomaly_cluster = df.groupby("Cluster")["Clicks"].mean().idxmax()
                df["Anomaly"] = df["Cluster"] == anomaly_cluster
                return df

            df_anom_clicks = identify_anomalies_clicks(df_clicks)

            st.subheader("📌 Amostras de anomalias em Clicks")
            st.dataframe(df_anom_clicks[df_anom_clicks["Anomaly"]].head())

            fig_clicks = px.scatter(
                df_anom_clicks,
                x="Date",
                y="Clicks",
                color="Anomaly",
                hover_data=["Query"],
                title="Anomalias em Clicks"
            )
            st.plotly_chart(fig_clicks, use_container_width=True)

            st.success("✔ Análise concluída!")

