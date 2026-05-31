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
Extract every job posting from the text above and return a JSON array.
Each object in the array must have EXACTLY these four keys — no others, no renaming:

  "role"        — the exact job title as written in the posting (e.g. "Senior Software Engineer - Backend")
  "experience"  — required years or level of experience
  "skills"      — list of required technical skills
  "description" — 1-2 sentence summary of the role

### OUTPUT RULES:
- Return ONLY a valid JSON array, even if there is just one job (wrap it in [ ])
- The key for the job title MUST be "role" — never "title", "job_title", or "position"
- Do NOT wrap output in ```json or ``` blocks
- Do NOT add any explanation before or after the JSON

Return JSON array now:
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
        word_limit = cfg.get("word_limit", 250)

        link_instruction = (
            f"Paste these exact portfolio URLs as a bullet list — do not paraphrase or rename them:\n{chr(10).join('- ' + u for u in links)}"
            if links else
            "Do not include any portfolio links or placeholders — no links are available for this submission."
        )

        base_prompt = """### JOB DESCRIPTION:
{job_description}

### ABOUT {company_name}:
{company_desc}

### YOUR IDENTITY:
You are {persona_name}, Business Development Executive at {company_name}.

### TASK:
Write a professional outreach email to the hiring manager for the role above.
The email should feel like a genuine business introduction, not a sales blast.

### EMAIL FORMAT — reproduce this structure exactly:

Hi [Hiring Manager / Hiring Team],

I am reaching out on behalf of {company_name}. We came across your opening for {job_role} and believe we can be a strong partner in helping you move fast on this need.

[BODY — 2 to 3 sentences: describe specifically how {company_name} addresses the core technical requirements of this role. Name the exact skills and tools from the job description. Emphasise that our consultants are senior-level, available immediately, and reduce hiring risk compared to a full-time search.]

Here are some relevant examples from our portfolio that align with this role:
{link_instruction}

We would love to explore how {company_name} can support your team. Would you be open to a quick 15-minute call this week?

Best regards,
{persona_name}
Business Development Executive
{company_name}

### HARD RULES:
- Keep the body section (between the intro and portfolio links) to 2–3 sentences only
- Use the exact job title from the job description — do not paraphrase it
- Total email length must be under {word_limit} words
- Tone: professional but warm — not stiff, not salesy
- Never use: "I hope this finds you well", "touch base", "synergy", "leverage", "utilize", "circle back", "game-changer"
- Do not invent portfolio links — use only the exact URLs provided above
- Do not add a subject line or any text outside the email
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
                job_role = (
                    job.get("role")
                    or job.get("title")
                    or job.get("job_title")
                    or job.get("position")
                    or ""
                ).strip()
                if not job_role:
                    logger.warning("Could not find role key in job dict: %s", list(job.keys()))
                    job_role = "the advertised role"

                res = chain_email.invoke({
                    "job_description": str(job),
                    "job_role": job_role,
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
