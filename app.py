import streamlit as st
import requests
import xml.etree.ElementTree as ET
import time
import os

# ==================================================
# PAGE CONFIG (CORRECT API NAME)
# ==================================================
st.set_page_config(
    page_title="DyeMind | Free AI Fluorophore Explorer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# SECRET HANDLING (ROBUST)
# ==================================================
HF_TOKEN = (
    os.environ.get("HF_TOKEN")
    or os.environ.get("HFTOKEN")
    or st.secrets.get("HF_TOKEN", None)
    or st.secrets.get("HFTOKEN", None)
)

if not HF_TOKEN:
    st.error("🚨 Hugging Face Token missing. Add HF_TOKEN in Streamlit Secrets.")
    st.stop()

# ==================================================
# HUGGING FACE AI
# ==================================================
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def query_huggingface(prompt):
    for _ in range(3):
        response = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 600,
                    "temperature": 0.3,
                    "return_full_text": False
                }
            },
            timeout=60
        )
        output = response.json()

        if isinstance(output, dict) and "error" in output:
            if "loading" in output["error"].lower():
                time.sleep(3)
                continue
            return f"⚠️ AI Error: {output['error']}"

        if isinstance(output, list) and "generated_text" in output[0]:
            return output[0]["generated_text"]

    return "⚠️ AI service busy. Please try again."

# ==================================================
# DATA FETCHING (CACHED – CORRECT DECORATOR)
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
        ids = requests.get(
            f"{base}/esearch.fcgi?db=pubmed&term={term}&retmode=json&retmax=5",
            timeout=10
        ).json()["esearchresult"]["idlist"]

        if not ids:
            return []

        xml = requests.get(
            f"{base}/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml",
            timeout=10
        ).content

        root = ET.fromstring(xml)
        articles = []
        for a in root.findall(".//PubmedArticle"):
            title = a.findtext(".//ArticleTitle")
            abstract = a.findtext(".//AbstractText")
            if abstract:
                articles.append({"title": title, "abstract": abstract})
        return articles
    except:
        return []

# ==================================================
# AI SYNTHESIS
# ==================================================
def generate_ai_report(query, wiki, chem, articles):
    wiki_text = wiki[0] if wiki[0] else "No Wikipedia data."
    chem_text = f"SMILES: {chem['smiles']} | Formula: {chem['formula']}" if chem else "No chemical data."
    lit_text = "\n".join(
        [f"- {a['title']}: {a['abstract'][:250]}..." for a in]()
