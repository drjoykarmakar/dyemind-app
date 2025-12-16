import streamlit as st
import requests
import xml.etree.ElementTree as ET
import time
import os

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="DyeMind | Free AI Fluorophore Explorer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# SECRETS
# ==================================================
HF_TOKEN = (
    os.environ.get("HF_TOKEN")
    or os.environ.get("HFTOKEN")
    or st.secrets.get("HF_TOKEN")
    or st.secrets.get("HFTOKEN")
)

if not HF_TOKEN:
    st.error("🚨 Hugging Face token missing. Add HF_TOKEN to Streamlit Secrets.")
    st.stop()

# ==================================================
# HUGGING FACE ROUTER API
# ==================================================
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"

HF_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

def query_huggingface(prompt):
    for _ in range(3):
        response = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 700,
                    "temperature": 0.3,
                    "return_full_text": False
                }
            },
            timeout=60
        )

        if response.status_code != 200:
            time.sleep(3)
            continue

        try:
            output = response.json()
        except ValueError:
            time.sleep(3)
            continue

        if isinstance(output, dict) and "error" in output:
            if "loading" in output["error"].lower():
                time.sleep(3)
                continue
            return f"⚠️ AI Error: {output['error']}"

        if isinstance(output, list) and output and "generated_text" in output[0]:
            return output[0]["generated_text"]

    return (
        "⚠️ AI service temporarily unavailable.\n\n"
        "Please wait ~30 seconds and try again."
    )

# ==================================================
# DATA FETCHERS
# ==================================================
@st.cache_data(show_spinner=False)
def get_wikipedia_intro(query):
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return d.get("extract"), d.get("content_urls", {}).get("desktop", {}).get("page")
    except:
        pass
    return None, None


@st.cache_data(show_spinner=False)
def get_pubchem_data(query):
    try:
        base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

        cid = requests.get(
            f"{base}/compound/name/{query}/cids/JSON",
            timeout=10
        ).json()["IdentifierList"]["CID"][0]

        props = requests.get(
            f"{base}/compound/cid/{cid}/property/CanonicalSMILES,MolecularFormula/JSON",
            timeout=10
        ).json()["PropertyTable"]["Properties"][0]

        return {
            "cid": cid,
            "smiles": props.get("CanonicalSMILES"),
            "formula": props.get("MolecularFormula"),
            "image": f"{base}/compound/cid/{cid}/PNG?image_size=large",
            "link": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        }
    except:
        return None


@st.cache_data(show_spinner=False)
def get_pubmed_literature(query):
    try:
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        term = f"{query} fluorescent probe"

        search = requests.get(
            f"{base}/esearch.fcgi?db=pubmed&term={term}&retmode=json&retmax=5",
            timeout=10
        ).json()

        ids = search["esearchresult"]["idlist"]
        if not ids:
            return []

        fetch = requests.get(
            f"{base}/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml",
            timeout=10
        ).content

        root = ET.fromstring(fetch)

        articles = []
        for art in root.findall(".//PubmedArticle"):
            title = art.findtext(".//ArticleTitle")
            abstract = art.findtext(".//AbstractText")
            pmid = art.findtext(".//PMID")

            if title and abstract and pmid:
                articles.append({
                    "title": title,
                    "abstract": abstract,
                    "pmid": pmid,
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })

        return articles
    except:
        return []

# ==================================================
# AI SYNTHESIS
# ==================================================
def generate_ai_report(query, wiki, chem, articles):
    wiki_text = wiki[0] if wiki[0] else "No Wikipedia introduction available."
    chem_text = (
        f"SMILES: {chem['smiles']} | Formula: {chem['formula']}"
        if chem else "No chemical data available."
    )

    lit_text = (
        "\n".join(
            [f"- {a['title']}: {a['abstract'][:250]}..." for a in articles]
        )
        if articles else "No relevant literature found."
    )

    prompt = f"""[INST]
You are an expert fluorescent probe scientist.

Write a concise, factual scientific summary for "{query}".

WIKIPEDIA:
{wiki_text}

CHEMISTRY:
{chem_text}

LITERATURE:
{lit_text}

RULES:
- Do NOT hallucinate excitation/emission values
- Do NOT invent LOD values
- Academic tone only

FORMAT:
**Overview**
**Chemical Properties**
**Performance**
**Applications**
**Limitations**
[/INST]
"""
    return query_huggingface(prompt)

# ==================================================
# UI
# ==================================================
with st.sidebar:
    st.title("🧪 DyeMind")
    st.caption("Free AI Fluorophore Explorer")
    st.markdown("**Dr. Joy Karmakar**")
    st.success("Running on Free Open-Source AI")

st.title("🧠 DyeMind: The Fluorophore Scientist")

query = st.text_input(
    "🔍 Enter fluorophore name or topic",
    placeholder="e.g. Bimane, Rhodamine B, Fura-2"
)

if query:
    with st.spinner("🔬 Gathering data..."):
        wiki = get_wikipedia_intro(query)
        chem = get_pubchem_data(query)
        articles = get_pubmed_literature(query)

    col1, col2 = st.columns([1, 2])

    if chem:
        with col1:
            st.image(
                chem["image"],
                caption=f"PubChem CID: {chem['cid']}",
                use_container_width=True
            )
            st.code(chem["smiles"], language="text")
            st.markdown(f"[View on PubChem]({chem['link']})")

    with col2:
        report = generate_ai_report(query, wiki, chem, articles)
        st.subheader("📝 AI Scientific Summary")
        st.markdown(report)

        st.download_button(
            "📥 Download Report",
            report,
            file_name=f"{query.replace(' ', '_')}_DyeMind_Report.md"
        )

    if wiki[0]:
        st.divider()
        st.subheader("📘 Wikipedia Introduction")
        st.write(wiki[0])
        if wiki[1]:
            st.markdown(f"[Read more on Wikipedia]({wiki[1]})")

    if articles:
        st.divider()
        st.subheader("📚 PubMed References")
        for art in articles:
            with st.expander(art["title"]):
                st.markdown(f"[🔗 View on PubMed]({art['link']})")
                st.write(art["abstract"])
