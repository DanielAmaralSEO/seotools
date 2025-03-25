import streamlit as st
import pandas as pd
import numpy as np
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from statsmodels.tsa.arima.model import ARIMA

# Função para autenticação via OAuth
def authenticate_google_search_console():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gsc_credentials"], scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    return build("searchconsole", "v1", credentials=credentials)

# Função para obter propriedades disponíveis
def get_properties(service):
    sites = service.sites().list().execute()
    return [site['siteUrl'] for site in sites.get('siteEntry', [])]

# Função para obter dados do Search Console
def get_search_console_data(service, site_url, start_date, end_date):
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["date"],
        "rowLimit": 1000
    }
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    
    data = []
    for row in response.get("rows", []):
        data.append([row["keys"][0], row["clicks"], row["impressions"]])
    
    df = pd.DataFrame(data, columns=["date", "clicks", "impressions"])
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df

# Função para previsão com ARIMA
def forecast(data, column, days=30):
    model = ARIMA(data[column], order=(5,1,0))
    model_fit = model.fit()
    forecast_index = pd.date_range(start=data.index[-1] + pd.Timedelta(days=1), periods=days, freq='D')
    forecast_values = model_fit.forecast(steps=days)
    return pd.DataFrame({column: forecast_values}, index=forecast_index)

# Interface do Streamlit
st.title("Previsão de Impressões e Cliques - Google Search Console")

service = authenticate_google_search_console()
properties = get_properties(service)
site_url = st.selectbox("Selecione a propriedade do Search Console", properties)

default_start_date = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
default_end_date = datetime.date.today().strftime("%Y-%m-%d")
start_date = st.date_input("Data de início", datetime.date.fromisoformat(default_start_date))
end_date = st.date_input("Data de fim", datetime.date.fromisoformat(default_end_date))

if st.button("Analisar Dados"):
    df = get_search_console_data(service, site_url, str(start_date), str(end_date))
    st.subheader("Dados Obtidos")
    st.line_chart(df)
    
    st.subheader("Previsão para os próximos 30 dias")
    forecast_clicks = forecast(df, "clicks")
    forecast_impressions = forecast(df, "impressions")
    
    st.line_chart(forecast_clicks)
    st.line_chart(forecast_impressions)
