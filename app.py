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
        st.error("❌ Voeg Groq API key toe in .streamlit/secrets.toml onder [groq]")
        st.stop()
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        st.error(f"❌ Fout bij verbinden Groove API: {e}")
        st.stop()

groq_client = get_groq_client()

# ─── Helper functies ─────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def get_replacements(template_text: str, context_text: str) -> list[dict]:
    prompt = (
        "Gegeven TEMPLATE en CONTEXT, lever JSON-array van {find, replace}."
        f"\n\nTEMPLATE:\n{template_text}\n\n"
        f"CONTEXT:\n{context_text}"
    )
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role":"system","content":"Antwoord alleen de JSON-array, geen extra tekst."},
            {"role":"user","content":prompt}
        ]
    )
    content = resp.choices[0].message.content
    cleaned = re.sub(r"\d+\s*:\s*{", "{", content)
    start = cleaned.find('[')
    end = cleaned.rfind(']') + 1
    json_str = cleaned[start:end] if start != -1 and end != -1 else cleaned
    try:
        replacements = json.loads(json_str)
    except json.JSONDecodeError:
        replacements = []
        lines = cleaned.splitlines()
        for i, line in enumerate(lines):
            if '"find"' in line:
                fm = re.search(r'"find"\s*:\s*"([^"]*)"', line)
                rm_val = None
                if fm:
                    for j in range(i+1, len(lines)):
                        if '"replace"' in lines[j]:
                            m = re.search(r'"replace"\s*:\s*"([^"]*)"', lines[j])
                            if m:
                                rm_val = m.group(1)
                            break
                if fm and rm_val is not None:
                    replacements.append({"find": fm.group(1), "replace": rm_val})
    return [r for r in replacements if r.get("find") and r["find"] != r.get("replace")]


def apply_replacements(doc_path: str, replacements: list[dict]) -> bytes:
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
col1, col2 = st.columns(2)
with col1:
    st.subheader("Template (.docx)")
    tpl_file = st.file_uploader("Kies template-bestand", type=["docx"], key="tpl")
    if tpl_file:
        tpl_path = os.path.join(tempfile.mkdtemp(), "template.docx")
        with open(tpl_path, "wb") as f:
            f.write(tpl_file.getbuffer())
        tpl_text = read_docx(tpl_path)
        st.subheader("Template-inhoud")
        st.text_area("", tpl_text, height=200)
with col2:
    st.subheader("Context (.docx/.txt)")
    ctx_file = st.file_uploader("Kies context-bestand", type=["docx","txt"], key="ctx")
    if ctx_file:
        tmp_ctx = tempfile.mkdtemp()
        if ctx_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            ctx_path = os.path.join(tmp_ctx, "context.docx")
            with open(ctx_path, "wb") as f:
                f.write(ctx_file.getbuffer())
            context_text = read_docx(ctx_path)
        else:
            context_text = ctx_file.read().decode("utf-8", errors="ignore")
        st.subheader("Context-inhoud")
        st.text_area("", context_text, height=200)

# Genereer & toon resultaten
if tpl_file and ctx_file:
    if st.button("🛠️ Genereer document met nieuwe context"):
        try:
            replacements = get_replacements(tpl_text, context_text)
            st.subheader("Aangepaste onderdelen:")
            for rep in replacements:
                st.write(f"• Vervang '{rep['find']}' door '{rep['replace']}'")
            doc_bytes = apply_replacements(tpl_path, replacements)
            st.session_state['doc_bytes'] = doc_bytes
        except Exception as e:
            st.error(f"Fout bij genereren: {e}")

    if 'doc_bytes' in st.session_state:
        st.download_button(
            "⬇️ Download aangepast document",
            data=st.session_state['doc_bytes'],
            file_name="aangepast_template.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
else:
    st.info("Upload zowel template als context om te beginnen.")