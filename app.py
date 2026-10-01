import io
import json
import os
from dotenv import load_dotenv
from fpdf import FPDF
import google.generativeai as genai
import streamlit as st

# Carregar variáveis de ambiente
load_dotenv()

HISTORICO_FILE = "historico_estudos.json"


def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                # Filtra mensagens de erro que possam ter sido salvas por engano
                return [
                    msg
                    for msg in dados
                    if "Erro ao consultar" not in msg.get("content", "")
                    and "Limite de frequência" not in msg.get("content", "")
                    and "Cota" not in msg.get("content", "")
                ]
        except Exception:
            return []
    return []


def guardar_historico(messages):
    mensagens_limpas = [
        msg
        for msg in messages
        if "Erro ao consultar" not in msg.get("content", "")
        and "Limite de frequência" not in msg.get("content", "")
        and "Cota" not in msg.get("content", "")
    ]
    with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
        json.dump(mensagens_limpas, f, ensure_ascii=False, indent=2)


def gerar_pdf_estudos(messages):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(
        0,
        10,
        text="Caderno de Estudos - Professor CACD",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(5)

    for msg in messages:
        role = (
            "Candidato (Dúvida/Tema)" if msg["role"] == "user" else "Professor CACD"
        )
        content = msg["content"]

        pdf.set_font("Helvetica", style="B", size=11)
        if msg["role"] == "user":
            pdf.set_text_color(0, 51, 102)
        else:
            pdf.set_text_color(102, 0, 0)

        pdf.cell(0, 8, text=f"[{role}]", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(30, 30, 30)

        texto_limpo = content.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 6, text=texto_limpo)
        pdf.ln(4)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer


st.set_page_config(
    page_title="Professor CACD", page_icon="🎓", layout="centered"
)
st.title("🎓 Professor CACD - Assistente de Estudos")
st.caption("Preparação de alto nível para a Carreira Diplomática")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("Chave da API não encontrada no arquivo .env!")
    st.stop()

genai.configure(api_key=api_key)

SYSTEM_INSTRUCTION = """
Você é um Professor Doutor especialista na preparação para o Concurso de Admissão à Carreira de Diplomata (CACD).
Sua missão é ensinar o candidato com rigor acadêmico, clareza pedagógica e alinhamento total à banca examinadora (Cebraspe).

Ao responder:
1. Identifique a disciplina (História do Brasil, Política Internacional, Economia, Direito Internacional, Geografia, etc.).
2. Explique os conceitos teóricos de forma aprofundada, citando a bibliografia consagrada do CACD quando relevante.
3. Apresente como esse tema costuma ser cobrado nas provas objetivas (Certo/Errado) ou discursivas.
4. Finalize propondo uma questão prática no estilo Cebraspe para fixação.
"""

# Configuração com o modelo oficial recomendado pelo Google
model = genai.GenerativeModel(
    model_name="gemini-3.8-flash", system_instruction=SYSTEM_INSTRUCTION
)

if "messages" not in st.session_state:
    st.session_state.messages = carregar_historico()

with st.sidebar:
    st.header("📄 Material de Estudo")

    if st.session_state.messages:
        pdf_data = gerar_pdf_estudos(st.session_state.messages)
        st.download_button(
            label="📥 Baixar Estudos em PDF",
            data=pdf_data,
            file_name="caderno_estudos_cacd.pdf",
            mime="application/pdf",
        )

    st.markdown("---")
    if st.button("🗑️ Limpar Histórico de Estudos"):
        st.session_state.messages = []
        guardar_historico([])
        st.rerun()

# Exibe apenas mensagens válidas na tela
for message in st.session_state.messages:
    if (
        "Erro ao consultar" not in message["content"]
        and "Limite de frequência" not in message["content"]
    ):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if user_input := st.chat_input("Digite sua dúvida ou tema de estudo..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analisando bibliografia e preparando aula..."):
            try:
                response = model.generate_content(user_input)
                bot_reply = response.text
                st.markdown(bot_reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": bot_reply}
                )
                guardar_historico(st.session_state.messages)
            except Exception as e:
                if "429" in str(e):
                    st.warning(
                        "⏳ Cota temporária atingida (limite de 5 perguntas por minuto na camada gratuita). Aguarde 1 minuto para continuar!"
                    )
                else:
                    st.error(f"Erro ao consultar a API: {e}")