# Adaptive Job Recommender System

This project implements a content-based adaptive job recommender system powered by large language models (LLMs) and embeddings. It intelligently matches users to job listings by comparing extracted skills and dynamically adapting to user choices. All language model components, prompts, and pipelines are structured using **LangChain** for modular and scalable orchestration.

---

## 🚀 Features

- Extracts hard and soft skills from job listings and user resumes using LLMs
- Computes influence scores for each skill to quantify importance
- Creates semantic embeddings for jobs and users using high-performance models
- Matches users to jobs using cosine similarity
- Continuously updates user profiles based on feedback and selections
- Built using **LangChain** for modular LLM workflows
- **Interactive UI** built with **Streamlit**
- **Backend models served via Flask RESTful APIs**

---

## 🧠 Core Components

### 1. **Data Sourcing**

- **Source**: [Bright Data – Glassdoor Job Listings](https://brightdata.com/products/datasets/glassdoor)
- > 3,000 diverse job listings collected, including:
  - Software Developers
  - ML Engineers
  - Data Scientists
  - Consultants
  - Financial Analysts
  - Engineers (various fields)
  - Medical Professionals
  - Sales & Marketing roles

- The data is cleaned and structured into a format suitable for LLM ingestion and stored in **MongoDB**.

---

### 2. **Job Modelling**

- **LLM Used**: `llama3:8b` via Ollama (Open-source model by Meta)
- Orchestrated using **LangChain** with:
  - Prompt templates
  - Output parsers
  - Role-based prompt chaining
- Extracted:
  - Hard skills (e.g., Python, SQL)
  - Soft skills (e.g., communication, leadership)
  - **Influence Scores**: Weights showing importance of each skill

---

### 3. **User Modelling**

- **LLM Used**: `llama3:8b` via Ollama
- Resume parsing, skill extraction, and influence scoring are handled through **LangChain** components
- Dynamically generates structured skill profiles from raw text using prompt chains

---

### 4. **Embeddings Creation**

- **Embedding Model**: `mxbai-embed-large:latest` (by Mixedbread AI)
- Embeddings generated using **LangChain’s embedding wrappers**
- Converts job and user text to vector representations stored in **MongoDB vector store**

---

### 5. **Adaptive Matching Model**

- **Approach**: Content-Based Filtering using **cosine similarity**
- Recommendation tiers:
  - 60%: Highly matching jobs (similarity > 90%)
  - 30%: Moderately matching (50%-90%)
  - 10%: Slightly matching (10%-50%)

- **Adaptive Logic**:
  - If user selects a weakly matching job:
    - A LangChain chain is triggered
    - The user profile is updated via LLM
    - Influence scores are revised
    - New embeddings are generated and used for fresh recommendations

---

### 6. **Frontend & Backend Integration**

- **Frontend**: Streamlit-based interactive UI
  - Resume upload
  - Visual display of recommended jobs
  - Real-time feedback and skill visualization
- **Backend**: Flask RESTful API
  - Skill extraction, embedding, and recommendation services are served as endpoints
  - Frontend communicates with backend via HTTP

---

## 🛠️ Tech Stack

| Component         | Technology                          |
|-------------------|--------------------------------------|
| LLMs              | `llama3:8b` via Ollama               |
| Embeddings        | `mxbai-embed-large`                 |
| Orchestration     | **LangChain** (prompt + chain logic)|
| Vector Storage    | MongoDB with vector indexing         |
| Backend API       | Flask RESTful API                    |
| Frontend UI       | Streamlit                            |
| Data Source       | Bright Data Glassdoor Dataset        |

---


## 📄 License

This project is licensed under the MIT License. See `LICENSE` for more details.

---

## 🙌 Acknowledgements

- [Ollama](https://ollama.com/search)
- [Meta AI – LLaMA 3](https://ai.meta.com/llama/)
- [Mixedbread AI – Embedding Models](https://huggingface.co/mixedbread-ai)
- [LangChain Framework](https://www.langchain.com/)
- [Bright Data Datasets](https://brightdata.com/products/datasets)
- [Streamlit](https://streamlit.io/)
- [Flask](https://flask.palletsprojects.com/)

---
