# 📧 AI-Powered Cold Email Generator

An AI-driven cold email generator built using **Groq LLM, LangChain, and Streamlit**.

This application allows users to input a company’s careers page URL. The system extracts job postings from the page and generates personalized cold emails tailored to the specific job role. The generated emails also include relevant portfolio links retrieved from a vector database based on the job description.

---

## 🚀 Project Overview

This project demonstrates how Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) can be combined to automate intelligent business outreach.

### 💡 Use Case Scenario

Imagine:

- **Databricks** is hiring for a software engineering role.
- Your company provides dedicated engineering talent and wants to pitch its services.
- Instead of manually drafting outreach emails, this tool:
  - Extracts the job description
  - Understands required skills using an LLM
  - Retrieves relevant portfolio projects
  - Generates a personalized cold email tailored to the role

This helps reduce manual effort while improving personalization and relevance.

---

## 🏗️ Architecture Overview

### High-Level Flow

1. User inputs a careers page URL.
2. The application scrapes and extracts job descriptions.
3. LangChain processes and structures the extracted content.
4. Relevant portfolio items are retrieved from a vector database using semantic similarity.
5. The LLM generates a customized cold email.
6. Streamlit displays the generated output.
<img width="931" height="569" alt="Cold_Email_generator_HLD drawio" src="https://github.com/user-attachments/assets/4e487976-315c-4ab2-a0c9-cca6d9c21e22" />

---

## 🛠️ Tech Stack

- **LLM Provider:** Groq (using a different model version than the reference implementation)
- **Framework:** LangChain
- **Frontend:** Streamlit
- **Vector Store:** ChromaDB (or your configured vector database)
- **Language:** Python

---

## 📦 Features

- 🔎 Extracts job listings from a careers page URL
- 🧠 Understands job requirements using LLM reasoning
- 📚 Retrieves relevant portfolio items via vector similarity search
- ✉️ Generates personalized cold emails
- ⚡ Fast inference powered by Groq

---

## 📂 Project Structure

```
├── app/
│   ├── main.py
│   ├── chains/
│   ├── utils/
│   ├── vector_store/
│   └── .env
├── requirements.txt
└── README.md
```
---

## 🔧 Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone <your-repository-url>
cd <your-project-folder>
```

---

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3️⃣ Configure Environment Variables

Create a `.env` file inside the `app/` directory and add:

```
GROQ_API_KEY=your_groq_api_key_here
```

You can generate your API key from:  
https://console.groq.com/keys

---

### 4️⃣ Run the Application

```bash
streamlit run app/main.py
```

The app will open in your default browser.
