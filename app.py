import os
import shutil
import uuid
from docxtpl import DocxTemplate

"""
Eenvoudige CLI-tool voor het genereren van DOCX documenten uit een template
zonder web-endpoints. Usage:
  python app.py --template path/to/template.docx --sources path/to/source1.docx path/to/source2.docx --output path/to/output.docx

Werkstappen:
1. Lees template in met docxtpl
2. Haal variabelen (kolomnamen) uit de eerste tabelrij van het template
3. Extract eenvoudige risico- en oorzaak-data uit bronnen (placeholder)
4. Vul context met data en render het resultaat
5. Sla op naar opgegeven outputpad
"""

def extract_table_headers(template_path):
    """
    Lees de kolomnamen uit de eerste rij van de eerste tabel in een DOCX-template.
    Retourneert een lijst van strings.
    """
    doc = DocxTemplate(template_path)
    table = doc.docx.tables[0]
    header_cells = table.rows[0].cells
    return [cell.text.strip() for cell in header_cells]


def extract_data_from_sources(source_paths):
    """
    Placeholder-functie om risico's en oorzaken uit bron-documents te halen.
    Moet later vervangen worden door echte extractielogica.
    Retourneert een lijst van dicts met keys 'risico', 'oorzaak', 'beheersmaatregel'.
    """
    # Simpele dummy-implementatie: telkens één voorbeeld per bestand
    data = []
    for path in source_paths:
        filename = os.path.basename(path)
        data.append({
            'risico': f'Risico uit {filename}',
            'oorzaak': f'Oorzaak uit {filename}',
            'beheersmaatregel': ''  # leeg: later vullen
        })
    return data


def fill_missing_measures(data):
    """
    Eenvoudige placeholder: vul ontbrekende beheersmaatregelen
    met een statische tekst. Kan later uitgebreid worden.
    """
    for item in data:
        if not item['beheersmaatregel']:
            item['beheersmaatregel'] = 'Voorstel maatregel...'
    return data


def generate_docx(template_path, source_paths, output_path):
    # Stap 1: headers
    headers = extract_table_headers(template_path)
    print(f'Gevonden kolommen in template: {headers}')

    # Stap 2: data-extractie
    data = extract_data_from_sources(source_paths)
    # Stap 3: vul ontbrekende beheersmaatregelen
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

    parser = argparse.ArgumentParser(description='Genereer DOCX uit template en bronnen')
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

