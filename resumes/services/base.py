# File: resumes/services/base.py
# Author: Oluwatobiloba Light
from abc import ABC, abstractmethod


class BaseResumeGenerator(ABC):
    """Abstract Base Class for AI Resume Generators"""

    @abstractmethod
    def generate_resume_content(self, user_data: dict) -> str:
        pass

    @abstractmethod
    def parse_resume_content(self, content: str) -> dict:
        pass
