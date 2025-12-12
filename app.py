import streamlit as st
import requests
import xml.etree.ElementTree as ET
import time

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="DyeMind | Free AI Fluorophore Explorer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Hugging Face Token from Secrets
# Ensure .streamlit/secrets.toml has: huggingface_token = "hf_..."
if "huggingface_token" in st.secrets:
    HF_TOKEN = st.secrets["huggingface_token"]
else:
    st.error("🚨 Hugging Face Token missing! Add it to Streamlit Secrets.")
    st.stop()

# --- 2. THE NEW FREE AI ENGINE (Hugging Face) ---

def query_huggingface(payload):
    """
    Sends a prompt to the Mistral-7B-Instruct model via Hugging Face Free API.
    """
    API_URL = "https://api-inference.huggingface.co/models/EssentialAI/rnj-1-instruct"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def parse_hf_output(output):
    """
    Tries to extract generated text from common HF Inference API formats.
    """
    # Case 1: list with generated_text (classic text-generation format)
    if isinstance(output, list) and len(output) > 0 and isinstance(output[0], dict):
        if "generated_text" in output[0]:
            return output[0]["generated_text"]

    # Case 2: dict with generated_text
    if isinstance(output, dict) and "generated_text" in output:
        return output["generated_text"]

    # No recognized text
    return None

def generate_ai_review(chem_data, articles, query):
    """
    Synthesizes a scientific review using free open-source AI.
    """
    # 1. Prepare Context
    chem_context = f"SMILES: {chem_data['smiles']}" if chem_data else "Structure unavailable."

    lit_context = ""
    if articles:
        for i, art in enumerate(articles[:3]):  # Limit to top 3 to fit free context window
            lit_context += f"- Title: {art['title']}\n  Abstract: {art['abstract'][:300]}...\n"
    else:
        lit_context = "No specific literature abstracts found in PubMed."

    # 2. Construct the Prompt (Optimized for Mistral)
    prompt = f"""[INST] You are an expert chemical biologist. Write a short, professional scientific summary for the fluorescent probe: "{query}".

Use these data sources:
CHEMISTRY: {chem_context}
LITERATURE: 
{lit_context}

Format the response strictly as follows:
**1. Overview:** What is it and what is it used for?
**2. Properties:** Mention structure and excitation/emission if known.
**3. Performance:** Extract any Limit of Detection (LOD) or sensitivity mentions.
**4. Applications:** Key use cases (e.g. mitochondria, ROS, ions).

Keep it concise, scientific, and factual. Do not hallucinate data. [/INST]
"""

    # 3. Call API with simple retry
    with st.spinner("🧠 AI is thinking (Free Tier)..."):
        for attempt in range(3):
            output = query_huggingface({
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 600,
                    "temperature": 0.3,
                    "return_full_text": False
                }
            })

            # Handle error structure
            if isinstance(output, dict) and "error" in output:
                # Free-tier loading / warm-up
                if "loading" in output["error"].lower():
                    time.sleep(3)
                    continue
                return f"⚠️ AI Error: {output['error']}"

            # Try to parse text
            text = parse_hf_output(output)
            if text:
                return text

        return "⚠️ AI Service Busy or unexpected response format. Please try again in 30 seconds."

# --- 3. DATA FETCHING UTILITIES ---

@st.cache_data(show_spinner=False)
def get_pubchem_data(query):
    """Fetches chemical structure & SMILES."""
    try:
        base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
        search = requests.get(
            f"{base_url}/compound/name/{query}/cids/JSON",
            timeout=30
        ).json()
        cid = search['IdentifierList']['CID'][0]

        props = requests.get(
            f"{base_url}/compound/cid/{cid}/property/CanonicalSMILES,MolecularFormula,MolecularWeight/JSON",
            timeout=30
        ).json()
        prop_data = props['PropertyTable']['Properties'][0]

        return {
            "cid": cid,
            "smiles": prop_data.get('CanonicalSMILES', 'N/A'),
            "formula": prop_data.get('MolecularFormula', 'N/A'),
            "image": f"{base_url}/compound/cid/{cid}/PNG?record_type=2d&image_size=large",
            "link": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        }
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def get_pubmed_literature(query):
    """Fetches real abstracts from PubMed."""
    try:
        db_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        term = f"{query} AND (fluorescent OR probe OR sensor)"
        search = requests.get(
            f"{db_url}/esearch.fcgi?db=pubmed&term={term}&retmode=json&retmax=5&sort=relevance",
            timeout=30
        ).json()
        ids = search.get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        details = requests.get(
            f"{db_url}/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml",
            timeout=30
        ).content
        root = ET.fromstring(details)

        articles = []
        for art in root.findall(".//PubmedArticle"):
            title = art.findtext(".//ArticleTitle")
            abstract = art.findtext(".//AbstractText")
            if abstract:
                articles.append({"title": title, "abstract": abstract})
        return articles
    except Exception:
        return []

# --- 4. UI LAYOUT ---

with st.sidebar:
    st.title("🧪 DyeMind")
    st.caption("Free AI-Powered Fluorophore Explorer")
    st.markdown("Created by **Dr. Joy Karmakar**")
    st.success("🟢 Running on Free Open-Source AI")

st.title("🧠 DyeMind: The Fluorophore Scientist")
st.markdown(
    "Enter a dye name (e.g., *'Bimane'*, *'Fura-2'*, *'Rhodamine B'*) "
    "to generate a scientific review."
)

query = st.text_input("🔍 Search Query:", placeholder="Type a fluorescent probe name...")

if query:
    # Status Indicator
    status_placeholder = st.empty()
    status_placeholder.info("🔬 Searching scientific databases...")

    col1, col2 = st.columns([1, 2])

    # 1. Fetch PubChem Data
    chem = get_pubchem_data(query)

    if chem:
        with col1:
            st.image(
                chem['image'],
                caption=f"Structure (CID: {chem['cid']})",
                use_container_width=True
            )
            st.code(chem['smiles'], language="text")
            st.markdown(f"[View on PubChem]({chem['link']})")

    # 2. Fetch Literature
    articles = get_pubmed_literature(query)

    # 3. Generate AI Review
    with col2:
        if chem or articles:
            status_placeholder.info("🧠 Synthesizing data with AI (Mistral-7B)...")
            review = generate_ai_review(chem, articles, query)
            status_placeholder.empty()

            st.subheader("📝 AI Scientific Summary")
            st.markdown(review)

            # Download Button
            st.download_button(
                "📥 Download Report",
                review,
                file_name=f"{query}_report.md"
            )
        else:
            status_placeholder.warning("No data found. Check spelling or try a different dye.")

    # 4. Show Literature Sources
    if articles:
        st.divider()
        st.subheader("📚 Key Literature (PubMed)")
        for art in articles:
            with st.expander(art['title']):
                st.write(art['abstract'])
