from sqlalchemy import String, Double, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class ReviewRound(Base):
    __tablename__ = 'review_rounds'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'), index=True)
    sequence: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    initiator_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Double)
    closed_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    # 仲裁席位；两票分歧时由未参与过本轮的管理员补位
    arbiter_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    decided_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    # 退回后重送生成新轮次；parent_id 串起同一结论的历次送审
    parent_id: Mapped[int | None] = mapped_column(ForeignKey('review_rounds.id'), nullable=True)
    __table_args__ = (UniqueConstraint('job_id', 'sequence', name='uq_review_job_sequence'),)
class ReviewVote(Base):
    __tablename__ = 'review_votes'
    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey('review_rounds.id'), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    seat: Mapped[int] = mapped_column(default=1)  # 1/2 双盲席位，3 仲裁席位
    decision: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[float] = mapped_column(Double)
    # 轮次关闭后才到达的意见：仍归原编号留痕，但不再参与计票
    late: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint('round_id', 'reviewer_id', name='uq_review_vote_reviewer'),)
