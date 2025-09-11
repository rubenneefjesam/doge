import os
import tempfile
from docxtpl import DocxTemplate
import pandas as pd
import streamlit as st
from groq import Groq

# ─── Streamlit Page Config ─────────────────────────────────────────────────
st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")

# ─── Sidebar: API-configuratie ─────────────────────────────────────────────────
st.sidebar.header("🔧 API Configuratie")
# Laat gebruiker sleutel, project en dataset invullen
api_key = st.sidebar.text_input("Groq API Key", type="password")
project_id = st.sidebar.text_input("Groq Project ID")
dataset = st.sidebar.text_input("Groq Dataset")

# ─── Init Groq-client ──────────────────────────────────────────────────────────
def get_groq_client(key: str, proj: str, ds: str):
    if not (key and proj and ds):
        st.sidebar.warning("Vul API Key, Project ID en Dataset in om te verbinden.")
        return None
    try:
        client = Groq(api_key=key, project_id=proj, dataset=ds)
        client.models.list()  # korte validatie
        st.sidebar.success("🔑 Verbonden met Groq")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij Groq-verbinding: {e}")
        return None

# Haal client op
groq_client = get_groq_client(api_key, project_id, dataset)

# ─── Fetch-functie ──────────────────────────────────────────────────────────
def fetch_measures():
    if not groq_client:
        return []
    query = '*[_type == "beheersmaatregel"][].tekst'
    try:
        return groq_client.fetch(query) or []
    except Exception:
        return []

# ─── Document-extractie en transformatie ─────────────────────────────────────
def extract_headers(template_path: str) -> list[str]:
    doc = DocxTemplate(template_path)
    return [cell.text.strip() for cell in doc.docx.tables[0].rows[0].cells]

def extract_data(paths: list[str]) -> list[dict]:
    items = []
    for p in paths:
        name = os.path.basename(p)
        items.append({
            "Risico": f"Risico uit {name}",
            "Oorzaak": f"Oorzaak uit {name}",
            "Beheersmaatregel": None
        })
    return items

def fill_measures(items: list[dict]) -> list[dict]:
    measures = fetch_measures()
    if not measures:
        measures = ["Geen voorstel beschikbaar"]
    for i, it in enumerate(items):
        if it.get("Beheersmaatregel") is None:
            it["Beheersmaatregel"] = measures[i % len(measures)]
    return items

def create_docx(template_path: str, df: pd.DataFrame, out_path: str) -> None:
    context = {"risks": df.to_dict(orient="records")}
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(out_path)

# ─── Stap 1: Upload template en brondocumenten ─────────────────────────────────
st.sidebar.header("Stap 1: Upload bestanden")
tpl_file = st.sidebar.file_uploader("DOCX Template", type="docx")
src_files = st.sidebar.file_uploader("Brondocumenten", type="docx", accept_multiple_files=True)

if tpl_file and src_files:
    tmpd = tempfile.mkdtemp()
    tpl_path = os.path.join(tmpd, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(tpl_file.getbuffer())

    paths = []
    for sf in src_files:
        p = os.path.join(tmpd, sf.name)
        with open(p, "wb") as out:
            out.write(sf.getbuffer())
        paths.append(p)

    # ─── Stap 2: Toon kolommen uit template
    st.subheader("Stap 2: Gevonden kolommen")
    st.write(extract_headers(tpl_path))

    # ─── Stap 3: Data extraheren en aanvullen
    data = extract_data(paths)
    df = pd.DataFrame(fill_measures(data))

    # ─── Stap 4: Controleer en bewerk
    st.subheader("Stap 3: Controleer en bewerk")
    edited = st.experimental_data_editor(df, num_rows="dynamic")

    # ─── Stap 5: Genereer DOCX
    st.subheader("Stap 4: Genereer document")
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
    st.info("Upload een template en minimaal één brondocument in de zijbalk om te starte