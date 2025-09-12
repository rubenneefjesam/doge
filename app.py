import os
import tempfile
from docxtpl import DocxTemplate
import streamlit as st
import docx
from groq import Groq

# ─── Streamlit Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")

# ─── Init Groq-client via st.secrets ──────────────────────────────────────
def get_groq_client():
    api_key = st.secrets.get("groq", {}).get("api_key", "").strip()
    if not api_key:
        st.sidebar.error("❌ Mist Groq-credentials! Voeg toe in `.streamlit/secrets.toml` onder [groq]")
        st.stop()
    try:
        client = Groq(api_key=api_key)
        st.sidebar.success("🔑 Verbonden met Groq API")
        return client
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()

groq_client = get_groq_client()

# ─── Hulpfuncties ────────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    """Lees alle paragraven uit een .docx en return als tekst."""
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

# ─── Vul placeholders via LLM en render template ─────────────────────────
def fill_placeholders(template_path: str, context_text: str) -> bytes:
    # Laad template om placeholders te detecteren
    tpl = DocxTemplate(template_path)
    # Haal ongedefinieerde variabelen (placeholders) op
    placeholders = list(tpl.get_undeclared_template_variables())

    # Prompt voor de LLM
    prompt = (
        "Je bent een geavanceerde content-assistent. In de template zijn de volgende placeholders aanwezig: "
        f"{', '.join(placeholders)}. "
        "Vul elke placeholder met de juiste tekst op basis van de onderstaande context. "
        "Geef alleen een JSON-object terug waarin elke key de naam is van de placeholder en de value de ingevulde tekst."
        f"\n\n=== CONTEXT ===\n{context_text}"
    )

    # Chat-call naar de LLM
        response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.0,
        messages=[
            {"role": "system", "content": (
                "Je bent een geavanceerde content-assistent."
                " Antwoord strikt met een geldig JSON-object zonder toelichting, markdown of extra tekst."
            )},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content.strip()

    # Parse JSON-output
    import json
    try:
        values = json.loads(content)
    except json.JSONDecodeError:
        # Toon wat er misging als raw output bij fout
        raise ValueError(f"JSON niet geldig:\n{content}")

    # Render de template met de ontvangen waarden
    import json
    values = json.loads(content)

    # Render de template met de ontvangen waarden
    tpl.render(values)

    # Sla op in een tijdelijk bestand en return de bytes
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tpl.save(tmp.name)
    tmp.seek(0)
    return tmp.read()

# ─── Streamlit UI ────────────────────────────────────────────────────────
st.sidebar.header("Upload bestanden")
tpl_file = st.sidebar.file_uploader("Upload DOCX Template", type=["docx"])
ctx_file = st.sidebar.file_uploader("Upload Context-bestand", type=["docx","txt"], help=".docx of .txt met de nieuwe inhoud")

if tpl_file and ctx_file:
    # Opslaan in tmp
    tmp_dir = tempfile.mkdtemp()
    tpl_path = os.path.join(tmp_dir, "template.docx")
    with open(tpl_path, "wb") as f:
        f.write(tpl_file.getbuffer())

    # Lees context
    if ctx_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        ctx_path = os.path.join(tmp_dir, "context.docx")
        with open(ctx_path, "wb") as f:
            f.write(ctx_file.getbuffer())
        context_text = read_docx(ctx_path)
    else:
        context_text = ctx_file.read().decode("utf-8", errors="ignore")

    # Preview
    st.subheader("Template Preview (eerste 200 tekens)")
    tpl_preview = read_docx(tpl_path)
    st.text(tpl_preview[:200] + ("…" if len(tpl_preview)>200 else ""))

    st.subheader("Context Preview (eerste 200 tekens)")
    st.text(context_text[:200] + ("…" if len(context_text)>200 else ""))

    # Knop voor invullen
    if st.button("🖋️ Vul template met context"):
        st.info("Bezig met invullen…")
        try:
            filled_bytes = fill_placeholders(tpl_path, context_text)
            st.download_button(
                label="⬇️ Download ingevuld document",
                data=filled_bytes,
                file_name="gevuld_template.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Invullen mislukt: {e}")
else:
    st.info("Upload zowel je template als je context om te starten.")
