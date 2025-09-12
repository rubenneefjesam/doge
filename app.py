import os
import io
import tempfile
import streamlit as st
import docx
import re
import json
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
            {"role": "system", "content": "Antwoord alleen met de JSON-array, geen extra tekst."},
            {"role": "user",   "content": prompt}
        ]
    )
    content = resp.choices[0].message.content

    # Verwijder numerieke prefixes zoals '0:{'
    cleaned = re.sub(r"\d+\s*:\s*{", "{", content)
    # Extract array tussen [ ]
    start = cleaned.find('[')
    end = cleaned.rfind(']') + 1
    json_str = cleaned[start:end] if start != -1 and end != -1 else cleaned

    # Parse JSON
    try:
        replacements = json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback handmatig parse
        replacements = []
        lines = cleaned.splitlines()
        for i, line in enumerate(lines):
            if '"find"' in line:
                fm = re.search(r'"find"\s*:\s*"([^"]*)"', line)
                rm = None
                if fm:
                    for j in range(i+1, len(lines)):
                        if '"replace"' in lines[j]:
                            m = re.search(r'"replace"\s*:\s*"([^"]*)"', lines[j])
                            if m:
                                rm = m.group(1)
                            break
                if fm and rm is not None:
                    replacements.append({"find": fm.group(1), "replace": rm})

    # Filter alleen daadwerkelijke vervangingen
    return [r for r in replacements if r.get("find") and r["find"] != r.get("replace")]


def apply_replacements(doc_path: str, replacements: list[dict]) -> bytes:
    """
    Past find/replace-operaties toe in een .docx en behoudt alle stijlen.
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

    # Paragrafen en tabellen verwerken
    for para in doc.paragraphs:
        replace_in_runs(para.runs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_runs(para.runs)

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

    # Lees context
    if ctx_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        ctx_path = os.path.join(tmp_dir, "context.docx")
        with open(ctx_path, "wb") as f:
            f.write(ctx_file.getbuffer())
        context_text = read_docx(ctx_path)
    else:
        context_text = ctx_file.read().decode("utf-8", errors="ignore")

    # Previews
    st.subheader("Template preview (eerste 200 tekens)")
    tpl_text = read_docx(tpl_path)
    st.text(tpl_text[:200] + ("…" if len(tpl_text)>200 else ""))
    st.subheader("Context preview (eerste 200 tekens)")
    st.text(context_text[:200] + ("…" if len(context_text)>200 else ""))

    # Stap 1: Genereer vervangingslijst en document
    if st.button("🛠️ Genereer document met nieuwe context"):
        try:
            replacements = get_replacements(tpl_text, context_text)
            # Toon vervangingsinformatie
            st.subheader("Aangepaste onderdelen:")
            for rep in replacements:
                st.write(f"• Vervang '{rep['find']}' door '{rep['replace']}'")
            # Maak document
            doc_bytes = apply_replacements(tpl_path, replacements)
            st.session_state["doc_bytes"] = doc_bytes
        except Exception as e:
            st.error(f"Fout bij genereren: {e}")

    # Stap 2: Download
    if "doc_bytes" in st.session_state:
        st.download_button(
            label="⬇️ Download aangepast document",
            data=st.session_state["doc_bytes"],
            file_name="aangepast_template.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
else:
    st.info("Upload template en context in de zijbalk om te starten.")
    st.info("Upload template en context in de zijbalk om te starten.")
