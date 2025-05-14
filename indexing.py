import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import httplib2
import json

# Configuração da página
st.set_page_config(page_title="Google Indexing API - Indexação de URLs", layout="centered")
st.title("🔍 Google Indexing API - Indexação de URLs")

# Explicação
st.markdown("""
Este app permite **indexar** ou **desindexar** até 100 URLs diretamente no Google usando a [Indexing API](https://developers.google.com/search/apis/indexing-api/v3/quickstart?hl=pt-br).

**Passos:**
1. Faça o upload do seu arquivo `.json` de credenciais da conta de serviço do Google.
2. Insira até 100 URLs (uma por linha) no campo abaixo.
3. Escolha se deseja indexar ou remover essas URLs do Google.
4. Clique no botão para enviar.
""")

# Upload do arquivo de credenciais
service_account_file = st.file_uploader("🔐 Faça upload do arquivo JSON de credenciais da conta de serviço", type=["json"])

# Campo para inserir URLs
raw_urls = st.text_area("🔗 Insira até 100 URLs (uma por linha):", height=200)

# Seleção de tipo de ação
user_option = st.selectbox("⚙️ Ação desejada para as URLs:", options=["URL_UPDATED", "URL_DELETED"])

# Botão de envio
if st.button("🚀 Enviar para a Indexing API"):
    if not service_account_file:
        st.error("Você precisa enviar o arquivo de credenciais JSON.")
    elif not raw_urls.strip():
        st.error("Você precisa inserir pelo menos uma URL.")
    else:
        try:
            # Lê as credenciais
            SCOPES = ["https://www.googleapis.com/auth/indexing"]
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.load(service_account_file),
                scopes=SCOPES
            )
            http = credentials.authorize(httplib2.Http())
            ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"

            # Processa URLs
            urls = [url.strip() for url in raw_urls.strip().split("\n") if url.strip()]
            if len(urls) > 100:
                st.warning("Atenção: você inseriu mais de 100 URLs. Somente as 100 primeiras serão processadas.")
                urls = urls[:100]

            # Envia cada URL
            results = []
            for url in urls:
                payload = json.dumps({
                    "url": url,
                    "type": user_option
                })
                response, content = http.request(ENDPOINT, method="POST", body=payload)
                result = json.loads(content.decode())

                # Salva resultado
                if "error" in result:
                    results.append(f"❌ Erro com {url}: ({result['error']['status']}) {result['error']['message']}")
                else:
                    notify_time = result['urlNotificationMetadata']['latestUpdate']['notifyTime']
                    results.append(f"✅ {url} enviado com sucesso. Última atualização: {notify_time}")

            # Exibe os resultados
            st.success("Processo finalizado!")
            st.write("### Resultados:")
            for r in results:
                st.write(r)

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar a solicitação: {str(e)}")
