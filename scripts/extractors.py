from pydantic import BaseModel
from typing import List


class Candidates(BaseModel):
    topical: list[str] = []
    geographic: list[str] = []
    personal_name: list[str] = []
    corporate_name: list[str] = []
    events: list[str] = []
    uniform_title: list[str] = []
    chronological: list[str] = []
    form_genre: list[str] = []

    def __str__(self) -> str:
        parts: list[str] = []
        for facet, values in self.model_dump().items():
            for term in values:
                parts.append(f"{facet}: {term}")
        return " | ".join(sorted(parts))