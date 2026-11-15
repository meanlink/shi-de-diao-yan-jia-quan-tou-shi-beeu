import time
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.models import User, Job, ReviewRound, ReviewVote
REVIEWER_ROLES = ('admin', 'analyst')
SEATS = (1, 2)
ARBITER_SEAT = 3
def _new_code(db, job_id, sequence):
    # 送审编号：同一结论重送递增序号；唯一约束兜底，冲突即换号
    base = f'RV-J{job_id}-{sequence:02d}'
    code = base
    suffix = 0
    while db.scalar(select(ReviewRound.id).where(ReviewRound.code == code)):
        suffix += 1
        code = f'{base}-R{suffix}'
    return code
def _eligible_reviewers(db, job):
    # 非发起人的分析员或管理员；分析员优先占席，尽量保留未参与的管理员用于第三人仲裁
    return list(db.scalars(
        select(User).where(User.role.in_(REVIEWER_ROLES), User.id != job.created_by)
        .order_by(User.role.desc(), User.id.asc())
    ))
def _lock_round(db, round_id):
    # 行锁串行化同轮签署，杜绝并发签署/重送串票（Postgres 行锁；SQLite 回退普通读取）
    rnd = db.get(ReviewRound, round_id)
    if rnd is not None:
        try:
            db.execute(select(ReviewRound).where(ReviewRound.id == round_id).with_for_update())
        except Exception:
            pass
    return rnd
def submit(db, job, initiator):
    if initiator.role not in REVIEWER_ROLES:
        raise HTTPException(403, '仅分析员或管理员可以送交复核')
    if job.status != 'completed':
        raise HTTPException(409, '仅已完成的研究结论可以送交双盲复核')
    if initiator.id == job.created_by:
        raise HTTPException(403, '发起人不能复核自己的结论，请由其他分析员或管理员送审')
    # 同一结论只允许一个进行中的轮次；退回后才能重送且生成新编号
    active = db.scalar(select(ReviewRound).where(
        ReviewRound.job_id == job.id,
        ReviewRound.status.in_(('pending', 'in_arbiter'))
    ))
    if active:
        raise HTTPException(409, f'该结论已有进行中的送审 {active.code}，收票后再操作')
    reviewers = _eligible_reviewers(db, job)
    if len(reviewers) < 2:
        raise HTTPException(409, '符合条件的非发起人复核人不足两名，无法组成双盲复核')
    last = db.scalar(select(ReviewRound).where(ReviewRound.job_id == job.id)
                     .order_by(ReviewRound.sequence.desc()))
    sequence = (last.sequence + 1) if last else 1
    parent_id = last.id if last else None
    rnd = ReviewRound(
        code=_new_code(db, job.id, sequence), job_id=job.id, sequence=sequence,
        status='pending', initiator_id=initiator.id, created_at=time.time(),
        parent_id=parent_id,
    )
    db.add(rnd)
    try:
        db.flush()
    except IntegrityError:
        # 并发送审/重送在 (job_id, sequence) 唯一约束上相撞：回滚本事务并明确拒绝
        db.rollback()
        raise HTTPException(409, '该结论的送审正在被并发处理，请刷新后重试')
    # 两个独立席位预先指定两名非发起人复核人；彼此身份在收齐前互不可见
    for seat, reviewer in zip(SEATS, reviewers[:2]):
        db.add(ReviewVote(round_id=rnd.id, reviewer_id=reviewer.id, seat=seat,
                          decision='', reason='', created_at=0.0))
    db.flush()
    return rnd
def resubmit(db, rnd, initiator):
    # 退回重送：仅允许从 rejected 轮次发起，生成全新送审编号，不复制旧票
    if rnd.status != 'rejected':
        raise HTTPException(409, '仅已退回的送审可以重新送交')
    job = db.get(Job, rnd.job_id)
    return submit(db, job, initiator)
def _tally(db, rnd):
    # 仅统计双盲两席的正式票（占位空票与迟到票不计）
    votes = list(db.scalars(select(ReviewVote).where(
        ReviewVote.round_id == rnd.id, ReviewVote.seat.in_(SEATS)
    )))
    decided = [v for v in votes if v.decision and not v.late]
    approvals = sum(1 for v in decided if v.decision == 'approve')
    rejections = sum(1 for v in decided if v.decision == 'reject')
    job = db.get(Job, rnd.job_id)
    if approvals == 2:
        rnd.status = 'approved'
        rnd.closed_at = rnd.decided_at = time.time()
        job.approved = True
        job.legacy_approved = False
    elif rejections == 2:
        rnd.status = 'rejected'
        rnd.closed_at = rnd.decided_at = time.time()
        job.approved = False
    elif len(decided) == 2 and approvals == 1 and rejections == 1:
        rnd.status = 'in_arbiter'
        rnd.closed_at = time.time()
    return rnd
