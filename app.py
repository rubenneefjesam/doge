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
            "❌ Mist Groq-credentials! Voeg ze toe in `.streamlit/secrets.toml`:\n"
            "[groq]\n"
            "api_key = \"...\"\n"
        )
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

# ─── Functie om maatregelen op te halen ───────────────────────────────────
def fetch_measures():
    query = '*[_type == "beheersmaatregel"][].tekst'
    return groq_client.fetch(query) or ["Geen voorstel beschikbaar"]

# ─── Document uitlezen ────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

# ─── Document genereren ─────────────────────────────────────────────────
def create_docx(template_path: str, source_paths: list[str], out_path: str) -> None:
    items = []
    measures = fetch_measures()
    for i, src in enumerate(source_paths):
        text = read_docx(src)
        items.append({
            "Risico": os.path.basename(src),
            "Oorzaak": (text[:200] + "...") if text else "",
            "Beheersmaatregel": measures[i % len(measures)]
        })
    context = {"risks": items}
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(out_path)

# ─── Streamlit UI ────────────────────────────────────────────────────────
st.sidebar.header("Upload bestanden")

tpl_file = st.sidebar.file_uploader("Upload DOCX Template", type=["docx"])
src_files = st.sidebar.file_uploader("Upload Brondocumenten", type=["docx"], accept_multiple_files=True)

if tpl_file and src_files:
    # Maak tijdelijke map
    tmp_dir = tempfile.mkdtemp()
    # Sla template op
    tpl_path = os.path.join(tmp_dir, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(tpl_file.getbuffer())

    # Sla brondocumenten op
    src_paths = []
    for sf in src_files:
        p = os.path.join(tmp_dir, sf.name)
        with open(p, "wb") as out:
            out.write(sf.getbuffer())
        src_paths.append(p)

    # Rechter scherm met twee kolommen: template & eerste brondocument
    st.subheader("Voorbeeldweergave documenten")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Template:** {tpl_file.name}")
        st.write(read_docx(tpl_path))
    with col2:
        st.markdown(f"**Brondocument:** {src_files[0].name}")
        st.write(read_docx(src_paths[0]))

    # Knop onder de weergave
    if st.button("Vul template aan met nieuwe/vervangende informatie"):
        out_path = os.path.join(tmp_dir, "resultaat.docx")
        create_docx(tpl_path, src_paths, out_path)
        with open(out_path, "rb") as f:
            st.download_button(
                label="Download ingevuld document",
                data=f,
                file_name="resultaat.docx"
            )
else:
    st.info("Upload een template en minimaal één brondocument via de zijbalk.")