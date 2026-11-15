from sqlalchemy import select
from src.models import User, ReviewRound, ReviewVote
def _user_map(db, ids):
    if not ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(list(set(ids))))).all()
    return {u.id: {'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role} for u in users}
# 轮次关闭（进入仲裁或已定案）后才可解盲；pending 期间双盲严格生效
def _blinded(rnd):
    return rnd.status == 'pending'
def vote_dict(db, vote, rnd, viewer):
    users = _user_map(db, [vote.reviewer_id])
    reviewer = users.get(vote.reviewer_id, {'id': vote.reviewer_id, 'name': '未知', 'email': '', 'role': ''})
    submitted = bool(vote.decision)
    out = {
        'seat': vote.seat,
        'submitted': submitted,
        'late': vote.late,
        'created_at': vote.created_at if submitted else None,
    }
    is_self = viewer is not None and viewer.id == vote.reviewer_id
    # 双盲期：只有本席位复核人能看到自己的身份与意见；其他人只见匿名席位与是否已提交
    if _blinded(rnd) and not is_self:
        out['reviewer'] = None
        out['decision'] = None
        out['reason'] = ''
        out['blinded'] = True
        return out
    out['reviewer'] = reviewer
    out['decision'] = vote.decision or None
    out['reason'] = vote.reason
    out['blinded'] = False
    return out
def round_dict(db, rnd, viewer):
    votes = list(db.scalars(select(ReviewVote).where(ReviewVote.round_id == rnd.id)
                            .order_by(ReviewVote.seat.asc(), ReviewVote.id.asc())))
    users = _user_map(db, [rnd.initiator_id, rnd.arbiter_id])
    arbiter = users.get(rnd.arbiter_id) if rnd.arbiter_id else None
    # 仲裁承接前不暴露候选管理员；承接后且已离开双盲期可显示
    if _blinded(rnd):
        arbiter = None
    return {
        'id': rnd.id,
        'code': rnd.code,
        'job_id': rnd.job_id,
        'sequence': rnd.sequence,
        'status': rnd.status,
        'initiator': users.get(rnd.initiator_id),
        'arbiter': arbiter,
        'parent_id': rnd.parent_id,
        'created_at': rnd.created_at,
        'closed_at': rnd.closed_at,
        'decided_at': rnd.decided_at,
        'blinded': _blinded(rnd),
        'votes': [vote_dict(db, v, rnd, viewer) for v in votes],
        # 当前查看者在本轮的可执行动作，由前端按此渲染；服务端仍独立鉴权
        'viewer_can_vote': _can_vote(rnd, votes, viewer),
        'viewer_can_arbitrate': _can_arbitrate(rnd, viewer),
        'viewer_can_resubmit': rnd.status == 'rejected' and viewer is not None
                               and viewer.role in ('admin', 'analyst'),
    }
def _can_vote(rnd, votes, viewer):
    if viewer is None or rnd.status != 'pending':
        return False
    for v in votes:
        if v.reviewer_id == viewer.id and v.seat in (1, 2) and not v.decision:
            return True
    return False
def _can_arbitrate(rnd, viewer):
    if viewer is None or rnd.status != 'in_arbiter' or viewer.role != 'admin':
        return False
    if rnd.arbiter_id is not None:
        return rnd.arbiter_id == viewer.id
    return True
