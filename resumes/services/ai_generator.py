# File: resumes/services/ai_generator.py
# Author: Oluwatobiloba Light
import json

from openai import OpenAI, OpenAIError

# from resumes.models import Resume
from resumes.services.base import BaseResumeGenerator

# from users.models import User


class OpenAIResumeGenerator(BaseResumeGenerator):
    """AI Resume Generator using OpenAI ChatGPT."""

    def __init__(self, api_key: str, organization_id: str):
        self.api_key = api_key
        self.organization_id = organization_id
        self.check_api_key()

    def check_api_key(self):
        """Check if the API key is provided."""
        if not self.api_key:
            raise ValueError("API key is required.")

    def init_openai(self) -> OpenAI:
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, organization=self.organization_id)

    def parse_resume_content(self, content: str) -> dict:
        """Parse the AI response into structured data."""
        try:
            # Add a system message to format response as JSON
            client = self.init_openai()
            parsing_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a JSON formatter. Convert the given resume text into a structured JSON format with full_name as a string (split the name or full_name. for e.g. 'John Doe' -> 'John' 'Doe'), phone_number as a string, work_experience as array of objects (company, position, duration, description), education as array of objects (institution, degree, year), skills as array of strings, and resume_summary as string, certifications as an array of strings, languages as an array of strings",
                    },
                    {"role": "user", "content": content},
                ],
            )

            parsed_data = json.loads(
                parsing_response.choices[0].message.content
            )
            return parsed_data
        except (json.JSONDecodeError, OpenAIError) as e:
            raise ValueError(f"Failed to parse AI response: {str(e)}")
        except Exception:
            raise ValueError("Failed to parse AI Response")

    def generate_resume_content(self, user_data: dict) -> str:
        """Generates a resume using OpenAI ChatGPT."""
        # This is just a sample.
        system_prompt = """
You are a professional career consultant and an expert in writing ATS-friendly resumes and cover letters.
Your job is to generate a well-structured {7} for a user based on their input.

### User Input:
- Full name: {0}
- Phone Number: {1}
- Languages: {2}
- Work Experience: {3}
- Skills: {4}
- Education: {5}
- Certifications: {6}

### Instructions:
- Use **clear bullet points** for resumes. It must contain these fields [Full name, Job Title, Work experience, skills, education, certifications, summary, languages, phone number]
- Write in a **professional, concise, and impactful tone**.
- Ensure the resume is **ATS-optimized** by including **relevant keywords**.
- If writing a cover letter, personalize it to the **job description**.
- Keep it **under two pages max**.
- Format the response using **Markdown**.

Provide a structured ATS-optimized resume. Now, generate the best resume for this candidate.
""".format(
            user_data.get("first_name", "John")
            + " "
            + user_data.get("last_name", "Doe"),
            user_data.get("phone_number"),
            user_data.get("languages"),
            user_data.get("work_experience"),
            user_data.get("skills"),
            user_data.get("education"),
            user_data.get("certifications"),
            "PDF",
        )

        try:
            client = self.init_openai()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    # {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            return content

        except OpenAIError as e:
            raise ValueError(f"OpenAI API error: {str(e)}")
