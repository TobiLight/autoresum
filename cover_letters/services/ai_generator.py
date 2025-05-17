# File: cover_letters/services/ai_generator.py
# Author: Oluwatobiloba Light
import json

from openai import OpenAI, OpenAIError

# from cover_letters.models import CoverLetter
from cover_letters.services.base import BaseCoverLetterGenerator


class OpenAICoverLetterGenerator(BaseCoverLetterGenerator):
    """AI Cover Letter Generator using OpenAI ChatGPT."""

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

    def parse_cover_letter_content(self, content: str) -> dict:
        """Parse the AI response into structured data."""
        try:
            # Add a system message to format response as JSON
            client = self.init_openai()
            parsing_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a JSON formatter. Convert the given cover letter content/text into a structured JSON format with name of the company_name as string and job title as string, the cover_letter as a string, name as string, email as string and phone as string.",
                    },
                    {"role": "user", "content": content},
                ],
            )

            parsed_data = json.loads(
                parsing_response.choices[0].message.content.strip()
            )

            return parsed_data
        except (json.JSONDecodeError, OpenAIError) as e:
            raise ValueError(f"Failed to parse AI response: {str(e)}")

    def generate_cover_letter_content(self, data: dict):
        """Generates a cover letter using OpenAI ChatGPT."""

        system_prompt = """
        You are a professional career consultant and an expert in writing ATS-friendly cover letters.
        Your job is to generate a well-structured personalized cover letter for a user based on their input.

        ### User Input:
            # - Full name (if provided/applicable): {full_name}
            # - Email address (if applicable): {email}
            # - Phone Number (if provided/applicable): {phone_number}
            # - Company Name: {company_name}
            # - Job Title: {job_title}
            # - Job Description: {job_description}
            # - Hiring Manager (if provided/applicable): {hiring_manager}
            # - Reason for applying: {reason_for_applying}

        ### Instructions:
        - Ensure the cover letter is **ATS-optimized** by including **relevant keywords**.
        - If writing a cover letter, personalize it to the **job description**.
        - Replace [Your Name] with the **user's full name**.
        - Keep it **under one page**.
        - Format the response using **Markdown**.

        Now, generate the best cover letter for this candidate.
        """.format(
            full_name=data.get("full_name", None),
            email=data.get("email", None),
            phone_number=data.get("phone_number", None),
            company_name=data.get("company_name", ""),
            job_title=data.get("job_title", ""),
            job_description=data.get("job_description", ""),
            hiring_manager=data.get("hiring_manager", None),
            reason_for_applying=data.get("reason_for_applying", None),
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
