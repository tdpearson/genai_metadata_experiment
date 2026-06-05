from pydantic import BaseModel
from typing import List


class SubjectHeadings(BaseModel):
    heading: str | None = None
    fast_uri: str | None = None
    marc_tag: str | None = None
    facet: str | None = None


class OclcFast(BaseModel):
    item_title: str | None = None
    subject_headings: List[SubjectHeadings]
    marc_encoding: str | None = None

    def __str__(self) -> str:
        return " | ".join(sorted([f"{item.facet}: {item.heading}" for item in self.subject_headings]))


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