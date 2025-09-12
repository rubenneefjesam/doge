import os
import tempfile
from docxtpl import DocxTemplate
import streamlit as st
import docx
from groq import Groq

# ─── Streamlit Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")

# ─── Init Groq-client via st.secrets ──────────────────────────────────────
def get_groq_client():
    api_key = st.secrets.get("groq", {}).get("api_key", "").strip()
    if not api_key:
        st.sidebar.error("❌ Voeg Groq API key toe in .streamlit/secrets.toml onder [groq]")
        st.stop()
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

groq_client = get_groq_client()

# ─── Functies ─────────────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def fill_placeholders(template_path: str, context_text: str) -> bytes:
    # Laad template
    tpl = DocxTemplate(template_path)
    placeholders = tpl.get_undeclared_template_variables()

    # Bouw prompt
    prompt = (
        "Je bent een content-assistent. Alleen antwoord: een geldig JSON-object met keys als placeholder-namen en values als ingevulde teksten."
        f" Placeholders: {', '.join(placeholders)}."
        f" Context:\n{context_text}"
    )

    # LLM-call
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        messages=[{"role":"system","content":prompt}]
    )
    content = resp.choices[0].message.content.strip()

    import json
    try:
        values = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Ongeldige JSON:\n{content}")

    # Render en bewaar layout
    tpl.render(values)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tpl.save(tmp.name)
    tmp.seek(0)
    return tmp.read()

# ─── Streamlit UI ────────────────────────────────────────────────────────
st.sidebar.header("Upload bestanden")
tpl_file = st.sidebar.file_uploader("1) Upload DOCX-template", type=["docx"])
ctx_file = st.sidebar.file_uploader("2) Upload context (.docx of .txt)", type=["docx","txt"])

if tpl_file and ctx_file:
    # Opslaan
    tmp_dir = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, "template.docx")
    with open(tpl_path, "wb") as f: f.write(tpl_file.getbuffer())

    # Lees context
    if ctx_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        ctx_path = os.path.join(tmp_dir, "context.docx")
        with open(ctx_path, "wb") as f: f.write(ctx_file.getbuffer())
        context_text = read_docx(ctx_path)
    else:
        context_text = ctx_file.read().decode("utf-8", errors="ignore")

    # Preview
    st.subheader("Template preview")
    tpl_preview = read_docx(tpl_path)
    st.text(tpl_preview[:200] + ("…" if len(tpl_preview)>200 else ""))
    st.subheader("Context preview")
    st.text(context_text[:200] + ("…" if len(context_text)>200 else ""))

    # Button
    if st.button("🖋️ Vul template met context"):
        st.info("Invullen template…")
        try:
            doc_bytes = fill_placeholders(tpl_path, context_text)
            st.download_button(
                "⬇️ Download ingevuld document",
                data=doc_bytes,
                file_name="gevuld_template.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Invullen mislukt: {e}")
else:
    st.info("Upload template en context om te beginnen.")