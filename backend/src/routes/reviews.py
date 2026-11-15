from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Job, ReviewRound, ReviewVote, User
from src.schemas.review import VoteInput, LateVoteInput, ArbitrateInput
from src.middlewares.auth import current_user
from src.services import reviews
from src.services.audit import record
from src.utils.review_serialization import round_dict
router = APIRouter(prefix='/reviews')
def _get_job(db, job_id):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, '分析任务不存在')
    return job
def _get_round(db, round_id):
    rnd = db.get(ReviewRound, round_id)
    if not rnd:
        raise HTTPException(404, '送审编号不存在')
    return rnd
@router.get('/jobs/{job_id}/rounds')
def job_rounds(job_id: int, db=Depends(get_db), u=Depends(current_user)):
    _get_job(db, job_id)
    rounds = reviews.rounds_for_job(db, job_id)
    return [round_dict(db, r, u) for r in rounds]
@router.post('/jobs/{job_id}/submit', status_code=201)
def submit(job_id: int, db=Depends(get_db), u=Depends(current_user)):
    job = _get_job(db, job_id)
    rnd = reviews.submit(db, job, u)
    record(db, u.email, 'review.submit', {'round': rnd.code, 'job_id': job_id})
    db.commit()
    db.refresh(rnd)
    return round_dict(db, rnd, u)
@router.post('/rounds/{round_id}/resubmit', status_code=201)
def resubmit(round_id: int, db=Depends(get_db), u=Depends(current_user)):
    rnd = _get_round(db, round_id)
    new_round = reviews.resubmit(db, rnd, u)
    record(db, u.email, 'review.resubmit',
           {'round': new_round.code, 'parent': rnd.code, 'job_id': new_round.job_id})
    db.commit()
    db.refresh(new_round)
    return round_dict(db, new_round, u)
@router.post('/rounds/{round_id}/vote')
def vote(round_id: int, data: VoteInput, db=Depends(get_db), u=Depends(current_user)):
    rnd = reviews._lock_round(db, round_id)
    if not rnd:
        raise HTTPException(404, '送审编号不存在')
    rnd, cast = reviews.cast_vote(db, rnd, u, data.decision, data.reason)
    record(db, u.email, 'review.vote',
           {'round': rnd.code, 'decision': data.decision, 'status': rnd.status})
    db.commit()
    db.refresh(rnd)
    return round_dict(db, rnd, u)
@router.post('/rounds/{round_id}/late-vote')
def late_vote(round_id: int, data: LateVoteInput, db=Depends(get_db), u=Depends(current_user)):
    # 迟到意见登记：仅管理员可代登记，且必须指定真实复核人；意见归原编号且不重计票
    if u.role != 'admin':
        raise HTTPException(403, '迟到意见登记仅管理员可操作，普通复核人不能代签')
    rnd = _get_round(db, round_id)
    if rnd.status == 'pending':
        raise HTTPException(409, '送审仍在投票期，请走正常复核通道')
    target = u
    if data.reviewer_id and data.reviewer_id != u.id:
        target = db.get(User, data.reviewer_id)
        if not target:
            raise HTTPException(404, '指定复核人不存在')
        if target.role not in reviews.REVIEWER_ROLES:
            raise HTTPException(422, '该账号不具备复核资格')
    v = reviews.record_late(db, rnd, target, data.decision, data.reason)
    record(db, u.email, 'review.late_vote',
           {'round': rnd.code, 'reviewer_id': target.id, 'decision': data.decision})
    db.commit()
    return {'ok': True, 'round': rnd.code, 'late': True, 'vote_id': v.id}
@router.post('/rounds/{round_id}/arbitration')
def take_arbitration(round_id: int, db=Depends(get_db), u=Depends(current_user)):
    rnd = reviews._lock_round(db, round_id)
    if not rnd:
        raise HTTPException(404, '送审编号不存在')
    reviews.start_arbitration(db, rnd, u)
    record(db, u.email, 'review.arbitration.take', {'round': rnd.code})
    db.commit()
    db.refresh(rnd)
    return round_dict(db, rnd, u)
@router.post('/rounds/{round_id}/arbitrate')
def arbitrate(round_id: int, data: ArbitrateInput, db=Depends(get_db), u=Depends(current_user)):
    rnd = reviews._lock_round(db, round_id)
    if not rnd:
        raise HTTPException(404, '送审编号不存在')
    rnd = reviews.arbitrate(db, rnd, u, data.decision, data.reason)
    record(db, u.email, 'review.arbitrate',
           {'round': rnd.code, 'decision': data.decision, 'status': rnd.status})
    db.commit()
    db.refresh(rnd)
    return round_dict(db, rnd, u)
@router.get('/rounds/{round_id}')
def round_detail(round_id: int, db=Depends(get_db), u=Depends(current_user)):
    rnd = _get_round(db, round_id)
    return round_dict(db, rnd, u)
@router.get('/open')
def open_rounds(db=Depends(get_db), u=Depends(current_user)):
    # 复核工作台：待我处理的送审 + 全部进行中送审（双盲期按权限遮蔽）
    mine = list(db.scalars(select(ReviewRound).where(
        ReviewRound.status.in_(('pending', 'in_arbiter'))
    ).order_by(ReviewRound.id.desc())))
    return [round_dict(db, r, u) for r in mine]
