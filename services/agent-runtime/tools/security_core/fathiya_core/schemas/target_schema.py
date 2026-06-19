from pydantic import BaseModel, Field, field_validator
from typing import List, Literal


class FramedProblem(BaseModel):
    problem_type: Literal["exploratory", "analytical", "research", "execution", "mixed"]
    clarity_score: int = Field(ge=1, le=10)
    needs_research: bool
    needs_clarification: bool
    missing_information: List[str]
    handling_strategy: Literal[
        "clarify_first",
        "research_first",
        "direct_execution",
        "analysis_then_execution"
    ]
    sub_tasks: List[str]

    @field_validator("problem_type", mode="before")
    @classmethod
    def normalize_problem_type(cls, value: str) -> str:
        allowed = {"exploratory", "analytical", "research", "execution", "mixed"}
        if value in allowed:
            return value
        text = str(value).lower()
        if "research" in text or "guidance" in text:
            return "research"
        if "analysis" in text or "analyt" in text or "security" in text:
            return "analytical"
        if "execute" in text or "execution" in text:
            return "execution"
        return "mixed"

    @field_validator("handling_strategy", mode="before")
    @classmethod
    def normalize_handling_strategy(cls, value: str) -> str:
        allowed = {
            "clarify_first",
            "research_first",
            "direct_execution",
            "analysis_then_execution",
        }
        if value in allowed:
            return value
        text = str(value).lower()
        if "clar" in text:
            return "clarify_first"
        if "research" in text:
            return "research_first"
        if "direct" in text or "execute" in text:
            return "direct_execution"
        return "analysis_then_execution"
