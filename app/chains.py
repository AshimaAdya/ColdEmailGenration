import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv

load_dotenv()

class Chain:
    def __init__(self):
        self.llm=ChatGroq(model="llama-3.3-70b-versatile",groq_api_key=os.getenv("GROQ_API_KEY"),temperature=0.0)

    def extract_jobs(self,cleaned_text):
        prompt_extract = PromptTemplate.from_template("""
        ### SCRAPED TEXT FROM WEBSITE:
        {page_data}

        ### INSTRUCTION:
        Extract the job postings and return them in JSON format with keys:
        'role','experience','skills','description'.

        ### OUTPUT RULES (VERY IMPORTANT):
        - Return ONLY beautify JSON
        - Do NOT wrap the output in ```json or ``` 

        Return JSON now:
        """)

        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={'page_data': cleaned_text})
        try:
            json_parser = JsonOutputParser()
            res = json_parser.parse(res.content)
        except OutputParserException:
            raise OutputParserException("Context too big. Unable to parse jobs.")
        return res if isinstance(res, list) else [res]

    def write_email(self,job,links):
        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
    {job_description}

    ### ABOUT APK CONSULTING:
    APK Consulting is an AI & Software Consulting firm that helps companies 
    build and integrate backend systems, data pipelines, and AI automation tools.
    We specialize in reducing engineering hiring risk by providing senior-level 
    consultants who can contribute from day one.

    ### INSTRUCTION:
    You are Ashima, a Business Development Executive at APK Consulting.
    
    Write a cold email to the hiring manager for the job described above.
    The goal of the email is to pitch APK Consulting's services as an 
    alternative or supplement to hiring full-time.
    
    The email must:
    - Open with one specific observation about the role or company (not a generic opener)
    - Explain in 2-3 sentences exactly how APK solves the pain this role is trying to solve
    - Include only the most relevant portfolio links from this list, 
      matching them specifically to skills mentioned in the job description: {link_list}
    - End with one clear, low-friction call to action (suggest a 15-min call)
    - Be under 150 words total
    - Sound human, direct, and confident — not salesy
    
    Do not use phrases like "I hope this email finds you well" or "I wanted to reach out".
    Do not provide a preamble.
    
    ### EMAIL:
    """
        )

        chain_email = prompt_email | self.llm
        res = chain_email.invoke({"job_description": str(job), "link_list": links})
        return res.content

    # if __name__ == "__main__":
    #     print(os.getenv("GROQ_API_KEY"))