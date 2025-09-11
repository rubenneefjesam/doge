import os
import tempfile
from docxtpl import DocxTemplate
import pandas as pd
import streamlit as st
from groq import Groq

# ─── Init Groq-client ─────────────────────────────────────────────────
def get_groq_client():
    # Haal credentials uit omgevingsvariabelen
    api_key    = os.getenv("GROQ_API_KEY", "").strip()
    project_id = os.getenv("GROQ_PROJECT_ID", "").strip()
    dataset    = os.getenv("GROQ_DATASET", "").strip()

    if not api_key:
        st.warning("⚠️ Geen GROQ_API_KEY gevonden. Voer eerst in je terminal in:\nexport GROQ_API_KEY=je_key")
        return None
    if not project_id or not dataset:
        st.error("❌ Stel ook GROQ_PROJECT_ID en GROQ_DATASET in:\nexport GROQ_PROJECT_ID=... && export GROQ_DATASET=...")
        st.stop()

    try:
        client = Groq(api_key=api_key, project_id=project_id, dataset=dataset)
        _ = client.models.list()
        st.sidebar.success("🔑 Groq API key werkt!")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Ongeldige Groq-credentials: {e}")
        st.stop()

# Initialiseer client
groq_client = get_groq_client()

# ─── Fetch-functie ─────────────────────────────────────────────────────
def fetch_measures():
    if not groq_client:
        return []
    query = '*[_type == "beheersmaatregel"][].tekst'
    return groq_client.fetch(query) or []

# ─── Document-extractie
def extract_headers(template_path):
    doc = DocxTemplate(template_path)
    return [cell.text.strip() for cell in doc.docx.tables[0].rows[0].cells]

def extract_data(paths):
    items = []
    for p in paths:
        name = os.path.basename(p)
        items.append({
            "Risico": f"Risico uit {name}",
            "Oorzaak": f"Oorzaak uit {name}",
            "Beheersmaatregel": None
        })
    return items

# ─── Vul maatregelen aan
def fill_measures(items):
    measures = fetch_measures()
    if not measures:
        measures = ["Geen voorstel beschikbaar"]
    for i, it in enumerate(items):
        if not it["Beheersmaatregel"]:
            it["Beheersmaatregel"] = measures[i % len(measures)]
    return items

# ─── Genereer DOCX
def create_docx(template_path, df, out_path):
    ctx = {"risks": df.to_dict(orient="records")}
    doc = DocxTemplate(template_path)
    doc.render(ctx)
    doc.save(out_path)

# ─── Streamlit UI
st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")

st.sidebar.header("Stap 1: Upload bestanden")
tpl = st.sidebar.file_uploader("Upload DOCX Template", type="docx")
srcs = st.sidebar.file_uploader("Upload brondocs", type="docx", accept_multiple_files=True)

if tpl and srcs:
    tmpd = tempfile.mkdtemp()
    tpl_path = os.path.join(tmpd, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(tpl.getbuffer())

    paths = []
    for fobj in srcs:
        p = os.path.join(tmpd, fobj.name)
        with open(p, "wb") as out:
            out.write(fobj.getbuffer())
        paths.append(p)

    st.markdown("### Stap 2: Kolommen uit template")
    st.write(extract_headers(tpl_path))

    data = extract_data(paths)
    df = pd.DataFrame(fill_measures(data))

    st.markdown("### Stap 3: Controleer en bewerk")
    edited = st.experimental_data_editor(df, num_rows="dynamic")

    st.markdown("### Stap 4: Genereer DOCX")
    if st.button("Genereer document"):
        out = os.path.join(tmpd, "resultaat.docx")
        create_docx(tpl_path, edited, out)
        with open(out, "rb") as file:
            st.download_button(
                label="Download .docx",
                data=file,
                file_name="resultaat.docx"
            )
else:
    st.info("Upload eerst een template en minimaal één brondocument.")