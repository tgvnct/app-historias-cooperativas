# streamlit_app.py - VERSÃO COMPLETA E CORRIGIDA

import streamlit as st
import cohere
import random
import re
import os
import gspread
from google.oauth2.service_account import Credentials
from textwrap import dedent

# O código CSS está aqui, comentado. Se quiser tentar novamente no futuro, basta remover os '/*' e '*/'.
/*
st.markdown(\"""
<style>
div[data-baseweb="textarea"] {
    background-color: transparent !important;
}
.stTextArea textarea[disabled] {
    background-color: transparent !important;
    color: #000000 !important;
    border: 1px solid #cccccc !important;
    user-select: none !important;
    -webkit-user-select: none !important;
    -moz-user-select: none !important;
    -ms-user-select: none !important;
}
</style>
\""", unsafe_allow_html=True)
*/


# --- CONSTANTES E CONFIGURAÇÕES ---
AUTORES = [
    "Machado de Assis",
    "Guimarães Rosa",
    "Jorge Amado",
    "Rachel de Queiroz",
    "Lygia Fagundes Telles",
]

# --- FUNÇÕES (COHERE E GOOGLE SHEETS) ---
def connect_to_gsheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("Desfechos das Histórias") # CONFIRA O NOME DA PLANILHA
        worksheet = spreadsheet.worksheet("Página1") # CONFIRA O NOME DA ABA
        return worksheet
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return None

if "COHERE_API_KEY" in st.secrets:
    co = cohere.Client(st.secrets["COHERE_API_KEY"])
else:
    st.error("⚠️ Configure COHERE_API_KEY nos Secrets do Streamlit.")
    st.stop()

def gerar_historia(autor: str) -> str:
    prompt = (
        f"Você é um autor brasileiro famoso chamado {autor}. "
        f"Escreva três parágrafos de uma história curta, com personagens icônicos do estilo de {autor}. "
        "Apresente todo o texto em português brasileiro e não apresente nenhuma palavra em outro idioma, linguagem literária e termine com um gancho para o leitor concluir. "
        "Não adicione títulos nem numere os parágrafos."
    )
    rsp = co.chat(
        model="command-r", message=prompt, temperature=1.0, p=0.9, k=50,
        seed=random.randint(1, 2_000_000_000),
    )
    texto = rsp.text.strip()
    texto = re.sub(r'^\s*\(?\s*texto\s*:\s*', '', texto, flags=re.I)
    texto = re.sub(r'Parágrafo\s*\d+\s*:\s*', '', texto, flags=re.I)
    return texto

# --- INTERFACE STREAMLIT ---
st.title("✍️ Histórias cooperativas")

# --- GERENCIAMENTO DE ESTADO DA SESSÃO ---
if 'historia_gerada' not in st.session_state:
    st.session_state.historia_gerada = ""
if 'autor_selecionado' not in st.session_state:
    st.session_state.autor_selecionado = ""
if 'desfecho_usuario' not in st.session_state:
    st.session_state.desfecho_usuario = ""
if 'envio_concluido' not in st.session_state:
    st.session_state.envio_concluido = False


# --- LÓGICA DE EXIBIÇÃO DA INTERFACE ---
if not st.session_state.envio_concluido:
    st.write("Escreva junto com autores clássicos do Brasil")
    autor = st.selectbox("Escolha o autor:", AUTORES)

    if st.button("Gerar início da história"):
        with st.spinner("Gerando…"):
            try:
                st.session_state.historia_gerada = gerar_historia(autor)
                st.session_state.autor_selecionado = autor
            except Exception as e:
                st.error(f"Erro na API da Cohere: {e}")
                st.session_state.historia_gerada = ""

    if st.session_state.historia_gerada:
        st.text_area(label="", value=st.session_state.historia_gerada, height=250, disabled=True)
        st.divider()
        st.write("Agora é a sua vez! Continue a história.")
        nome_usuario = st.text_input("Seu nome:")
        desfecho = st.text_area("Seu desfecho:", height=150)

        if st.button("Enviar e ver história completa"):
            if nome_usuario and desfecho:
                with st.spinner("Enviando seu desfecho..."):
                    worksheet = connect_to_gsheet()
                    if worksheet:
                        nova_linha = [st.session_state.autor_selecionado, nome_usuario, st.session_state.historia_gerada, desfecho]
                        worksheet.append_row(nova_linha)
                        
                        st.session_state.desfecho_usuario = desfecho
                        st.session_state.envio_concluido = True
                        st.rerun()
            else:
                st.warning("Por favor, preencha seu nome e o desfecho antes de enviar.")

else:
    st.success("Sua história foi enviada e salva com sucesso!")
    st.header("Confira a história completa:")

    # Monta o texto completo
    texto_completo = f"""
        {st.session_state.historia_gerada}

        *Seu desfecho:*

        **{st.session_state.desfecho_usuario}**
    """

    # Usa dedent para remover a indentação antes de exibir
    st.markdown(dedent(texto_completo))
    
    st.divider()

    # Botão para resetar e escrever uma nova história
    if st.button("Escrever outra história"):
        # Limpa todas as variáveis de estado para recomeçar
        st.session_state.historia_gerada = ""
        st.session_state.autor_selecionado = ""
        st.session_state.desfecho_usuario = ""
        st.session_state.envio_concluido = False
        st.rerun()
