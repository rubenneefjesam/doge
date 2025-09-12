import os
import io
import tempfile
import streamlit as st
import docx
import re
import json
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────┐
# 🎨 Streamlit Page Config & Global Styles
# ─────────────────────────────────────────────────────────────────────────────┘
st.set_page_config(
    page_title="🎉 DOCX Generator", 
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.markdown(
    """
    <style>
    .stButton>button {font-size:16px; font-weight:bold; background-color:#4CAF50; color:white;}
    .stDownloadButton>button {font-size:16px; font-weight:bold; background-color:#2196F3; color:white;}
    .stTextArea>div>div>textarea {background-color:#1e1e1e; color:#cfcfcf; font-family:monospace;}
    </style>
    """,
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────────────────────┐
# 🔑 Groq Client Initialization
# ─────────────────────────────────────────────────────────────────────────────┘
def get_groq_client():
    api_key = st.secrets.get("groq", {}).get("api_key", "").strip()
    if not api_key:
        st.error("❌ Voeg Groq API key toe in `.streamlit/secrets.toml` onder [groq]")
        st.stop()
    try:
        client = Groq(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

groq_client = get_groq_client()

# ─────────────────────────────────────────────────────────────────────────────┐
# 📄 Utility Functions
# ─────────────────────────────────────────────────────────────────────────────┘
def read_docx(path: str) -> str:
    """Lees platte tekst uit alle paragrafen van een .docx."""
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def get_replacements(template_text: str, context_text: str) -> list[dict]:
    """Vraag de LLM om find/replace-instructies als JSON-array."""
    prompt = (
        "Gegeven TEMPLATE en CONTEXT, lever een JSON-array van objecten {find, replace}."
        f"\n\nTEMPLATE:\n{template_text}\n\n"
        f"CONTEXT:\n{context_text}"
    )
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role":"system","content":"Antwoord alleen met de JSON-array, geen extra tekst."},
            {"role":"user","content":prompt}
        ]
    )
    content = resp.choices[0].message.content
    # Cleanup numbered prefixes and extract JSON
    cleaned = re.sub(r"\d+\s*:\s*{", "{", content)
    start = cleaned.find('[')
    end = cleaned.rfind(']') + 1
    json_str = cleaned[start:end] if start!=-1 and end!=-1 else cleaned
    try:
        replacements = json.loads(json_str)
    except json.JSONDecodeError:
        replacements = []
        for line in cleaned.splitlines():
            m_find = re.search(r'"find"\s*:\s*"([^"]*)"', line)
            if m_find:
                find_val = m_find.group(1)
                # find replace on same line or next
                m_rep = re.search(r'"replace"\s*:\s*"([^"]*)"', line)
                if not m_rep:
                    # look ahead
                    idx = cleaned.splitlines().index(line)
                    for nxt in cleaned.splitlines()[idx+1:]:
                        m_rep = re.search(r'"replace"\s*:\s*"([^"]*)"', nxt)
                        if m_rep:
                            break
                if m_rep:
                    replacements.append({"find":find_val, "replace":m_rep.group(1)})
    # Filter out no-ops
    return [r for r in replacements if r['find'] and r['find']!=r['replace']]


def apply_replacements(doc_path: str, replacements: list[dict]) -> bytes:
    """Voert find/replace uit in .docx, behoudt styling."""
    doc = docx.Document(doc_path)

    def repl(runs):
        if not runs:
            return
        text = ''.join(r.text for r in runs)
        for rep in replacements:
            text = text.replace(rep['find'], rep['replace'])
        runs[0].text = text
        for r in runs[1:]:
            r.text = ''

    for p in doc.paragraphs:
        repl(p.runs)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    repl(p.runs)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────┐
# 🚀 Main Interface
# ─────────────────────────────────────────────────────────────────────────────┘
st.markdown("## 👉 Upload en bekijk je documenten")
col1, col2 = st.columns([1,1])

with col1:
    tpl_file = st.file_uploader("**1. Kies je template**", type="docx", key="tpl")
    if tpl_file:
        tpl_path = os.path.join(tempfile.mkdtemp(), "template.docx")
        with open(tpl_path, "wb") as f: f.write(tpl_file.getbuffer())
        st.markdown("**Template-inhoud:**")
        st.text_area("", read_docx(tpl_path), height=200, key="tpl_preview")

with col2:
    ctx_file = st.file_uploader("**2. Kies je nieuwe context**", type=["docx","txt"], key="ctx")
    if ctx_file:
        tmpc = tempfile.mkdtemp()
        if ctx_file.type.endswith('document'):
            cpath = os.path.join(tmpc, "context.docx")
            with open(cpath,"wb") as f: f.write(ctx_file.getbuffer())
            context = read_docx(cpath)
        else:
            context = ctx_file.read().decode('utf-8',errors='ignore')
        st.markdown("**Context-inhoud:**")
        st.text_area("", context, height=200, key="ctx_preview")

if tpl_file and ctx_file:
    st.markdown("---")
    if st.button("🎉 Genereer aangepast document"):
        tpl_text = read_docx(tpl_path)
        replacements = get_replacements(tpl_text, context)
        st.success("🎯 Vervangingsinstructies succesvol gegenereerd:")
        for rep in replacements:
            st.write(f"• Vervang '**{rep['find']}**' -> '**{rep['replace']}**'")
        result = apply_replacements(tpl_path, replacements)
        st.download_button(
            "⬇️ Download je aangepaste document",
            data=result,
            file_name="aangepast_template.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
else:
    st.warning("Upload eerst een template en context om te starten.")
