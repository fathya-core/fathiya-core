from pydantic import BaseModel, Field
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