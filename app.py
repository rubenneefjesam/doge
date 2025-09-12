import os
import tempfile
from docxtpl import DocxTemplate
import streamlit as st
import docx


# ─── Streamlit Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="DOCX Generator", layout="wide")
st.title("📄 DOCX Generator met Templates")


# ─── Functie om Groq-client op te halen (ongewijzigd) ┬────────────────────
from groq import Groq


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


# ─── Document uitlezen ────────────────────────────────────────────────────
def read_docx(path: str) -> str:
doc = docx.Document(path)
return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


# ─── Document genereren ─────────────────────────────────────────────────
def create_docx(template_path: str, source_paths: list[str], out_path: str) -> None:
# Simpele vullogica: voor elk bronbestand een maatregel
items = []
measures = fetch_measures()
for i, src in enumerate(source_paths):
items.append({
"Risico": os.path.basename(src),
"Oorzaak": read_docx(src)[:200] + "...",
"Beheersmaatregel": measures[i % len(measures)]
})
df_records = items
context = {"risks": df_records}
doc = DocxTemplate(template_path)
doc.render(context)
doc.save(out_path)


# ─── Streamlit UI ────────────────────────────────────────────────────────
# Zijbalk voor upload
st.sidebar.header("Upload bestanden")
tpl_file = st.sidebar.file_uploader("Upload DOCX Template", type=["docx"])
src_files = st.sidebar.file_uploader("Upload Brondocumenten (2 stuks)", type=["docx"], accept_multiple_files=True)


if tpl_file and src_files and len(src_files) == 2:
# Opslaan temp
tmp = tempfile.mkdtemp()
tpl_path = os.path.join(tmp, "template.docx")
with open(tpl_path, "wb") as f:
f.write(tpl_file.getbuffer())


src_paths = []
for sf in src_files:
p = os.path.join(tmp, sf.name)
with open(p, "wb") as out:
out.write(sf.getbuffer())
src_paths.append(p)


# Rechter scherm met twee kolommen
st.subheader("Voorbeeldweergave documenten")
col1, col2 = st.columns(2)
with col1:
st.markdown(f"**Template:** {tpl_file.name}")
st.write(read_docx(tpl_path))
with col2:
st.markdown(f"**Brondocument:** {src_files[1].name}")
st.write(read_docx(src_paths[1]))


# Button onder aan
if st.button("Vul template aan met nieuwe/vervangende informatie"):
out_path = os.path.join(tmp, "resultaat.docx")
create_docx(tpl_path, src_paths, out_path)
st.info("Upload een template en precies twee brondocumenten via de zijbalk.")