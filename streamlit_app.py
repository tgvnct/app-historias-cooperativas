# streamlit_app.py
import streamlit as st
import cohere, random, re, os
import gspread
from google.oauth2.service_account import Credentials

# Deixamos o código CSS aqui, comentado por enquanto.
# --- CSS PERSONALIZADO ---
# st.markdown("""...""", unsafe_allow_html=True)


# --- CONSTANTES E CONFIGURAÇÕES ------------------------------------
AUTORES = [
    "Machado de Assis",
    "Guimarães Rosa",
    "Jorge Amado",
    "Rachel de Queiroz",
    "Lygia Fagundes Telles",
]

# --- FUNÇÕES (COHERE E GOOGLE SHEETS) --------------------------------
def connect_to_gsheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("Desfechos das Histórias") # CONFIRA SE ESTE NOME ESTÁ CORRETO
        worksheet = spreadsheet.worksheet("Página1") # CONFIRA SE O NOME DA ABA ESTÁ CORRETO
        return worksheet
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return None

API_KEY = st.secrets.get("COHERE_API_KEY")
if API_KEY:
    co = cohere.Client(API_KEY)
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

# --- INTERFACE STREAMLIT ------------------------------------------
st.title("✍️ Histórias cooperativas")

# --- GERENCIAMENTO DE ESTADO DA SESSÃO ---
# MUDANÇA: Adicionamos mais variáveis para controlar o fluxo
if 'historia_gerada' not in st.session_state:
    st.session_state.historia_gerada = ""
if 'autor_selecionado' not in st.session_state:
    st.session_state.autor_selecionado = ""
if 'desfecho_usuario' not in st.session_state:
    st.session_state.desfecho_usuario = ""
if 'envio_concluido' not in st.session_state:
    st.session_state.envio_concluido = False


# MUDANÇA: A interface agora é condicional
# Se o envio ainda não foi concluído, mostra a interface normal
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
        st.text_area(label=f"Início da história por: {st.session_state.autor_selecionado}", value=st.session_state.historia_gerada, height=250, disabled=True)
        st.divider()
        st.write("Agora é a sua vez! Continue a história.")
        nome_usuario = st.text_input("Seu nome:")
        desfecho = st.text_area("Seu desfecho:", height=150)

        if st.button("Enviar e ver história completa"):
            if nome_usuario and desfecho:
                with st.spinner("Enviando seu desfecho..."):
                    worksheet = connect_to_gsheet()
                    if worksheet:
                        # MUDANÇA: Adicionamos o autor na linha a ser gravada
                        nova_linha = [st.session_state.autor_selecionado, nome_usuario, st.session_state.historia_gerada, desfecho]
                        worksheet.append_row(nova_linha)
                        
                        # MUDANÇA: Guardamos o desfecho e mudamos o estado para "concluído"
                        st.session_state.desfecho_usuario = desfecho
                        st.session_state.envio_concluido = True
                        st.rerun() # Força o recarregamento para mostrar a nova tela
            else:
                st.warning("Por favor, preencha seu nome e o desfecho antes de enviar.")

# MUDANÇA: Se o envio foi concluído, mostra a tela de sucesso com a história completa
else:
    st.success("Sua história foi enviada e salva com sucesso!")
    st.header("Confira a história completa:")

    # Junta as duas partes da história
    historia_completa = f"{st.session_state.historia_gerada}\n\n{st.session_state.desfecho_usuario}"
    
    st.markdown(f"""
    > _Início por **{st.session_state.autor_selecionado}**_
    >
    > {st.session_state.historia_gerada}
    >
    > _Seu desfecho:_
    >
    > **{st.session_state.desfecho_usuario}**
    """)
    
    st.divider()

    # MUDANÇA: Botão para resetar e escrever uma nova história
    if st.button("Escrever outra história"):
        # Limpa todas as variáveis de estado para recomeçar
        st.session_state.historia_gerada = ""
        st.session_state.autor_selecionado = ""
        st.session_state.desfecho_usuario = ""
        st.session_state.envio_concluido = False
        st.rerun()
