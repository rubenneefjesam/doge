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
            "❌ Mist Groq-credentials! Voeg ze toe in `.streamlit/secrets.toml` met een [groq]-sectie."
        )
        st.stop()
    try:
        client = Groq(api_key=api_key)
        st.sidebar.success("🔑 Verbonden met Groq API")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

# Groq-client ophalen
groq_client = get_groq_client()

# ─── Document uitlezen ────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

# ─── Vul template via LLM ─────────────────────────────────────────────────
def enrich_and_fill(template_path: str, source_paths: list[str]) -> bytes:
    # Bepaal vaste velden uit je template
    fields = ["Risico", "Oorzaak", "Beheersmaatregel"]

    # Bouw prompt met alle documenten
    parts = []
    for src in source_paths:
        text = read_docx(src)
        parts.append(f"Document '{os.path.basename(src)}':\n{text}")
    prompt = (
        "Je bent een assistent voor het vullen van een DOCX-template. "
        f"Het template heeft velden: {', '.join(fields)}."
        " Maak een JSON-array waarbij elk object deze velden bevat."
        " Gebruik de inhoud van de volgende documenten om de waarden te vullen."
        " Output alleen de JSON-array zonder extra commentaar."
        + "\n\n" + "\n\n".join(parts)
    )

    # Stuur één gecombineerde chat-aanroep
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Je bent een data-assistent die JSON levert voor DOCX-templates."},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content
    import json
    records = json.loads(content)

    # Render template met de ontvangen records
    tpl = DocxTemplate(template_path)
    tpl.render({"risks": records})

    # Sla op en return als bytes
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

    # Toon template en eerste bron naast elkaar
    st.subheader("Voorbeeldweergave documenten")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Template:** {tpl_file.name}")
        st.write(read_docx(tpl_path))
    with col2:
        st.markdown(f"**Brondocument:** {src_files[0].name}")
        st.write(read_docx(src_paths[0]))

    # Knop om template te verrijken en invullen
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
    st.info("Upload een template en minimaal één brondocument via de zijbalk.")