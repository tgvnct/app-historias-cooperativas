# streamlit_app.py
import streamlit as st
import cohere, random, re, os
import gspread
from google.oauth2.service_account import Credentials

# --- CONSTANTES E CONFIGURAÇÕES ------------------------------------
AUTORES = [
    "Machado de Assis",
    "Guimarães Rosa",
    "Jorge Amado",
    "Rachel de Queiroz",
    "Lygia Fagundes Telles",
]

# --- CONEXÃO COM GOOGLE SHEETS --------------------------------------
def connect_to_gsheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        # ABRA A PLANILHA PELO NOME QUE VOCÊ DEU A ELA
        spreadsheet = client.open("Desfechos - Histórias") # <-- MUDE AQUI O NOME DA SUA PLANILHA
        worksheet = spreadsheet.worksheet("Página1") # OU O NOME DA ABA
        return worksheet
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return None

# --- LE CHAVE DA COHERE -------------------------------------------
API_KEY = st.secrets.get("COHERE_API_KEY")
if not API_KEY:
    st.error("⚠️ Configure COHERE_API_KEY nos Secrets do Streamlit.")
    st.stop()
co = cohere.Client(API_KEY)

# --- FUNÇÃO QUE GERA A HISTÓRIA -----------------------------------
def gerar_historia(autor: str) -> str:
    prompt = (
        f"Você é um autor brasileiro famoso chamado {autor}. "
        f"Escreva três parágrafos de uma história curta, com personagens icônicos do estilo de {autor}. "
        "Apresente todo o texto em português brasileiro e não apresente nenhuma palavra em outro idioma, linguagem literária e termine com um gancho para o leitor concluir. "
        "Não adicione títulos nem numere os parágrafos."
    )
    rsp = co.chat(
        model="command-r",
        message=prompt,
        temperature=1.0,
        p=0.9,
        k=50,
        seed=random.randint(1, 2_000_000_000),
    )
    texto = rsp.text.strip()
    texto = re.sub(r'^\s*\(?\s*texto\s*:\s*', '', texto, flags=re.I)
    texto = re.sub(r'Parágrafo\s*\d+\s*:\s*', '', texto, flags=re.I)
    return texto

# --- INTERFACE STREAMLIT ------------------------------------------
st.title("✍️ Histórias cooperativas – escreva junto com autores clássicos do Brasil")

if 'historia_gerada' not in st.session_state:
    st.session_state.historia_gerada = ""

autor = st.selectbox("Escolha o autor:", AUTORES)

if st.button("Gerar história"):
    with st.spinner("Gerando…"):
        try:
            st.session_state.historia_gerada = gerar_historia(autor)
        except Exception as e:
            st.error(f"Erro na API da Cohere: {e}")
            st.session_state.historia_gerada = ""

if st.session_state.historia_gerada:
    st.text_area("História gerada:", st.session_state.historia_gerada, height=250, key="historia_area", disabled=True)
    st.divider()
    st.write("Agora é a sua vez! Continue a história.")
    nome_usuario = st.text_input("Seu nome:")
    desfecho = st.text_area("Seu desfecho:", height=150)

    if st.button("Enviar desfecho"):
        if nome_usuario and desfecho:
            with st.spinner("Enviando seu desfecho..."):
                worksheet = connect_to_gsheet()
                if worksheet:
                    nova_linha = [nome_usuario, st.session_state.historia_gerada, desfecho]
                    worksheet.append_row(nova_linha)
                    st.success("Desfecho enviado!")
                    st.session_state.historia_gerada = ""
                    st.rerun()
        else:
            st.warning("Por favor, preencha seu nome e o desfecho antes de enviar.")
