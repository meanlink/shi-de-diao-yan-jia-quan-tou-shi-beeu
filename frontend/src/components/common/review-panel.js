import {reviews} from '../../api/entities.js';
import {session} from '../../stores/session.js';
import {ReviewRoundStatus,ReviewDecision} from '../../constants/enums.js';
import {esc,date,notify} from '../../utils/dom.js';
const seatLabel=seat=>seat===3?'仲裁席位':'复核席位 '+seat;
const decisionBadge=d=>d?('<span class="vote-decision '+esc(d)+'">'+esc(ReviewDecision[d]||d)+'</span>'):'';
function voteLine(v){
 if(v.blinded){
  return '<div class="vote-row blind"><span class="seat">'+esc(seatLabel(v.seat))+'</span><span class="blind-note">'+(v.submitted?'已提交 · 双盲中，身份与意见暂隐':'待提交')+'</span></div>';
 }
 return '<div class="vote-row'+(v.late?' late':'')+'"><div class="vote-head"><span class="seat">'+esc(seatLabel(v.seat))+'</span>'+decisionBadge(v.decision)+(v.late?'<span class="late-tag">迟到意见 · 不计票</span>':'')+'</div><div class="vote-who">'+esc(v.reviewer?.name||'—')+' · '+esc(v.reviewer?.role||'')+(v.created_at?' · '+date(v.created_at):'')+'</div>'+(v.reason?'<p class="vote-reason">'+esc(v.reason)+'</p>':'')+'</div>';
}
function roundCard(r){
 const canVote=r.viewer_can_vote,canArb=r.viewer_can_arbitrate,canResub=r.viewer_can_resubmit;
 const isAdmin=session.user.role==='admin';
 return '<article class="review-round status-'+esc(r.status)+'">'
  +'<div class="round-head"><div><strong class="round-code">'+esc(r.code)+'</strong>'
  +'<span class="review-status '+esc(r.status)+'">'+esc(ReviewRoundStatus[r.status]||r.status)+'</span></div>'
  +'<small>第 '+r.sequence+' 次送审 · 发起 '+(r.initiator?esc(r.initiator.name):'—')+' · '+date(r.created_at)+'</small></div>'
  +(r.arbiter?'<p class="arbiter-line">仲裁管理员：'+esc(r.arbiter.name)+(r.status==='in_arbiter'?'（等待仲裁结论）':'')+'</p>':'')
  +'<div class="vote-list">'+r.votes.map(voteLine).join('')+'</div>'
  +(r.blinded?'<p class="hint blind-hint">双盲进行中：收齐两票前，复核人彼此看不到对方身份与意见。</p>':'')
  +(canVote?'<form class="vote-form" data-round="'+r.id+'"><label>我的复核结论<select name="decision"><option value="approve">通过</option><option value="reject">驳回</option></select></label><label>复核理由（随结论留痕，解盲后可查）<textarea name="reason" rows="3" required minlength="4" maxlength="1000" placeholder="请写明依据，不少于 4 个字"></textarea></label><button type="submit" class="primary small">提交独立意见</button></form>':'')
  +(r.status==='in_arbiter'&&canArb&&!r.arbiter?'<button class="button small" data-take-arb="'+r.id+'">由我承接仲裁（未参与的管理员）</button>':'')
  +(r.status==='in_arbiter'&&canArb&&r.arbiter?'<form class="vote-form" data-arbitrate="'+r.id+'"><label>仲裁结论<select name="decision"><option value="approve">维持通过</option><option value="reject">维持驳回</option></select></label><label>仲裁理由<textarea name="reason" rows="3" required minlength="4" maxlength="1000" placeholder="第三名管理员的独立裁决理由"></textarea></label><button type="submit" class="primary small">签署仲裁结论</button></form>':'')
  +(canResub?'<button class="button small" data-resubmit="'+r.id+'">退回重送（生成新送审编号）</button>':'')
  +(isAdmin&&!r.blinded?'<details class="late-box"><summary>登记迟到意见（归原编号，不重计票）</summary><form class="vote-form" data-late="'+r.id+'"><label>迟到结论<select name="decision"><option value="approve">通过</option><option value="reject">驳回</option></select></label><label>迟到理由<textarea name="reason" rows="2" required minlength="4" maxlength="1000"></textarea></label><button type="submit" class="small">登记迟到意见</button></form></details>':'')
  +'</article>';
}
export function reviewPanel(job,rounds){
 const role=session.user.role;
 const canSubmit=role==='admin'||role==='analyst';
 const active=rounds.find(r=>r.status==='pending'||r.status==='in_arbiter');
 const legacy=job.legacy_approved;
 let head;
 if(legacy) head='<div class="review-banner legacy">历史通过：该结论在双盲复核上线前已批准，效力保留；关联的旧分发计划在补完双盲复核前暂停归档。</div>';
 else if(job.approved) head='<div class="review-banner passed">已通过双盲复核，可安排分发。</div>';
 else if(active) head='<div class="review-banner running">双盲复核进行中，两票通过后方可分发。</div>';
 else head='<div class="review-banner idle">尚未通过双盲复核，分发前须完成两票制独立复核。</div>';
 const submitBtn=(canSubmit&&!active&&job.status==='completed')?'<button class="button small" data-submit="'+job.id+'">送交双盲复核</button>':'';
 return '<section class="panel review-panel"><div class="section-title"><h2>双盲复核</h2>'+submitBtn+'</div>'+head
  +(rounds.length?'<div class="rounds">'+rounds.slice().reverse().map(roundCard).join('')+'</div>':'<p class="empty">尚无送审记录。由非发起人的分析员或管理员送交后，指定两名独立复核人。</p>')
  +'</section>';
}
export function bindReviewPanel(refresh){
 const q=s=>document.querySelectorAll(s);
 q('[data-submit]').forEach(b=>b.addEventListener('click',async()=>{
  try{await reviews.submit(b.dataset.submit);notify('已送交双盲复核，送审编号已生成');await refresh();}
  catch(e){notify(e.message,true);}
 }));
 q('[data-resubmit]').forEach(b=>b.addEventListener('click',async()=>{
  try{await reviews.resubmit(b.dataset.resubmit);notify('已重新送审，生成新的送审编号');await refresh();}
  catch(e){notify(e.message,true);}
 }));
 q('[data-take-arb]').forEach(b=>b.addEventListener('click',async()=>{
  try{await reviews.takeArbitration(b.dataset.takeArb);notify('你已承接仲裁，请签署独立结论');await refresh();}
  catch(e){notify(e.message,true);}
 }));
 q('form.vote-form[data-round]').forEach(f=>f.addEventListener('submit',async e=>{
  e.preventDefault();const body=new FormData(f);
  try{await reviews.vote(f.dataset.round,{decision:body.get('decision'),reason:body.get('reason')});notify('独立意见已提交，收齐前对其他复核人保密');await refresh();}
  catch(err){notify(err.message,true);}
 }));
 q('form.vote-form[data-arbitrate]').forEach(f=>f.addEventListener('submit',async e=>{
  e.preventDefault();const body=new FormData(f);
  try{await reviews.arbitrate(f.dataset.arbitrate,{decision:body.get('decision'),reason:body.get('reason')});notify('仲裁结论已签署');await refresh();}
  catch(err){notify(err.message,true);}
 }));
 q('form.vote-form[data-late]').forEach(f=>f.addEventListener('submit',async e=>{
  e.preventDefault();const body=new FormData(f);
  try{await reviews.lateVote(f.dataset.late,{decision:body.get('decision'),reason:body.get('reason')});notify('迟到意见已归入原送审编号，不参与计票');await refresh();}
  catch(err){notify(err.message,true);}
 }));
}
