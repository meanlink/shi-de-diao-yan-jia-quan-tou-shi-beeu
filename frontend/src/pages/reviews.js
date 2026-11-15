import {reviews,jobs} from '../api/entities.js';
import {heading} from '../components/common/shell.js';
import {reviewPanel,bindReviewPanel} from '../components/common/review-panel.js';
import {esc} from '../utils/dom.js';
export async function reviewPage(){
 const [open,allJobs]=await Promise.all([reviews.open(),jobs.list()]);
 const jobMap=new Map(allJobs.map(j=>[j.id,j]));
 const mine=open.filter(r=>r.viewer_can_vote||r.viewer_can_arbitrate);
 const panels=open.length
  ? open.map(r=>{const j=jobMap.get(r.job_id);return '<div class="review-job-block"><div class="review-job-title"><a href="#/results/'+r.job_id+'">'+esc(j?j.name:('分析 #'+r.job_id))+' ↗</a><small>送审 '+esc(r.code)+'</small></div>'+reviewPanel(j||{id:r.job_id,status:'completed',legacy_approved:false,approved:false},[r])+'</div>';}).join('')
  : '<p class="empty">当前没有进行中的双盲复核。可到结果页对已完成结论发起送审。</p>';
 const mineHint=mine.length
  ? '<div class="review-banner running">你有 '+mine.length+' 项待处理（投票或仲裁），下方对应卡片可直接操作。</div>'
  : '<div class="review-banner passed">暂无需要你处理的复核项。</div>';
 return heading('05 / BLIND REVIEW','双盲复核工作台','两名非发起人复核人独立给出结论与理由，收齐前互隐身份与意见；两票通过可分发，两票驳回退回，分歧由第三名未参与管理员仲裁。','<a class="button" href="#/results">前往结果页送审 ↗</a>')
  + mineHint
  + '<section class="panel"><div class="section-title"><h2>进行中的送审</h2><span>'+open.length+' 项</span></div>'+panels+'</section>'
  + '<section class="panel"><div class="section-title"><h2>历史送审与解盲意见</h2><span>定案后可查身份与理由</span></div><p class="hint">已关闭的送审（通过/退回）按结论归档在各自的结果页，包含解盲后的复核人身份、结论、理由与迟到意见。<a class="text-link" href="#/results">打开结果复核页 ↗</a></p></section>';
}
export function bindReviewPage(refresh){bindReviewPanel(refresh);}