def cast_vote(db, rnd, user, decision, reason):
    if decision not in ('approve', 'reject'):
        raise HTTPException(422, '结论必须是通过或驳回')
    reason = (reason or '').strip()
    if len(reason) < 4:
        raise HTTPException(422, '请填写不少于 4 个字的复核理由')
    if len(reason) > 1000:
        raise HTTPException(422, '复核理由不超过 1000 字')
    if rnd.status != 'pending':
        # 轮次已关闭：意见仍归原编号留痕（迟到），但拒绝代签/重计
        raise HTTPException(409, f'送审 {rnd.code} 已关闭，意见仅可登记为迟到意见，不再计票')
    vote = db.scalar(select(ReviewVote).where(
        ReviewVote.round_id == rnd.id, ReviewVote.reviewer_id == user.id
    ))
    if vote is None:
        raise HTTPException(403, '你不是本轮指定复核人，不能代签')
    if vote.decision:
        raise HTTPException(409, '你已提交本轮意见，不能重复记票或改票')
    vote.decision = decision
    vote.reason = reason
    vote.created_at = time.time()
    db.flush()
    _tally(db, rnd)
    return rnd, vote
def record_late(db, rnd, user, decision, reason):
    # 迟到意见：归原送审编号、标记 late，不参与任何计票
    reason = (reason or '').strip()
    if decision not in ('approve', 'reject') or len(reason) < 4:
        raise HTTPException(422, '迟到意见也需明确结论与理由')
    existing = db.scalar(select(ReviewVote).where(
        ReviewVote.round_id == rnd.id, ReviewVote.reviewer_id == user.id
    ))
    if existing is not None and existing.decision:
        raise HTTPException(409, '该复核人在本编号下已有意见，不能重复登记')
    seat = existing.seat if existing else ARBITER_SEAT
    if existing is not None and not existing.decision:
        existing.decision = decision
        existing.reason = reason
        existing.created_at = time.time()
        existing.late = True
        vote = existing
    else:
        vote = ReviewVote(round_id=rnd.id, reviewer_id=user.id, seat=seat,
                          decision=decision, reason=reason, created_at=time.time(), late=True)
        db.add(vote)
    db.flush()
    return vote
def start_arbitration(db, rnd, user):
    if rnd.status != 'in_arbiter':
        raise HTTPException(409, '仅分歧待裁的送审可以指定仲裁管理员')
    if user.role != 'admin':
        raise HTTPException(403, '仲裁须由管理员承担')
    participated = {v.reviewer_id for v in db.scalars(
        select(ReviewVote).where(ReviewVote.round_id == rnd.id)
    )}
    if user.id in participated or user.id == rnd.initiator_id:
        raise HTTPException(403, '仲裁管理员必须未参与本轮复核且非送审发起人')
    rnd.arbiter_id = user.id
    db.flush()
    return rnd
def arbitrate(db, rnd, user, decision, reason):
    if rnd.status != 'in_arbiter':
        raise HTTPException(409, '该送审不在仲裁阶段')
    if user.role != 'admin':
        raise HTTPException(403, '仲裁须由管理员承担')
    if rnd.arbiter_id is None:
        raise HTTPException(409, '请先由未参与的管理员承接仲裁')
    if rnd.arbiter_id != user.id:
        raise HTTPException(403, '仅承接仲裁的管理员可以签署仲裁结论，不能代签')
    reason = (reason or '').strip()
    if decision not in ('approve', 'reject') or len(reason) < 4:
        raise HTTPException(422, '仲裁须给出明确结论与不少于 4 个字的理由')
    if len(reason) > 1000:
        raise HTTPException(422, '仲裁理由不超过 1000 字')
    existing = db.scalar(select(ReviewVote).where(
        ReviewVote.round_id == rnd.id, ReviewVote.reviewer_id == user.id
    ))
    if existing is not None and existing.decision:
        raise HTTPException(409, '仲裁结论已提交，不能重复记票')
    if existing is None:
        db.add(ReviewVote(round_id=rnd.id, reviewer_id=user.id, seat=ARBITER_SEAT,
                          decision=decision, reason=reason, created_at=time.time(), late=False))
    else:
        existing.decision = decision
        existing.reason = reason
        existing.created_at = time.time()
    job = db.get(Job, rnd.job_id)
    rnd.status = 'approved' if decision == 'approve' else 'rejected'
    rnd.decided_at = time.time()
    job.approved = decision == 'approve'
    if decision == 'approve':
        job.legacy_approved = False
    db.flush()
    return rnd
def rounds_for_job(db, job_id):
    return list(db.scalars(select(ReviewRound).where(ReviewRound.job_id == job_id)
                           .order_by(ReviewRound.sequence.asc())))
def active_round(db, job_id):
    return db.scalar(select(ReviewRound).where(
        ReviewRound.job_id == job_id,
        ReviewRound.status.in_(('pending', 'in_arbiter'))
    ).order_by(ReviewRound.id.desc()))
