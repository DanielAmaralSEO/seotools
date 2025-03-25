import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from causalimpact import CausalImpact
import yfinance as yf
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import os

# Função para autenticar e acessar o Google Search Console via OAuth
def authenticate_gsc():
    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
    creds = None
    
    # O arquivo token.json armazena o token de acesso e atualização do usuário.
    # Se não houver token válido, o processo de login será feito.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Se não houver credenciais (ou as credenciais expiraram), o usuário deve se autenticar.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)  # Insira o caminho do seu arquivo de credenciais OAuth 2.0
            creds = flow.run_local_server(port=8501)  # A autenticação será feita no navegador
    
        # Salve as credenciais para a próxima vez que o script for executado
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    # Criação do serviço da API
    webmasters_service = build('webmasters', 'v3', credentials=creds)
    return webmasters_service

# Função para obter dados do Google Search Console
def get_gsc_data(start_date, end_date, site_url):
    service = authenticate_gsc()
    request = service.searchanalytics().query(siteUrl=site_url, body={
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': ['date'],
        'rowLimit': 5000
    })
    response = request.execute()
    
    # Organizando os dados em um DataFrame
    data = []
    for row in response['rows']:
        data.append({
            'date': row['keys'][0],
            'clicks': row['clicks'],
            'impressions': row['impressions']
        })
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    return df

# Função para realizar a análise de Causal Impact
def analyze_causal_impact(df, training_start, training_end, treatment_start, treatment_end):
    # Formatar dados para análise
    df.set_index('date', inplace=True)
    y = df['clicks']
    X = df[['impressions']]
    
    # Dividir em treinamento e teste
    pre_period = [training_start, training_end]
    post_period = [treatment_start, treatment_end]
    
    # Realizar o impacto causal
    df_final = pd.concat([y, X], axis=1).dropna()
    impact = CausalImpact(df_final, pre_period, post_period)
    return impact.summary()

# Função Streamlit para interface do usuário
def app():
    st.title('Análise de Impacto Causal com Google Search Console')

    st.write("""
    Este aplicativo permite analisar o impacto causal de um evento em termos de cliques e impressões no Google Search Console.
    Você pode definir o período de treinamento e o período de intervenção.
    """)

    # Coleta de entradas do usuário
    site_url = st.text_input('Insira a URL do seu site:', 'https://www.example.com')
    training_start = st.date_input('Data de início do treinamento:', datetime(2020, 9, 1))
    training_end = st.date_input('Data de fim do treinamento:', datetime(2020, 10, 19))
    treatment_start = st.date_input('Data de início da intervenção:', datetime(2020, 10, 20))
    treatment_end = st.date_input('Data de fim da intervenção:', datetime(2020, 10, 23))

    # Obter os dados do Google Search Console
    if st.button('Obter Dados'):
        with st.spinner('Carregando dados do Google Search Console...'):
            gsc_data = get_gsc_data(str(training_start), str(treatment_end), site_url)
            st.write('Dados carregados com sucesso!')

            # Mostrar os dados obtidos
            st.write(gsc_data.head())

            # Análise de impacto causal
            st.write("Analisando o impacto causal...")
            impact_result = analyze_causal_impact(
                gsc_data, str(training_start), str(training_end), str(treatment_start), str(treatment_end)
            )
            st.write(impact_result)

            # Exibindo o gráfico de impacto causal
            st.write("Gráfico de Impacto Causal:")
            fig, ax = plt.subplots(figsize=(10, 6))
            impact = CausalImpact(gsc_data[['clicks', 'impressions']], [training_start, training_end], [treatment_start, treatment_end])
            impact.plot(ax=ax)
            st.pyplot(fig)

# Iniciar o Streamlit
if __name__ == '__main__':
    app()
