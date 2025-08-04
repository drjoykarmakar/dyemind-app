
# 🧠 DyeMind – AI-Powered Fluorophore Explorer

**Created by Dr. Joy Karmakar (March 2025)**  
DyeMind is the **first unified AI platform for fluorescent molecules**, combining real-time structure visualization, literature mining, and intelligent summarization in one seamless experience.

---

## 🚀 What It Does

- 🔬 **Chemical Structure:** Retrieves fluorophore structures from PubChem  
- 📚 **Literature Search:** Finds related papers from PubMed in real time  
- 🧠 **AI Summarization:** Uses Hugging Face models to summarize abstracts  
- 🧬 **Wikipedia Intro:** Provides a quick contextual overview  
- 💬 **AI Q&A Box:** Ask questions about dyes, imaging, or use cases — get AI answers instantly

---

## 🌍 Why It Matters

Fluorophores are vital in:
- Biomedical imaging
- Diagnostics
- Biosensing
- Drug discovery

But finding and comparing them is hard — DyeMind changes that.

---

## 🛠️ Built With

- `Streamlit` – frontend and app framework  
- `PubChem API` – for chemical structure and SMILES  
- `PubMed eUtils API` – for biomedical articles  
- `Hugging Face Transformers` – for NLP and summarization  
- `Wikipedia REST API` – for background context  

---

## 📦 Installation (for local use)

```bash
git clone https://github.com/DrJoyKarmakar/dyemind-app.git
cd dyemind-app
pip install -r requirements.txt
streamlit run app.py
```

> 🔑 Set your Hugging Face token in a `.streamlit/secrets.toml` file:
```toml
huggingface_token = "your_hf_token_here"
```

---

## 🧠 Sample Questions for AI Assistant

- “What is the best dye for mitochondrial imaging?”
- “Compare BODIPY and Rhodamine for bioimaging.”
- “What are recent fluorophores used in cancer diagnosis?”

---

## 👨‍🔬 Author

**Dr. Joy Karmakar**  
Postdoctoral Researcher, UCSF  
Founder & CEO of DyeMind  
[dyemind.com](https://dyemind.com)
