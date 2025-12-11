# 🛡️ Agentic RAG — Generic Url Scraper Chatbot

**Built by Mohammad Azharuddin**

A **fully generic Agentic RAG chatbot** that can convert **ANY website** or documents into an intelligent, searchable AI assistant simply by providing a **sitemap URL**.

The bot automatically:

* Recursively **crawls all sitemap links**
* Extracts + cleans website content
* Stores embeddings in **ChromaDB**
* Answers user questions using **Groq LLM**
* Uses **local documents** as a secondary knowledge base

Minimal setup, production-ready architecture.

---

## ⭐ Why This Bot Is Generic (Key Point)

You can turn **any website** into a chatbot in **2 steps**:

### **1️⃣ Replace the sitemap URL**

Example:

```env
ONSURITY_SITEMAP=https://www.onsurity.com/sitemap_index.xml
```

→ If you replace it with:

```env
ONSURITY_SITEMAP=https://coindcx.com/sitemap.xml
```

or

```env
ONSURITY_SITEMAP=https://your-company.com/sitemap.xml
```

The bot will:

* Detect if it’s a sitemap index
* Recursively load all nested sitemaps
* Crawl every valid webpage
* Extract text automatically
* Index the entire site into Chroma

No additional code changes needed.

### **2️⃣ (Optional) Add local documents**

Place files into:

```
data/insurance_docs/
```

The bot merges website-crawled knowledge + local KB automatically.

---

## 🔍 Key Features (SEO-Optimized)

* **Generic AI Website Chatbot** (works for any domain)
* **Recursive sitemap crawler** (auto-discovers all pages)
* **RAG search engine with ChromaDB vector embeddings**
* **Groq LLaMA-3.3-70B for ultra-fast answers**
* **Local doc ingestion support** (PDF, text, policies, KB docs)
* **Agentic routing using KNN classifier**
* **SEO-friendly scraping engine** (handles Brotli, redirects, cloudflare patterns)
* **Streamlit UI for live chatbot**

SEO Keywords: *generic AI chatbot, website scraping bot, sitemap crawling, RAG chatbot, Groq LLM chatbot, vector search AI, enterprise website assistant.*

---

## 🏗️ High-Level Architecture (Generic Workflow)

1. **Sitemap URL → Recursive Crawl**
2. **Extract Text → Clean HTML/XML → Normalize Content**
3. **Chunking → Embeddings → Chroma Vector Store**
4. **Classifier routes user intent**
5. **RAG retriever → Re-ranker → Grounded context**
6. **Groq LLM generates safe & accurate responses**

This flow works **for any website you plug in.**

---

## 🚀 Use Cases

* Convert your company website into an **AI FAQ bot**
* Build **customer support chatbots**
* Build **enterprise knowledge bots**
* Build **research assistants** for ANY public website

---

## 🧑‍💻 Creator

**Mohammad Azharuddin**
Creator of the Agentic RAG Website Chatbot

---
