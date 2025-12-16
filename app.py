import streamlit as st
import requests
import xml.etree.ElementTree as ET
import time
import os

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="DyeMind | Free AI Fluorophore Explorer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SECRET HANDLING (Optimized for Hugging Face) ---
# We check the Environment Variable "HF_TOKEN" first (for Hugging Face), 
# then checks local secrets (for local testing).
HF_TOKEN = os.environ.get("HF_TOKEN") or st.secrets.get("HF_TOKEN")

if not HF_TOKEN:
    st.error("🚨 Hugging Face Token missing! Please add 'HF_TOKEN' to your Space Settings.")
    st.stop()

# --- 2. THE NEW FREE AI ENGINE (Hugging Face) ---

def queryhuggingface(payload):
    """
    Sends a prompt to the Mistral-7B-Instruct model via Hugging Face Free API.
    """
    # Using Mistral-7B-Instruct-v0.3 (Newer & often more reliable)
    APIURL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(APIURL, headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def generateaireview(chemdata, articles, query):
    """
    Synthesizes a scientific review using free open-source AI.
    """
    # 1. Prepare Context
    chemcontext = f"SMILES: {chemdata['smiles']}" if chemdata else "Structure unavailable."
    
    litcontext = ""
    if articles:
        # Limit to top 3 articles to keep prompt size manageable for free tier
        for i, art in enumerate(articles[:3]): 
            litcontext += f"- Title: {art['title']}\n  Abstract: {art['abstract'][:300]}...\n"
    else:
        lit_context = "No specific literature abstracts found in PubMed."

    # 2. Construct the Prompt (Optimized for Mistral)
    prompt = f"""[INST] You are an expert chemical biologist. Write a short, professional scientific summary for the fluorescent probe: "{query}".

Use these data sources:
CHEMISTRY: {chemcontext}
LITERATURE: 
{litcontext}

Format the response strictly as follows:
1. Overview: What is it and what is it used for?
2. Properties: Mention structure and excitation/emission if known.
3. Performance: Extract any Limit of Detection (LOD) or sensitivity mentions.
4. Applications: Key use cases (e.g. mitochondria, ROS, ions).

Keep it concise, scientific, and factual. Do not hallucinate data. [/INST]
"""

    # 3. Call API with Retry Logic
    with st.spinner("🧠 AI is thinking (Free Tier)..."):
        # Retry logic for model wake-up (Cold Start)
        for attempt in range(3):
            output = queryhuggingface({
                "inputs": prompt,
                "parameters": {
                    "maxnewtokens": 600,
                    "temperature": 0.3,
                    "returnfulltext": False
                }
            })
            
            # Handle "Model Loading" error (common on free tier)
            if isinstance(output, dict) and "error" in output:
                errormsg = output["error"].lower()
                if "loading" in errormsg:
                    time.sleep(3) # Wait for model to wake up
                    continue
                else:
                    return f"⚠️ AI Error: {output['error']}"
            
            # Success
            if isinstance(output, list) and len(output) > 0 and "generatedtext" in output[0]:
                return output[0]["generated_text"]
            
        return "⚠️ AI Service Busy. Please try again in 30 seconds."

# --- 3. DATA FETCHING UTILITIES ---

@st.cachedata(showspinner=False)
def getpubchemdata(query):
    """Fetches chemical structure & SMILES."""
    try:
        baseurl = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
        search = requests.get(f"{baseurl}/compound/name/{query}/cids/JSON").json()
        cid = search['IdentifierList']['CID'][0]
        
        props = requests.get(f"{baseurl}/compound/cid/{cid}/property/CanonicalSMILES,MolecularFormula,MolecularWeight/JSON").json()
        propdata = props['PropertyTable']['Properties'][0]
        
        return {
            "cid": cid,
            "smiles": propdata.get('CanonicalSMILES', 'N/A'),
            "formula": propdata.get('MolecularFormula', 'N/A'),
            "image": f"{baseurl}/compound/cid/{cid}/PNG?recordtype=2d&image_size=large",
            "link": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        }
    except:
        return None

@st.cachedata(showspinner=False)
def getpubmedliterature(query):
    """Fetches real abstracts from PubMed."""
    try:
        # Search
        dburl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        term = f"{query} AND (fluorescent OR probe OR sensor)"
        search = requests.get(f"{dburl}/esearch.fcgi?db=pubmed&term={term}&retmode=json&retmax=5&sort=relevance").json()
        ids = search.get("esearchresult", {}).get("idlist", [])
        
        if not ids: return []
        
        # Fetch
        details = requests.get(f"{db_url}/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml").content
        root = ET.fromstring(details)
        
        articles = []
        for art in root.findall(".//PubmedArticle"):
            title = art.findtext(".//ArticleTitle")
            abstract = art.findtext(".//AbstractText")
            if abstract:
                articles.append({"title": title, "abstract": abstract})
        return articles
    except:
        return []

# --- 4. UI LAYOUT ---

with st.sidebar:
    st.title("🧪 DyeMind")
    st.caption("Free AI-Powered Fluorophore Explorer")
    st.markdown("Created by Dr. Joy Karmakar")
    st.success("🟢 Running on Free Open-Source AI")

st.title("🧠 DyeMind: The Fluorophore Scientist")
st.markdown("Enter a dye name (e.g., 'Bimane', 'Fura-2', 'Rhodamine B') to generate a scientific review.")

query = st.text_input("🔍 Search Query:", placeholder="Type a fluorescent probe name...")

if query:
    # Status Indicator
    statusplaceholder = st.empty()
    statusplaceholder.info("🔬 Searching scientific databases...")
    
    col1, col2 = st.columns([1, 2])
    
    # 1. Fetch PubChem Data
    chem = getpubchemdata(query)
    
    if chem:
        with col1:
            st.image(chem['image'], caption=f"Structure (CID: {chem['cid']})", usecontainerwidth=True)
            st.code(chem['smiles'], language="text", label="SMILES")
            st.markdown(f"[View on PubChem]({chem['link']})")
    
    # 2. Fetch Literature
    articles = getpubmedliterature(query)
    
    # 3. Generate AI Review
    with col2:
        if chem or articles:
            statusplaceholder.info("🧠 Synthesizing data with AI (Mistral-7B)...")
            review = generateaireview(chem, articles, query)
            statusplaceholder.empty()
            
            st.subheader("📝 AI Scientific Summary")
            st.markdown(review)
            
            # Download Button
            st.downloadbutton("📥 Download Report", review, filename=f"{query}report.md")
        else:
            statusplaceholder.warning("No data found. Check spelling or try a different dye.")

    # 4. Show Literature Sources
    if articles:
        st.divider()
        st.subheader("📚 Key Literature (PubMed)")
        for art in articles:
            with st.expander(art['title']):
                st.write(art['abstract'])
