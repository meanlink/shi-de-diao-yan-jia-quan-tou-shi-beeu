from sqlalchemy import inspect, text, select
from src.config.database import Base, engine, Session
from src import models
# 既有表上的新增列：create_all 不会补列，需幂等 ALTER
_ADDED_COLUMNS = {
    'jobs': [('legacy_approved', 'BOOLEAN DEFAULT FALSE')],
    'reports': [('review_pending', 'BOOLEAN DEFAULT FALSE')],
}
def _add_missing_columns():
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing:
                continue
            present = {c['name'] for c in inspector.get_columns(table)}
            for name, ddl in columns:
                if name not in present:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
def backfill_legacy():
    """双盲复核上线前的存量数据：
    - 已批准且无任何复核轮次的结论 -> 历史通过（保留效力，不强制重审）
    - 已存在的分发计划 -> 归档前需补完一次双盲复核，已有附件保持原文不动
    幂等：只在新列默认值（未处理）且符合条件时更新。
    """
    with Session() as db:
        round_exists = inspect(engine).has_table('review_rounds')
        jobs = list(db.scalars(select(models.Job).where(models.Job.approved == True)))
        for j in jobs:
            if getattr(j, 'legacy_approved', False):
                continue
            has_round = False
            if round_exists:
                has_round = db.scalar(
                    select(models.ReviewRound.id).where(models.ReviewRound.job_id == j.id).limit(1)
                ) is not None
            if not has_round:
                j.legacy_approved = True
        for r in db.scalars(select(models.Report)):
            if getattr(r, 'review_pending', False):
                continue
            linked = db.get(models.Job, r.job_id)
            # 旧计划且结论尚无复核轮次：归档前补复核；新流程建立的计划本就有通过轮次
            if linked is not None and getattr(linked, 'legacy_approved', False):
                r.review_pending = True
        db.commit()
def migrate():
    Base.metadata.create_all(engine)
    _add_missing_columns()
    backfill_legacy()
if __name__ == '__main__':
    migrate()
