from typing import Literal

from pydantic import BaseModel, Field


Driver = Literal[
    "Brand Perception",
    "User Experience",
    "Responsible Business Practices",
]

SubDriver = Literal[
    "Thought Leadership",
    "Product Strategy",
    "Brand Visibility & Marketing",
    "Product & Service Quality",
    "Customer Support & Complaint Resolution",
    "Digital & Omnichannel Experience",
    "Regulatory Compliance & Ethical Governance",
    "Social Impact & Community (CSR)",
]

Sentiment = Literal["Positive", "Neutral", "Negative"]


class MentionClassification(BaseModel):
    is_relevant: bool = Field(
        description="Whether the mention belongs in the BFSI reputation analysis."
    )
    reputation_driver: Driver
    sub_driver: SubDriver
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(max_length=300)


class ClassificationResult(MentionClassification):
    matched_terms: list[str] = Field(default_factory=list)
    classification_source: str = "rule"
