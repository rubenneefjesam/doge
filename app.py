import os
import io
import tempfile
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
        client = Groq(api_key=api_key)
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

groq_client = get_groq_client()

# ─── Functies ─────────────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    """Lees alle tekstuele paragrafen uit een .docx-bestand."""
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def get_replacements(template_text: str, context_text: str) -> list[dict]:
    """
    Vraag LLM om find/replace instructies als JSON-array.
    """
    prompt = (
        "Gegeven de TEMPLATE en CONTEXT, lever een JSON-array van objecten {find, replace}."
        f"\n\nTEMPLATE:\n{template_text}\n\n"
        f"CONTEXT:\n{context_text}"
    )
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role":"system","content":"Geef alleen de JSON-array, geen extra tekst."},
            {"role":"user","content":prompt}
        ]
    )
    content = resp.choices[0].message.content
    # Verwijder nummering en pak array\ n    cleaned = content
    # extract between [ ]
    start = cleaned.find('[')
    end = cleaned.rfind(']') + 1
    json_str = cleaned[start:end] if start != -1 and end != -1 else cleaned
    import json, re
    # remove numeric prefixes
    json_str = re.sub(r"\d+\s*:\s*{", "{", json_str)
    replacements = json.loads(json_str)
    # filter zinvolle vervangingen
    return [r for r in replacements if r.get('find') and r.get('find') != r.get('replace')]


def apply_replacements(doc_path: str, replacements: list[dict]) -> bytes:
    """
    Past find/replace-operaties toe in een .docx, behoudt alle stijlen.
    """
    doc = docx.Document(doc_path)

    def replace_in_runs(runs):
        if not runs:
            return
        text = ''.join(r.text for r in runs)
        for rep in replacements:
            text = text.replace(rep['find'], rep['replace'])
        runs[0].text = text
        for r in runs[1:]:
            r.text = ''

    # paragrafen
    for para in doc.paragraphs:
        replace_in_runs(para.runs)
    # tabellen
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_runs(para.runs)

    # export als bytes
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# ─── Streamlit UI ────────────────────────────────────────────────────────
st.sidebar.header("Upload bestanden")
tpl_file = st.sidebar.file_uploader("1) Upload DOCX-template", type=["docx"])
ctx_file = st.sidebar.file_uploader("2) Upload Context (.docx of .txt)", type=["docx","txt"])

if tpl_file and ctx_file:
    tmp_dir = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(tpl_file.getbuffer())

    # lees context
    if ctx_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        ctx_path = os.path.join(tmp_dir, "context.docx")
        with open(ctx_path, "wb") as f:
            f.write(ctx_file.getbuffer())
        context_text = read_docx(ctx_path)
    else:
        context_text = ctx_file.read().decode("utf-8", errors="ignore")

    # preview
    st.subheader("Template preview (eerste 200 tekens)")
    tpl_text = read_docx(tpl_path)
    st.text(tpl_text[:200] + ("…" if len(tpl_text)>200 else ""))
    st.subheader("Context preview (eerste 200 tekens)")
    st.text(context_text[:200] + ("…" if len(context_text)>200 else ""))

    if st.button("🔄 Vul en vervang automatisch"):
        st.info("Genereren vervangingsinstructies…")
        try:
            replacements = get_replacements(tpl_text, context_text)
            st.write("Vervangingslijst:", replacements)
            doc_bytes = apply_replacements(tpl_path, replacements)
            st.download_button(
                "⬇️ Download aangepast document",
                data=doc_bytes,
                file_name="aangepast_template.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Fout bij invullen: {e}")
else:
    st.info("Upload template en context in de zijbalk om te starten.")