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
        st.sidebar.error(
            "❌ Mist Groq-credentials! Voeg ze toe in `.streamlit/secrets.toml`:
[groq]
api_key = \"...\"")
        st.stop()
    try:
        client = Groq(api_key=api_key)
        st.sidebar.success("🔑 Verbonden met Groq API")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

# Haal de client op
groq_client = get_groq_client()

# ─── Document uitlezen ────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

# ─── Vul template via LLM ─────────────────────────────────────────────────
def enrich_and_fill(template_path: str, source_paths: list[str]) -> bytes:
    # Lees template placeholder-namen
    tpl = DocxTemplate(template_path)
    fields = [cell.text.strip() for cell in tpl.docx.tables[0].rows[0].cells]
    # Bouw prompt
    parts = [f"Template fields: {', '.join(fields)}."]
    for src in source_paths:
        text = read_docx(src)
        parts.append(f"Brondocument ({os.path.basename(src)}):\n{text}")
    prompt = (
        "Vul het template in met de volgende brondocumenten. Geef per rij een entry voor: "
        + ", ".join(fields)
        + ". Output in JSON array formaat."
    )
    full_prompt = prompt + "\n\n" + "\n\n".join(parts)

    # Chat-call naar LLM
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Je bent een data-assistent die JSON-outputs levert voor DOCX-sjablonen."},
            {"role": "user", "content": full_prompt}
        ]
    )
    content = response.choices[0].message.content
    # Parse JSON
    import json
    records = json.loads(content)
    # Render en sla op
    tpl.render({"risks": records})
    out = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tpl.save(out.name)
    out.seek(0)
    return out.read()

# ─── Streamlit UI ────────────────────────────────────────────────────────
st.sidebar.header("Upload bestanden")
tpl_file = st.sidebar.file_uploader("Upload DOCX Template", type=["docx"])
src_files = st.sidebar.file_uploader("Upload Brondocumenten", type=["docx"], accept_multiple_files=True)

if tpl_file and src_files:
    tmp_dir = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(tpl_file.getbuffer())
    src_paths = []
    for sf in src_files:
        p = os.path.join(tmp_dir, sf.name)
        with open(p, "wb") as o:
            o.write(sf.getbuffer())
        src_paths.append(p)

    st.subheader("Voorbeeldweergave documenten")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Template:** {tpl_file.name}")
        st.write(read_docx(tpl_path))
    with col2:
        st.markdown(f"**Brondocument:** {src_files[0].name}")
        st.write(read_docx(src_paths[0]))

    if st.button("Vul template aan met nieuwe/vervangende informatie"):
        st.info("Bezig met invullen via LLM…")
        try:
            doc_bytes = enrich_and_fill(tpl_path, src_paths)
            st.download_button(
                label="Download ingevuld document",
                data=doc_bytes,
                file_name="resultaat.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Invullen mislukt: {e}")
else:
    st.info("Upload een template en ten minste één brondocument via de zijbalk.")