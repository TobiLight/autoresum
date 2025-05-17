# File: cover_letters/services/base.py
# Author: Oluwatobiloba Light
from abc import ABC, abstractmethod


class BaseCoverLetterGenerator(ABC):
    """Abstract Base Class for AI Cover Letter Generators"""

    @abstractmethod
    def generate_cover_letter_content(self, job_info: dict) -> str:
        pass

    @abstractmethod
    def parse_cover_letter_content(self, content: str) -> str:
        pass
