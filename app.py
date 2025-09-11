import os
import shutil
import uuid
from docxtpl import DocxTemplate
import groq

"""
Eenvoudige CLI-tool voor het genereren van DOCX documenten uit een template
en het ophalen van beheersmaatregelen via GROQ.
Usage:
  export GROQ_API_KEY=...
  export GROQ_PROJECT_ID=...
  export GROQ_DATASET=...
  python app.py --template path/to/template.docx --sources path/to/source1.docx path/to/source2.docx --output path/to/output.docx

Werkstappen:
1. Lees template in met docxtpl
2. Haal variabelen (kolomnamen) uit de eerste tabelrij van het template
3. Extract eenvoudige risico- en oorzaak-data uit bronnen (placeholder)
4. Haal beheersmaatregelen op via GROQ API
5. Vul context met data en render het resultaat
6. Sla op naar opgegeven outputpad
"""

def get_groq_client():
    api_key = os.getenv('GROQ_API_KEY')
    project_id = os.getenv('GROQ_PROJECT_ID')
    dataset = os.getenv('GROQ_DATASET')
    if not all([api_key, project_id, dataset]):
        raise EnvironmentError('GROQ_API_KEY, GROQ_PROJECT_ID en GROQ_DATASET moeten ingesteld zijn als omgevingsvariabelen')
    return groq.Client(project_id=project_id, dataset=dataset, api_key=api_key)


def fetch_measures_from_groq():
    """
    Vraagt vanuit de GROQ Dataset alle beheersmaatregelen op.
    Verwacht documenten van type 'beheersmaatregel' met veld 'tekst'.
    """
    client = get_groq_client()
    query = '*[_type == "beheersmaatregel"][].tekst'
    results = client.fetch(query)
    return results or []


def extract_table_headers(template_path):
    doc = DocxTemplate(template_path)
    table = doc.docx.tables[0]
    return [cell.text.strip() for cell in table.rows[0].cells]


def extract_data_from_sources(source_paths):
    """
    Placeholder: vul risico's en oorzaken uit bron-documenten.
    Vervang door eigen logica (regex, NLP) indien nodig.
    """
    data = []
    for path in source_paths:
        filename = os.path.basename(path)
        data.append({
            'risico': f'Risico uit {filename}',
            'oorzaak': f'Oorzaak uit {filename}',
            'beheersmaatregel': None
        })
    return data


def fill_missing_measures(data):
    """
    Vul lege beheersmaatregel-velden met items uit GROQ dataset.
    Loopt cyclisch door de beschikbare maatregelen.
    """
    measures = fetch_measures_from_groq()
    if not measures:
        print('Geen beheersmaatregelen gevonden via GROQ, gebruik standaard tekst')
        measures = ['Geen voorstel beschikbaar']
    idx = 0
    for item in data:
        if not item.get('beheersmaatregel'):
            item['beheersmaatregel'] = measures[idx % len(measures)]
            idx += 1
    return data


def generate_docx(template_path, source_paths, output_path):
    # Stap 1: headers
    headers = extract_table_headers(template_path)
    print(f'Gevonden kolommen in template: {headers}')

    # Stap 2: data-extractie
    data = extract_data_from_sources(source_paths)

    # Stap 3: vul beheersmaatregelen via GROQ
    data = fill_missing_measures(data)

    # Maak context voor docxtpl: verwacht 'risks' met list of dicts
    context = {'risks': data}

    # Render en sla op
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)
    print(f'Document gegenereerd: {output_path}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Genereer DOCX uit template en bronnen, met GROQ')
    parser.add_argument('--template', '-t', required=True, help='Pad naar DOCX-template')
    parser.add_argument('--sources', '-s', nargs='+', required=True, help='Pad(s) naar bron-DOCX file(s)')
    parser.add_argument('--output', '-o', required=True, help='Pad voor output DOCX')
    args = parser.parse_args()

    # Controleer paden
    if not os.path.isfile(args.template):
        raise FileNotFoundError(f'Template niet gevonden: {args.template}')
    for src in args.sources:
        if not os.path.isfile(src):
            raise FileNotFoundError(f'Source niet gevonden: {src}')

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    generate_docx(args.template, args.sources, args.output)
