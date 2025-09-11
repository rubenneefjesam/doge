import os
import tempfile
from docxtpl import DocxTemplate
import pandas as pd
import streamlit as st

# Functies uit CLI-tool hergebruiken
def extract_table_headers(template_path):
    doc = DocxTemplate(template_path)
    table = doc.docx.tables[0]
    return [cell.text.strip() for cell in table.rows[0].cells]

def extract_data_from_sources(source_paths):
    data = []
    for path in source_paths:
        filename = os.path.basename(path)
        data.append({
            'Risico': f'Risico uit {filename}',
            'Oorzaak': f'Oorzaak uit {filename}',
            'Beheersmaatregel': ''
        })
    return data

def fill_missing_measures(data):
    for item in data:
        if not item['Beheersmaatregel']:
            item['Beheersmaatregel'] = 'Voorstel maatregel...'
    return data

def generate_docx(template_path, df, output_path):
    context = {'risks': df.to_dict(orient='records')}
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)

# Streamlit UI
st.set_page_config(page_title='DOCX Generator', layout='wide')
st.title("📄 DOCX Generator met Templates")

# Sidebar voor uploads
st.sidebar.header("Stap 1: Upload bestanden")
template_file = st.sidebar.file_uploader("Upload DOCX Template", type=['docx'])
sources = st.sidebar.file_uploader("Upload Brondocumenten (meerdere)", type=['docx'], accept_multiple_files=True)

if template_file and sources:
    # Opslaan naar tijdelijke bestanden
    tmp_dir = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, 'template.docx')
    with open(tpl_path, 'wb') as f:
        f.write(template_file.getbuffer())
    source_paths = []
    for f in sources:
        p = os.path.join(tmp_dir, f.name)
        with open(p, 'wb') as out:
            out.write(f.getbuffer())
        source_paths.append(p)

    # Stap 2: Headers en Data Extractie
    headers = extract_table_headers(tpl_path)
    st.markdown("### Stap 2: Gevonden kolommen uit template")
    st.write(headers)

    data = extract_data_from_sources(source_paths)
    data = fill_missing_measures(data)
    df = pd.DataFrame(data)

    st.markdown("### Stap 3: Controleer en bewerk de data")
    edited_df = st.experimental_data_editor(df, num_rows="dynamic")

    # Stap 4: Generatie
    st.markdown("### Stap 4: Genereer DOCX-bestand")
    if st.button("Genereer Document"):
        output_path = os.path.join(tmp_dir, 'output.docx')
        generate_docx(tpl_path, edited_df, output_path)
        with open(output_path, 'rb') as f:
            st.download_button("Download Document", f, file_name='resultaat.docx')
else:
    st.info("Upload een DOCX-template en minimaal één brondocument via de zijbalk.")
