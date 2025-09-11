from dotenv import load_dotenv
load_dotenv()  # moet vóór al je os.getenv-calls staan

import os
tempfile
from docxtpl import DocxTemplate
import pandas as pd
import streamlit as st
from groq import Groq

# ─── Init Groq-client ─────────────────────────────────────────────────
def get_groq_client():
    api_key    = os.getenv("GROQ_API_KEY", "").strip()
    project_id = os.getenv("GROQ_PROJECT_ID", "").strip()
    dataset    = os.getenv("GROQ_DATASET", "").strip()

    if not api_key:
        st.warning("⚠️ Geen GROQ_API_KEY gevonden. Functies met Groq falen.")
        return None
    if not all([project_id, dataset]):
        st.error("❌ Stel ook GROQ_PROJECT_ID en GROQ_DATASET in in je .env.")
        st.stop()

    try:
        client = Groq(api_key=api_key, project_id=project_id, dataset=dataset)
        # korte validatie
        _ = client.models.list()
        st.sidebar.success("🔑 Groq API key werkt!")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Ongeldige Groq-credentials: {e}")
        st.stop()

# maak de client direct beschikbaar
groq_client = get_groq_client()

# ─── GROQ-fetching ────────────────────────────────────────────────────
def fetch_measures_from_groq():
    if not groq_client:
        return []
    query = '*[_type == "beheersmaatregel"][].tekst'
    return groq_client.fetch(query) or []

# ─── Extractie- & render-functies ────────────────────────────────────
def extract_table_headers(template_path):
    doc = DocxTemplate(template_path)
    return [cell.text.strip() for cell in doc.docx.tables[0].rows[0].cells]

def extract_data_from_sources(source_paths):
    data = []
    for path in source_paths:
        fn = os.path.basename(path)
        data.append({
            "Risico": f"Risico uit {fn}",
            "Oorzaak": f"Oorzaak uit {fn}",
            "Beheersmaatregel": None
        })
    return data

def fill_missing_measures(data):
    measures = fetch_measures_from_groq()
    if not measures:
        measures = ["Geen voorstel beschikbaar"]
    for idx, item in enumerate(data):
        if not item["Beheersmaatregel"]:
            item["Beheersmaatregel"] = measures[idx % len(measures)]
    return data

def generate_docx(template_path, df, output_path):
    context = {"risks": df.to_dict(orient="records")}
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)

# ─── Streamlit UI ────────────────────────────────────────────────────
st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")

st.sidebar.header("Stap 1: Upload bestanden")
template_file = st.sidebar.file_uploader("Upload DOCX Template", type=["docx"])
sources       = st.sidebar.file_uploader("Upload Brondocumenten", type=["docx"], accept_multiple_files=True)

if template_file and sources:
    tmp_dir = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(template_file.getbuffer())

    src_paths = []
    for f in sources:
        p = os.path.join(tmp_dir, f.name)
        with open(p, "wb") as out:
            out.write(f.getbuffer())
        src_paths.append(p)

    st.markdown("### Stap 2: Gevonden kolommen")
    st.write(extract_table_headers(tpl_path))

    data = extract_data_from_sources(src_paths)
    df = pd.DataFrame(fill_missing_measures(data))

    st.markdown("### Stap 3: Controleer en bewerk")
    edited = st.experimental_data_editor(df, num_rows="dynamic")

    st.markdown("### Stap 4: Genereer DOCX")
    if st.button("Genereer document"):
        out = os.path.join(tmp_dir, "resultaat.docx")
        generate_docx(tpl_path, edited, out)
        with open(out, "rb") as f:
            st.download_button(
                "Download .docx",
                f,
                file_name="resultaat.docx"
            )
else:
    st.info("Upload eerst een template en minimaal één brondocument via de zijbalk.")