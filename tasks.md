# 🚀 Project Breakdown: Sovereign Multi-Agent Intelligence System (Faveod)

## 📌 Project Overview
Build a **100% sovereign, self-hosted Multi-Agent AI system** using **Chinese open-source AI models** (DeepSeek, Qwen, BAAI) to automate competitive intelligence across Africa and the Middle East for Faveod's International Business Development Director.

---

## 🛠️ PHASE 1: Sovereign Infrastructure & Environment Setup
*Goal: Set up the local/sovereign server and host all open-source models without relying on foreign APIs (OpenAI, Anthropic, etc.).*

- [ ] **Task 1.1: Hardware & OS Provisioning**
  - Secure GPU server infrastructure (minimum 1x–2x NVIDIA A100 or H100 with 80GB VRAM, or equivalent cloud instance).
  - Install Linux environment (Ubuntu 22.04 LTS), CUDA drivers, and Docker Container Toolkit.

- [ ] **Task 1.2: Model Serving & Vector Database Deployment**
  - Install **vLLM** or **Ollama** as the local model inference server.
  - Download and deploy the core Chinese open-source models:
    - `DeepSeek-R1` or `DeepSeek-R1-Distill-Qwen-32B` *(Reasoning model for complex criteria analysis)*.
    - `Qwen-2.5-72B-Instruct` or `Qwen-2.5-32B-Instruct` *(Data extraction & multilingual processing)*.
    - `BGE-M3` *(Multilingual vector embedding model by BAAI)*.
    - `BGE-Reranker-v2-m3` *(Re-ranking model for precise document context)*.
  - Deploy a vector database (**Qdrant** or **Milvus**) inside Docker for storing document chunks.

- [ ] **Task 1.3: Agent Orchestration Layer Setup**
  - Install and configure **Dify** (open-source agent framework) or **LangGraph**.
  - Connect Dify/LangGraph to local model endpoints via vLLM API wrappers.

---

## 🎯 PHASE 2: Agent 1 — "Tender Hunter" (Public Contracts Finder)
*Goal: Automatically find, download, analyze, and score international software tenders funded by World Bank, AfDB, EBRD, IMF.*

- [x] **Task 2.1: Data Ingestion & Scraping Engine**
  - Build web scrapers (using Python, Playwright/Puppeteer) targeted at tender portals:
    - World Bank (DevBusiness / Projects API).
    - African Development Bank (AfDB) procurement portal.
    - European Bank for Reconstruction and Development (EBRD).
    - International Monetary Fund (IMF) & regional government portals.
  - Implement a rotating residential proxy to bypass geo-blocking/bot protection.

- [x] **Task 2.2: Document Parsing & RAG Pipeline**
  - Integrate **PyMuPDF** / **Unstructured** to extract text from dense tender PDFs/DOCX.
  - Implement text chunking and vector index creation using `BGE-M3` in Qdrant/Milvus.
  - Implement `BGE-Reranker-v2-m3` to fetch relevant legal/technical contract sections.

- [x] **Task 2.3: Reasoning Engine (Faveod Criteria Filter)**
  - Develop the system prompt for `DeepSeek-R1` to evaluate 4 mandatory criteria:
    1. **Source Code / IP Ownership:** Does the client retain 100% IP rights?
    2. **High Security / Quality:** Are there local hosting or strict security requirements?
    3. **Compressed Timelines:** Are delivery deadlines tight/strictly enforced?
    4. **Green-IT:** Are there digital sobriety or eco-design requirements?
  - Add strict anti-hallucination guardrails: Output `"IP_Status": "Unspecified - Manual review required"` if similarity score is below 0.75.

- [x] **Task 2.4: Agent Output Generation**
  - Output structured JSON with a calculated **Faveod Fit Score (0–100%)** and exact source document citations.

---

## 🤝 PHASE 3: Agent 2 — "Partner Scout" (Local ESN Discovery)
*Goal: Identify local IT services companies (ESNs/Integrators) in target countries to act as local implementation or support partners.*

- [x] **Task 3.1: Data Collection & Search Setup**
  - Deploy a self-hosted **SearXNG** instance (privacy-focused meta-search engine).
  - Configure automated search queries per target country (e.g., Morocco, Senegal, UAE, Saudi Arabia, Egypt) for terms like `"Software Engineering"`, `"Systems Integrator"`, `"IT Services"`.

- [x] **Task 3.2: ESN Website & Portfolio Analyzer**
  - Build a web scraper to fetch "Case Studies", "References", and "Partners" pages of discovered IT companies.
  - Use `Qwen-2.5` to analyze company profiles:
    - Identify client references and project scale.
    - Detect technology focus (Custom development vs. proprietary low-code/SAP/Oracle resellers).

- [x] **Task 3.3: Partner Qualification & Database Engine**
  - Filter out direct competitors (exclusive low-code/off-the-shelf software resellers).
  - Retain IT service providers capable of custom software maintenance and local support.
  - Format output into a structured profile: Company Name, Country, Size, Client References, Contact URL, and Faveod Affinity Score.

---

## 📅 PHASE 4: Agent 3 — "Event Mapper & Lead Profiler"
*Goal: Map regional IT conferences, extract attendee/speaker lists, and profile high-value prospects (CIOs, CTOs, Ministers).*

- [x] **Task 4.1: Event Scraper & Monitoring Engine**
  - Build automated monitors on event platforms (10times, Eventbrite, Luma) and regional IT news sites (TechCabal, ArabianBusiness).
  - Track keywords: `"IT Summit"`, `"Digital Transformation Africa"`, `"Cybersecurity Conference Dubai"`.

- [x] **Task 4.2: Participant & Speaker Extraction**
  - Scrape public speaker panels and declared attendee lists from event websites.
  - Feed raw text into `Qwen-2.5` to perform Named Entity Recognition (NER) and extract Person Names, Job Titles, and Company Names.

- [x] **Task 4.3: Lead Enrichment & Prospect Cards**
  - Cross-reference extracted names to identify decision-makers (CIOs, CTOs, IT Directors, Digital Transformation Ministers).
  - Use `Qwen-2.5` to generate a summary of each lead's key IT challenges based on their recent panel topics or public statements.

---

## 📊 PHASE 5: User Interface, Integration & Testing
*Goal: Connect all 3 agents into a unified dashboard and push outputs to Faveod's team.*

- [ ] **Task 5.1: Dashboard & Notification Workflow**
  - Build a user dashboard in **Dify** or a web UI (Streamlit/Next.js) displaying:
    - Real-time Tender Feed with match scores.
    - Directory of Qualified Local Partners.
    - Interactive IT Event Calendar with prioritized prospect lists.
  - Setup automated alerts (Slack, Teams, or Email digest) when a high-match tender (>80% score) is detected.

- [ ] **Task 5.2: End-to-End Validation & Multilingual Testing**
  - Test Agent 1 against real Arabic, French, and English tender documents.
  - Validate anti-hallucination rules (verify that missing criteria are marked correctly rather than guessed).
  - Fine-tune prompt parameters (temperature, max tokens, system prompts).