import streamlit as st
import pandas as pd
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import date

st.set_page_config(page_title="GSC Extractor")

st.title("📊 Google Search Console – Extrator de Dados")

# ---------- CONFIG ----------
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Salva credenciais na sessão
if "credentials" not in st.session_state:
    st.session_state["credentials"] = None

# ---------- AUTENTICAÇÃO ----------
def login_button():
    st.subheader("Faça login para continuar")

    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
        redirect_uri=st.secrets["redirect_uri"]
    )
    
    auth_url, state = flow.authorization_url(prompt="consent")

    st.session_state["state"] = state
    st.markdown(f"👉 [Clique aqui para autenticar]({auth_url})")

# Callback para receber o "code"
if "code" in st.query_params:
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=SCOPES,
        redirect_uri=st.secrets["redirect_uri"]
    )
    
    flow.fetch_token(code=st.query_params["code"])
    st.session_state["credentials"] = flow.credentials
    st.success("Autenticado com sucesso! 🎉")

# ---------- INTERFACE PRINCIPAL ----------
if st.session_state["credentials"] is None:
    login_button()
    st.stop()

creds = st.session_state["credentials"]

# GSC API service
service = build("searchconsole", "v1", credentials=creds)

# Lista de propriedades
sites_list = service.sites().list().execute()
valid_sites = [s["siteUrl"] for s in sites_list["siteEntry"] if s["permissionLevel"] != "siteUnverifiedUser"]

st.subheader("Configurações da consulta")

site = st.selectbox("Selecione a propriedade", valid_sites)

start_date = st.date_input("Data inicial", date(2025, 1, 1))
end_date = st.date_input("Data final", date.today())

if st.button("Buscar dados"):
    st.info("Consultando o Search Console, aguarde...")

    body = {
        "startDate": str(start_date),
        "endDate": str(end_date),
        "dimensions": ["date", "query"],
        "rowLimit": 25000
    }

    response = service.searchanalytics().query(siteUrl=site, body=body).execute()

    rows = response.get("rows", [])

    data = []
    for r in rows:
        data.append({
            "date": r["keys"][0],
            "query": r["keys"][1],
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
        })

    df = pd.DataFrame(data)
    st.dataframe(df)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV", csv, "gsc_export.csv", "text/csv")
