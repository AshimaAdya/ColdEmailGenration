import datetime
import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
from dotenv import load_dotenv

from chains import Chain
from portfolio import Portfolio
from utils import clean_text, truncate_text
from validators import validate_url, check_url_accessible
from components import copy_button, download_button
from logger import get_logger, Timer

load_dotenv()
logger = get_logger(__name__)


def _render_sidebar() -> dict:
    with st.sidebar:
        st.header("Settings")
        persona_name = st.text_input("Your Name", value=st.session_state.get("persona_name", "Ashima"))
        company_name = st.text_input("Company Name", value=st.session_state.get("company_name", "Nexus AI Consulting"))
        company_desc = st.text_area(
            "Company Description",
            value=st.session_state.get(
                "company_desc",
                "Nexus AI Consulting is an AI & Software Consulting firm that helps companies "
                "build and integrate backend systems, data pipelines, and AI automation tools. "
                "We specialize in reducing engineering hiring risk by providing senior-level "
                "consultants who can contribute from day one.",
            ),
            height=120,
        )
        word_limit = st.slider("Email Word Limit", min_value=80, max_value=300, value=150, step=10)
        max_retries = st.slider("Max Retry Attempts", min_value=1, max_value=5, value=3)

        st.session_state["persona_name"] = persona_name
        st.session_state["company_name"] = company_name
        st.session_state["company_desc"] = company_desc

    return {
        "persona_name": persona_name,
        "company_name": company_name,
        "company_desc": company_desc,
        "word_limit": word_limit,
        "max_retries": max_retries,
    }


def _render_quality_scores(eval_result, max_retries: int):
    scores = eval_result.scores
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Overall", f"{eval_result.overall_score:.0%}", delta="Pass" if eval_result.passed else "Fail")
    c2.metric("Word Count", f"{scores['word_count']:.0%}")
    c3.metric("CTA", "Yes" if scores['has_cta'] else "No")
    c4.metric("Tone", f"{scores['tone']:.0%}")
    c5.metric("Relevance", f"{scores['relevance']:.0%}")
    c6.metric("Portfolio Link", "Yes" if scores.get('has_portfolio_link') else "No")

    if not eval_result.passed:
        st.warning(f"Best available email shown — quality threshold not met after {max_retries} attempt(s). {eval_result.feedback}")


def create_streamlit_app(llm: Chain, portfolio: Portfolio):
    st.title("Cold Mail Generator")

    if "email_history" not in st.session_state:
        st.session_state["email_history"] = []

    config = _render_sidebar()

    url_input = st.text_input("Enter a Job Posting URL:")
    submit_button = st.button("Generate Email", type="primary")

    if submit_button:
        # Validate URL before doing any work
        valid, err = validate_url(url_input)
        if not valid:
            st.error(err)
            st.stop()

        accessible, err = check_url_accessible(url_input)
        if not accessible:
            st.error(err)
            st.stop()

        try:
            with st.status("Processing...", expanded=True) as status:
                status.write("Fetching and cleaning the job page...")
                with Timer(logger, "url_load", url=url_input):
                    loader = WebBaseLoader([url_input])
                    data = truncate_text(clean_text(loader.load().pop().page_content))

                status.write("Loading portfolio vector store...")
                portfolio.load_portfolio()

                status.write("Extracting job postings with LLM...")
                jobs = llm.extract_jobs(data)
                logger.info("Extracted %d job(s)", len(jobs), extra={"step": "extract_jobs", "job_count": len(jobs)})

                if len(jobs) > 1:
                    status.write(f"Found {len(jobs)} job postings. Generating emails...")
                else:
                    status.write("Generating cold email...")

                results = []
                for job in jobs:
                    skills = job.get("skills", [])
                    links = portfolio.query_links(skills)
                    if not links:
                        logger.warning("No portfolio links returned for skills: %s", skills)
                        status.write("Warning: no matching portfolio links found — check Portfolio Manager.")
                    email, eval_result = llm.write_email(job, links, config=config, max_retries=config["max_retries"])
                    results.append((job, email, eval_result))

                status.update(label=f"Done! Generated {len(results)} email(s).", state="complete")

            if len(results) > 1:
                st.info(f"Found {len(results)} job postings on this page.")

            for i, (job, email, eval_result) in enumerate(results):
                role = job.get("role", f"Job {i + 1}")
                with st.expander(f"Job {i + 1}: {role}", expanded=(i == 0)):
                    st.code(email, language="markdown")

                    col_copy, col_dl, _ = st.columns([1, 1, 4])
                    with col_copy:
                        copy_button(email)
                    with col_dl:
                        download_button(email, role)

                    st.divider()
                    st.caption("Quality Scores")
                    _render_quality_scores(eval_result, config["max_retries"])

                # Save to session history
                st.session_state["email_history"].append({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "url": url_input,
                    "role": role,
                    "email": email,
                    "score": eval_result.overall_score,
                })

        except Exception as e:
            logger.exception("Pipeline failed for URL: %s", url_input)
            st.error(f"An error occurred: {e}")

    # Email history panel
    history = st.session_state.get("email_history", [])
    if history:
        st.divider()
        with st.expander(f"Email History — {len(history)} email(s) this session"):
            for item in reversed(history):
                st.caption(f"{item['timestamp']} | {item['role']} | Score: {item['score']:.0%} | {item['url']}")
                st.code(item["email"], language="markdown")
                st.markdown("---")


if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Cold Email Generator", page_icon="📧")
    chain = Chain()
    portfolio = Portfolio()
    create_streamlit_app(chain, portfolio)
