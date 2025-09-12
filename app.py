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
        return Groq(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden Groq API: {e}")
        st.stop()

groq_client = get_groq_client()

# ─── Functies ─────────────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def apply_replacements(doc_path: str, replacements: list[dict]) -> bytes:
    """
    Past find/replace-operaties toe in het Word-document en behoudt alle opmaak.
    """
    doc = docx.Document(doc_path)
    def replace_in_runs(runs):
        text = ''.join(r.text for r in runs)
        for rep in replacements:
            if rep['find'] in text:
                text = text.replace(rep['find'], rep['replace'])
        # herbouw first run en clear others
        runs[0].text = text
        for r in runs[1:]:
            r.text = ''

    # vervang in paragrafen
    for para in doc.paragraphs:
        replace_in_runs(para.runs)
    # vervang in tabellen
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_runs(para.runs)

    # schrijf naar bytes
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def get_replacements(template_text: str, context_text: str) -> list[dict]:
    """
    Vraag LLM om een lijst van find/replace-instructies als JSON.
    """
    prompt = (
        "Gegeven de onderstaande template-tekst en nieuwe context, lever strikt een JSON-array van objecten zonder indexnummers. "
        "Elk object heeft twee velden: 'find' en 'replace'. Voorbeeld:\n"
        "[\n"
        "  {\"find\": \"oude tekst\", \"replace\": \"nieuwe tekst\"},\n"
        "  ...\n"
        "]\n\n"
        f"TEMPLATE:\n{template_text}\n\n"
        f"CONTEXT:\n{context_text}"
    )
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role":"system","content":"Antwoord alleen de JSON-array, zonder uitleg, markdown of opsomming."},
            {"role":"user","content": prompt}
        ]
    )
    content = resp.choices[0].message.content
    # JSON-extractie tussen eerste '[' en laatste ']'
    start = content.find('[')
    end = content.rfind(']') + 1
    json_str = content[start:end] if start != -1 and end != -1 else content.strip()
    import json
    replacements = json.loads(json_str)
    return replacements

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
        st.info("Bezig met genereren van vervangingsinstructies…")
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
    st.info("Upload zowel je template als context-bestand in de zijbalk.")
