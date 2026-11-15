from enum import Enum
class Role(str, Enum):
    admin = 'admin'
    analyst = 'analyst'
    viewer = 'viewer'
class JobStatus(str, Enum):
    queued = 'queued'
    running = 'running'
    completed = 'completed'
    failed = 'failed'
class ReviewRoundStatus(str, Enum):
    pending = 'pending'          # 双盲投票收集中
    in_arbiter = 'in_arbiter'    # 两票分歧，等待第三名管理员仲裁
    approved = 'approved'        # 两票通过（或仲裁维持通过），可分发
    rejected = 'rejected'        # 两票驳回（或仲裁驳回），退回发起人
class ReviewDecision(str, Enum):
    approve = 'approve'
    reject = 'reject'
