import os
from docxtpl import DocxTemplate
import groq

def get_groq_client():
    api_key    = os.getenv('GROQ_API_KEY')
    project_id = os.getenv('GROQ_PROJECT_ID')
    dataset    = os.getenv('GROQ_DATASET')
    if not all([api_key, project_id, dataset]):
        raise EnvironmentError(
            'Stel GROQ_API_KEY, GROQ_PROJECT_ID en GROQ_DATASET in als omgevingsvariabelen'
        )
    return groq.Client(project_id=project_id,
                       dataset=dataset,
                       api_key=api_key)

def fetch_measures_from_groq():
    """
    Haal alle beheersmaatregelen op uit Sanity via GROQ.
    Verwacht documenten van type 'beheersmaatregel' met veld 'tekst'.
    """
    client = get_groq_client()
    query  = '*[_type == "beheersmaatregel"][].tekst'
    results = client.fetch(query)
    return results or []

def fill_missing_measures(data):
    """
    Vul in je data-lijst lege 'beheersmaatregel'-velden
    cyclisch met de opgehaalde teksten.
    """
    measures = fetch_measures_from_groq()
    if not measures:
        measures = ['Geen voorstel beschikbaar']
    idx = 0
    for item in data:
        if not item.get('beheersmaatregel'):
            item['beheersmaatregel'] = measures[idx % len(measures)]
            idx += 1
    return data

# Voorbeeld in je generate-functie:
def generate_docx(template_path, source_paths, output_path):
    # … extractie van risico’s/oorzaken …
    data = extract_data_from_sources(source_paths)

    # hier komt de GROQ-lookup:
    data = fill_missing_measures(data)

    # renderen en bewaren
    doc = DocxTemplate(template_path)
    doc.render({'risks': data})
    doc.save(output_path)
