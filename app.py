import os
import tempfile
from docxtpl import DocxTemplate
import pandas as pd
import streamlit as st
from groq import Groq

# ─── Load .env if present (optional) ───────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Streamlit Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")

# ─── Groq API-client initialisatie via omgevingsvariabelen ────────────────
def get_groq_client():
    api_key    = os.getenv("GROQ_API_KEY", "").strip()
    project_id = os.getenv("GROQ_PROJECT_ID", "").strip()
    dataset    = os.getenv("GROQ_DATASET", "").strip()

    if not api_key:
        st.sidebar.error("⚠️ GROQ_API_KEY niet gevonden in omgevingsvariabelen.")
        st.stop()
    if not project_id or not dataset:
        st.sidebar.error("⚠️ GROQ_PROJECT_ID of GROQ_DATASET niet ingesteld in omgevingsvariabelen.")
        st.stop()

    try:
        client = Groq(api_key=api_key, project_id=project_id, dataset=dataset)
        _ = client.models.list()
        st.sidebar.success("🔑 Verbonden met Groq API")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

# Initialise client
groq_client = get_groq_client()

# ─── Functie om maatregelen op te halen ────────────────────────────────────
def fetch_measures():
    query = '*[_type == "beheersmaatregel"][].tekst'
    return groq_client.fetch(query) or []

# ─── Functies voor documentverwerking ─────────────────────────────────────
def extract_headers(template_path: str) -> list[str]:
    doc = DocxTemplate(template_path)
    return [cell.text.strip() for cell in doc.docx.tables[0].rows[0].cells]

def extract_data(paths: list[str]) -> list[dict]:
    return [{
        "Risico": f"Risico uit {os.path.basename(p)}",
        "Oorzaak": f"Oorzaak uit {os.path.basename(p)}",
        "Beheersmaatregel": None
    } for p in paths]

def fill_measures(items: list[dict]) -> list[dict]:
    measures = fetch_measures() or ["Geen voorstel beschikbaar"]
    for i, item in enumerate(items):
        if not item["Beheersmaatregel"]:
            item["Beheersmaatregel"] = measures[i % len(measures)]
    return items

def create_docx(template_path: str, df: pd.DataFrame, out_path: str) -> None:
    context = {"risks": df.to_dict(orient="records")}
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(out_path)

# ─── Streamlit UI-workflow ────────────────────────────────────────────────
st.sidebar.header("Stap 1: Upload bestanden")
template_file = st.sidebar.file_uploader("Upload DOCX Template", type=["docx"])
sources = st.sidebar.file_uploader("Upload brondocumenten", type=["docx"], accept_multiple_files=True)

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

    st.subheader("Stap 2: Kolommen uit template")
    st.write(extract_headers(tpl_path))

    data = extract_data(src_paths)
    df = pd.DataFrame(fill_measures(data))

    st.subheader("Stap 3: Controleer en bewerk")
    edited = st.experimental_data_editor(df, num_rows="dynamic")

    st.subheader("Stap 4: Genereer DOCX")
    if st.button("Genereer document"):
        out_file = os.path.join(tmp_dir, "resultaat.docx")
        create_docx(tpl_path, edited, out_file)
        with open(out_file, "rb") as file:
            st.download_button(
                label="Download .docx",
                data=file,
                file_name="resultaat.docx"
            )
else:
    st.info("Upload een template en minimaal één brondocument om te starten.")