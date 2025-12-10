import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import date
import pandas as pd
import json
import tempfile


st.title("Extractor GSC via API (com upload de credenciais)")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


# ---------------------------------------------
# 1 — UPLOAD DO ARQUIVO JSON
# ---------------------------------------------
uploaded_file = st.file_uploader(
    "Faça upload do arquivo client_secret.json",
    type=["json"]
)

if uploaded_file is None:
    st.warning("⚠️ Você precisa enviar o arquivo client_secret.json para continuar.")
    st.stop()


# Salva o arquivo temporariamente
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
    temp_file.write(uploaded_file.read())
    client_secret_path = temp_file.name


# ---------------------------------------------
# 2 — AUTENTICAÇÃO OAUTH
# ---------------------------------------------
if "credentials" not in st.session_state:
    st.session_state["credentials"] = None


def login_button():
    # Cria o fluxo OAuth
    flow = Flow.from_client_secrets_file(
        client_secret_path,
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob"  # funciona em Streamlit
    )

    auth_url, _ = flow.authorization_url(prompt="consent")

    st.markdown(f"### 🔐 Passo 1: Clique para fazer login no Google")
    st.markdown(f"[Autorizar acesso ao Search Console]({auth_url})")

    auth_code = st.text_input("Cole aqui o código de autorização:")

    if st.button("Confirmar código"):
        try:
            flow.fetch_token(code=auth_code)
            st.session_state["credentials"] = flow.credentials
            st.success("🎉 Autenticado com sucesso!")
        except Exception as e:
            st.error(f"Erro na autenticação: {str(e)}")


if st.session_state["credentials"] is None:
    login_button()
    st.stop()

creds = st.session_state["credentials"]


# ---------------------------------------------
# 3 — INTERFACE PARA CONSULTAR O SEARCH CONSOLE
# ---------------------------------------------
st.subheader("Extrair dados do Search Console")

site_url = st.text_input("URL da propriedade (ex: https://www.iclinic.com.br/)")

col1, col2 = st.columns(2)
start_date = col1.date_input("Data inicial", value=date(2024, 1, 1))
end_date = col2.date_input("Data final", value=date.today())

if st.button("Extrair dados"):
    try:
        service = build("searchconsole", "v1", credentials=creds)

        body = {
            "startDate": str(start_date),
            "endDate": str(end_date),
            "dimensions": ["query"],
            "rowLimit": 25000
        }

        response = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=body)
            .execute()
        )

        rows = response.get("rows", [])

        data = []
        for r in rows:
            data.append({
                "date": start_date,  # só volta por período; se quiser diário, ajustamos
                "query": r["keys"][0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0)
            })

        df = pd.DataFrame(data)
        st.dataframe(df)

        st.download_button(
            "Baixar CSV",
            df.to_csv(index=False),
            file_name="gsc_export.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Erro ao buscar dados: {str(e)}")
