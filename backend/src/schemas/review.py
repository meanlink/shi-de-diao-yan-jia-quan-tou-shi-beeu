from pydantic import BaseModel, Field
class VoteInput(BaseModel):
    decision: str = Field(description='approve 或 reject')
    reason: str = Field(min_length=4, max_length=1000)
class LateVoteInput(VoteInput):
    reviewer_id: int | None = None
class ArbitrateInput(VoteInput):
    pass
