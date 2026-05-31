# AI-Powered Cold Email Generator

An AI-driven cold email generator built using **Groq LLM (Llama 3.3 70B), LangChain, and Streamlit**.

Input a job posting URL and the app generates a personalized cold email pitching **Nexus AI Consulting's** services, backed by relevant portfolio links pulled from a ChromaDB vector store.

---

## Architecture

<img width="931" height="569" alt="Cold_Email_generator_HLD drawio" src="https://github.com/user-attachments/assets/4e487976-315c-4ab2-a0c9-cca6d9c21e22" />

```
Job Posting URL
      │
      ▼
 URL Validation ──── invalid? ──► show error
      │
      ▼
 Scrape + Clean + Truncate (24k char limit)
      │
      ▼
 Groq LLM: Extract Job JSON
 { role, skills, experience, description }
      │
      ├─────────────────────────────┐
      ▼                             ▼
 ChromaDB Semantic Search     Job JSON
 (skills → portfolio links)        │
      │                             │
      └──────────────┬──────────────┘
                     ▼
            Groq LLM: Generate Email
            (persona + job + links)
                     │
                     ▼
            EmailEvaluator (score 0–1)
            word count · CTA · tone
            relevance · portfolio link
                     │
          ┌──────────┴──────────┐
       score ≥ 0.7           score < 0.7
          │                 & retries left
          │                      │
          │              inject feedback +
          │              raise temperature
          │                      │
          │                      └──► retry email
          ▼
   Display Email + Quality Scores
```

## How It Works

1. User enters a job posting URL
2. Page is scraped, cleaned, and truncated to fit within LLM token limits
3. Groq LLM extracts structured job data — role, skills, experience, description
4. ChromaDB semantic search retrieves the most relevant portfolio links for the job's skills
5. LLM generates a cold email with an **evaluation + retry loop** — emails are scored on word count, CTA presence, tone, skill relevance, and portfolio link inclusion; if the score is below 0.7 the email is regenerated (up to 3 attempts) with feedback injected into the prompt
6. Final email is displayed with per-criterion quality scores

---

## Features

- Evaluation + retry loop with automatic feedback injection
- Configurable persona name, company name, description, and word limit via sidebar
- Per-job expandable UI when a page contains multiple postings
- Copy-to-clipboard and .txt download for every email
- Email history panel (persists across the session)
- Portfolio Manager page — add, delete, and force-reload portfolio entries without touching files
- URL validation and accessibility check before scraping
- Structured JSON logging to `app/logs/cold_email.log`
- Exponential backoff on Groq API rate limit / timeout errors

---

## Project Structure

```
app/
  main.py                  — Streamlit UI, pipeline orchestration
  chains.py                — LLM calls: job extraction + email generation with eval loop
  portfolio.py             — ChromaDB wrapper; hash-based auto-reload when CSV changes
  evaluator.py             — EmailEvaluator: scores word count, CTA, tone, relevance, portfolio link
  retry.py                 — @with_retry decorator with exponential backoff
  validators.py            — URL format and accessibility checks
  logger.py                — JSON structured logger with rotating file handler
  utils.py                 — clean_text + truncate_text helpers
  components.py            — Streamlit copy button and download button
  pages/
    portfolio_manager.py   — Add/delete portfolio entries, force-reload vector store
  resources/
    my_portfolio.csv       — Portfolio data: Techstack and Links columns
requirements.txt
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create `app/.env` (copy from `app/.env.example`):

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a key at: https://console.groq.com/keys

### 3. Run the app

```bash
streamlit run app/main.py
```

---

## Portfolio Management

Edit `app/resources/my_portfolio.csv` — two columns: `Techstack` (comma-separated skills) and `Links` (portfolio URL). The vector store auto-reloads when the file changes (detected via MD5 hash). To force a manual reload, use the **Portfolio Manager** page in the app sidebar.

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Groq — Llama 3.3 70B Versatile |
| Orchestration | LangChain |
| Vector Store | ChromaDB (persistent) |
| Frontend | Streamlit |
| Language | Python 3.10+ |
