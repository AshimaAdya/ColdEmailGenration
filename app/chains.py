import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv

from evaluator import EmailEvaluator
from retry import with_retry
from logger import get_logger, Timer

load_dotenv()

logger = get_logger(__name__)
_evaluator = EmailEvaluator()


class Chain:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0,
        )

    @with_retry(max_attempts=3, base_delay=1.0)
    def extract_jobs(self, cleaned_text: str) -> list:
        prompt_extract = PromptTemplate.from_template("""
### SCRAPED TEXT FROM WEBSITE:
{page_data}

### INSTRUCTION:
Extract the job postings and return them in JSON format with keys:
'role','experience','skills','description'.

### OUTPUT RULES (VERY IMPORTANT):
- Return ONLY valid JSON
- Do NOT wrap the output in ```json or ```

Return JSON now:
""")
        with Timer(logger, "extract_jobs"):
            chain_extract = prompt_extract | self.llm
            res = chain_extract.invoke(input={'page_data': cleaned_text})
        try:
            json_parser = JsonOutputParser()
            parsed = json_parser.parse(res.content)
        except OutputParserException:
            raise OutputParserException("Context too big. Unable to parse jobs.")
        return parsed if isinstance(parsed, list) else [parsed]

    def write_email(self, job: dict, links: list, config: dict = None, max_retries: int = 3):
        cfg = config or {}
        persona_name = cfg.get("persona_name", "Ashima")
        company_name = cfg.get("company_name", "Nexus AI Consulting")
        company_desc = cfg.get(
            "company_desc",
            "Nexus AI Consulting is an AI & Software Consulting firm that helps companies "
            "build and integrate backend systems, data pipelines, and AI automation tools. "
            "We specialize in reducing engineering hiring risk by providing senior-level "
            "consultants who can contribute from day one.",
        )
        word_limit = cfg.get("word_limit", 150)

        link_instruction = (
            f"You MUST include these exact portfolio URLs verbatim in the email body "
            f"(copy-paste them, do not paraphrase or use placeholders): {links}"
            if links else
            "Do not include any portfolio links or placeholders — no links are available."
        )

        base_prompt = """### JOB DESCRIPTION:
{job_description}

### ABOUT {company_name}:
{company_desc}

### INSTRUCTION:
You are {persona_name}, a Business Development Executive at {company_name}.

Write a cold email to the hiring manager for the job described above.
The goal of the email is to pitch {company_name}'s services as an alternative or supplement to hiring full-time.

The email must:
- Open with one specific observation about the role or company (not a generic opener)
- Explain in 2-3 sentences exactly how {company_name} solves the pain this role is trying to solve
- {link_instruction}
- End with one clear, low-friction call to action (suggest a 15-min call)
- Be under {word_limit} words total
- Sound human, direct, and confident — not salesy

Do not use phrases like "I hope this email finds you well" or "I wanted to reach out".
Do not invent or paraphrase portfolio links — use only the exact URLs provided above.
Do not provide a preamble.
{feedback_section}
### EMAIL:
"""

        best_email = ""
        best_result = None

        for attempt in range(max_retries):
            temperature = min(0.3 + 0.1 * attempt, 0.7)
            llm = self.llm.bind(temperature=temperature)

            feedback_section = ""
            if best_result is not None and not best_result.passed:
                feedback_section = (
                    f"\nPREVIOUS ATTEMPT FEEDBACK: {best_result.feedback} "
                    "Please address these issues in your next attempt.\n"
                )

            prompt_email = PromptTemplate.from_template(base_prompt)
            chain_email = prompt_email | llm

            with Timer(logger, "write_email", attempt=attempt + 1):
                res = chain_email.invoke({
                    "job_description": str(job),
                    "company_name": company_name,
                    "company_desc": company_desc,
                    "persona_name": persona_name,
                    "link_instruction": link_instruction,
                    "word_limit": word_limit,
                    "feedback_section": feedback_section,
                })

            email = res.content
            result = _evaluator.evaluate(email, job, links)
            logger.info(
                "Email evaluation attempt %d: score=%.2f passed=%s",
                attempt + 1, result.overall_score, result.passed,
                extra={"step": "evaluate_email"},
            )

            if best_result is None or result.overall_score > best_result.overall_score:
                best_email = email
                best_result = result

            if result.passed:
                break

        return best_email, best_result
