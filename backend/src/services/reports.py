import time, os, csv, io, hashlib, json
from fastapi import HTTPException
from sqlalchemy import select
from src.models import Job, Report, Delivery, ReviewRound
from src.config.settings import ARTIFACT_DIR
def create(db, data):
    j=db.get(Job,data.job_id)
    if not j or j.status!='completed':
        raise HTTPException(409,'请先选择已完成的分析结果')
    if not j.approved:
        raise HTTPException(409,'结论尚未通过双盲复核，不能安排分发')
    if not j.legacy_approved:
        # 新流程：必须存在对应通过的双盲轮次
        passed=db.scalar(select(ReviewRound).where(
            ReviewRound.job_id==j.id, ReviewRound.status=='approved'))
        if not passed:
            raise HTTPException(409,'该结论缺少双盲复核通过记录，不能安排分发')
    r=Report(name=data.name, job_id=j.id, destination=data.destination, interval_seconds=data.interval_seconds, next_run=time.time()+data.delay_seconds, enabled=True)
    db.add(r); db.flush()
    return r
def deliver(db, report):
    j=db.get(Job,report.job_id)
    if not j or not j.approved: return
    # 旧计划（双盲上线前建立）归档前必须补完一次双盲复核；未完成则本次跳过投递
    if getattr(report,'review_pending',False):
        passed=db.scalar(select(ReviewRound).where(
            ReviewRound.job_id==j.id, ReviewRound.status=='approved'))
        if not passed:
            return
        report.review_pending=False
    out=io.StringIO()
    out.write('﻿')
    table=j.result.get('table',{})
    cols=table.get('columns',[])
    writer=csv.writer(out)
    def safe(v):
        if isinstance(v,(int,float)) and not isinstance(v,bool): return v
        text=str(v)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    writer.writerow([safe(c['label']) for c in cols])
    for row in table.get('rows',[]): writer.writerow([safe(row.get(c['key'],'')) for c in cols])
    data=out.getvalue().encode('utf-8')
    delivery=Delivery(report_id=report.id, created_at=time.time(), checksum=hashlib.sha256(data).hexdigest(), filename='', destination=report.destination)
    db.add(delivery); db.flush()
    delivery.filename=f'report-{report.id}-delivery-{delivery.id}.csv'
    os.makedirs(ARTIFACT_DIR,exist_ok=True)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename),'wb') as f:f.write(data)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename+'.json'),'w') as f: json.dump({'job':j.name,'params':j.params,'result':j.result,'checksum':delivery.checksum},f,ensure_ascii=False,allow_nan=False)
    report.next_run=time.time()+report.interval_seconds
    return delivery
