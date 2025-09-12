import os
import tempfile
import streamlit as st
import docx
from groq import Groq

st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")

def get_client():
    key = st.secrets["groq"]["api_key"].strip()
    return Groq(api_key=key)

client = get_client()

def read_docx(path):
    d = docx.Document(path)
    return "\n\n".join(p.text for p in d.paragraphs if p.text.strip())

def write_docx_from_text(text) -> bytes:
    # splits op regels – pas aan naar voorkeur
    lines = text.split("\n")
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc = docx.Document()
    for line in lines:
        doc.add_paragraph(line)
    doc.save(out.name)
    out.seek(0)
    return out.read()

st.sidebar.header("Upload bestanden")
tpl_file = st.sidebar.file_uploader("Upload Template (.docx)", type="docx")
ctx_file = st.sidebar.file_uploader("Upload Nieuwe Context (.docx)", type="docx")

if tpl_file and ctx_file:
    # opslaan
    tmp = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp, "template.docx")
    ctx_path = os.path.join(tmp, "context.docx")
    with open(tpl_path,"wb") as f: f.write(tpl_file.getbuffer())
    with open(ctx_path,"wb") as f: f.write(ctx_file.getbuffer())

    tpl_text = read_docx(tpl_path)
    ctx_text = read_docx(ctx_path)

    st.subheader("Template Preview")
    st.write(tpl_text[:500] + ("…" if len(tpl_text)>500 else ""))
    st.subheader("Context Preview")
    st.write(ctx_text[:500] + ("…" if len(ctx_text)>500 else ""))

    if st.button("🪄 Vul en vervang automatisch"):
        prompt = (
            "Je krijgt een template (met al z’n vaste tekst én placeholders) en een nieuwe context. "
            "Ga in de template op zoek naar alle plaatsen waar die nieuwe informatie relevant is en "
            "voeg die context daar in of vervang bestaande zinnen. "
            "Lever de complete, bijgewerkte versie van het document terug—geen aparte JSON, maar "
            "de hele tekst."
            f"\n\n=== TEMPLATE ===\n{tpl_text}"
            f"\n\n=== NIEUWE CONTEXT ===\n{ctx_text}"
        )

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role":"system","content":"Je bent een teksteditor die docx-templates kan aanpassen."},
                {"role":"user","content":prompt}
            ]
        )
        updated = res.choices[0].message.content

        # maak er een .docx van
        doc_bytes = write_docx_from_text(updated)
        st.download_button(
            "⬇️ Download bijgewerkt document",
            data=doc_bytes,
            file_name="gevuld_document.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
else:
    st.info("Upload zowel je template als de nieuwe context bovenaan de zijbalk.")
