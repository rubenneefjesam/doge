import os
import tempfile

from docxtpl import DocxTemplate
import pandas as pd
import streamlit as st
from groq import Groq  # juiste import

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
        # (optioneel) korte validatie-call:
        # bijvoorbeeld client.health() of een andere eenvoudige call
        st.sidebar.success("🔑 Verbonden met Groq API")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

groq_client = get_groq_client()

# ─── Functie om maatregelen op te halen ───────────────────────────────────
def fetch_measures():
    query = '*[_type == "beheersmaatregel"][].tekst'
    return groq_client.fetch(query) or ["Geen voorstel beschikbaar"]

# ─── Document-extractie & transformatie ─────────────────────────────────
def extract_headers(template_path: str) -> list[str]:
    doc = DocxTemplate(template_path)
    return [cell.text.strip() for cell in doc.docx.tables[0].rows[0].cells]

def extract_data(paths: list[str]) -> list[dict]:
    return [
        {
            "Risico": f"Risico uit {os.path.basename(p)}",
            "Oorzaak": f"Oorzaak uit {os.path.basename(p)}",
            "Beheersmaatregel": None
        }
        for p in paths
    ]

def fill_measures(items: list[dict]) -> list[dict]:
    measures = fetch_measures()
    for i, item in enumerate(items):
        if not item["Beheersmaatregel"]:
            item["Beheersmaatregel"] = measures[i % len(measures)]
    return items

def create_docx(template_path: str, df: pd.DataFrame, out_path: str) -> None:
    context = {"risks": df.to_dict(orient="records")}
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(out_path)

# ─── Streamlit UI ────────────────────────────────────────────────────────
st.sidebar.header("Stap 1: Upload bestanden")
template_file = st.sidebar.file_uploader("Upload DOCX Template", type=["docx"])
source_files  = st.sidebar.file_uploader("Upload Brondocumenten", type=["docx"], accept_multiple_files=True)

if template_file and source_files:
    tmp_dir  = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(template_file.getbuffer())

    paths = []
    for sf in source_files:
        p = os.path.join(tmp_dir, sf.name)
        with open(p, "wb") as out:
            out.write(sf.getbuffer())
        paths.append(p)

    # Stap 2: Toon kolommen uit template
    st.subheader("Stap 2: Gevonden kolommen")
    st.write(extract_headers(tpl_path))

    # Stap 3: Data extraheren en aanvullen
    data = extract_data(paths)
    df   = pd.DataFrame(fill_measures(data))

    # Stap 4: Controleer en bewerk
    st.subheader("Stap 3: Controleer en bewerk")
    edited = st.experimental_data_editor(df, num_rows="dynamic")

    # Stap 5: Genereer DOCX
    st.subheader("Stap 4: Genereer document")
    if st.button("Genereer document"):
        out_file = os.path.join(tmp_dir, "resultaat.docx")
        create_docx(tpl_path, edited, out_file)
        with open(out_file, "rb") as f:
            st.download_button(
                label="Download .docx",
                data=f,
                file_name="resultaat.docx"
            )
else:
    st.info("Upload eerst een template en minimaal één brondocument via de zijbalk.")
