import os
import tempfile
from docxtpl import DocxTemplate
import pandas as pd
import streamlit as st
import groq

# ——— GROQ-klant en fetch-functies (zelfde als eerder) ———
def get_groq_client():
    api_key    = os.getenv('GROQ_API_KEY')
    project_id = os.getenv('GROQ_PROJECT_ID')
    dataset    = os.getenv('GROQ_DATASET')
    if not all([api_key, project_id, dataset]):
        st.error('Stel GROQ_API_KEY, GROQ_PROJECT_ID en GROQ_DATASET in als omgevingsvariabelen')
        st.stop()
    return groq.Client(project_id=project_id, dataset=dataset, api_key=api_key)

def fetch_measures_from_groq():
    client = get_groq_client()
    query  = '*[_type == "beheersmaatregel"][].tekst'
    return client.fetch(query) or []

# ——— Extractie- en render-functies ———
def extract_table_headers(template_path):
    doc = DocxTemplate(template_path)
    table = doc.docx.tables[0]
    return [cell.text.strip() for cell in table.rows[0].cells]

def extract_data_from_sources(source_paths):
    data = []
    for path in source_paths:
        fn = os.path.basename(path)
        data.append({'Risico': f'Risico uit {fn}', 'Oorzaak': f'Oorzaak uit {fn}', 'Beheersmaatregel': None})
    return data

def fill_missing_measures(data):
    measures = fetch_measures_from_groq()
    if not measures:
        measures = ['Geen voorstel beschikbaar']
    idx = 0
    for item in data:
        if not item['Beheersmaatregel']:
            item['Beheersmaatregel'] = measures[idx % len(measures)]
            idx += 1
    return data

def generate_docx(template_path, df, output_path):
    context = {'risks': df.to_dict(orient='records')}
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)

# ——— Streamlit UI ———
st.set_page_config(page_title='DOCX Generator', layout='wide')
st.title("📄 DOCX Generator met Templates")

st.sidebar.header("Stap 1: Upload bestanden")
template_file = st.sidebar.file_uploader("Upload DOCX Template", type=['docx'])
sources       = st.sidebar.file_uploader("Upload Brondocumenten", type=['docx'], accept_multiple_files=True)

if template_file and sources:
    tmp_dir = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, 'template.docx')
    with open(tpl_path, 'wb') as f: f.write(template_file.getbuffer())
    src_paths = []
    for f in sources:
        p = os.path.join(tmp_dir, f.name)
        with open(p, 'wb') as out: out.write(f.getbuffer())
        src_paths.append(p)

    st.markdown("### Stap 2: Gevonden kolommen")
    st.write(extract_table_headers(tpl_path))

    data = extract_data_from_sources(src_paths)
    data = fill_missing_measures(data)
    df = pd.DataFrame(data)

    st.markdown("### Stap 3: Controleer en bewerk")
    edited = st.experimental_data_editor(df, num_rows="dynamic")

    st.markdown("### Stap 4: Genereer DOCX")
    if st.button("Genereer document"):
        out = os.path.join(tmp_dir, 'resultaat.docx')
        generate_docx(tpl_path, edited, out)
        with open(out, 'rb') as f:
            st.download_button("Download .docx", f, file_name="resultaat.docx")
else:
    st.info("Upload eerst een template en minimaal één brondocument via de zijbalk.")
