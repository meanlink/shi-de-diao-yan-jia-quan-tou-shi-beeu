import {jobs,reviews} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {chart} from '../components/common/chart.js';
import {table} from '../components/common/table.js';
import {status} from '../components/common/status.js';
import {reviewPanel,bindReviewPanel} from '../components/common/review-panel.js';
import {esc,fmt,date,notify} from '../utils/dom.js';
export async function results(id){
 workspace.jobs=await jobs.list();const j=id?await jobs.get(id):(workspace.jobs.find(j=>j.id===workspace.selectedJob)||workspace.jobs[0]);
 if(j&&!workspace.jobs.some(x=>x.id===j.id))workspace.jobs.push(j);
 if(!j)return heading('04 / REVIEW','结果复核','尚无分析结果。')+'<div class="empty">先到分析工作台，选择批次并提交一次计算。<a href="#/workbench">前往工作台 ↗</a></div>';
 workspace.selectedJob=j.id;const r=j.result||{};
 const rounds=j.status==='completed'?await reviews.rounds(j.id):[];
 const approvalText=j.legacy_approved?'历史通过（双盲上线前批准）':(j.approved?'已通过双盲复核':'待双盲复核');
 const reviewBlock=j.status==='completed'?reviewPanel(j,rounds):'';
 return heading('04 / REVIEW','结果复核与业务解释',j.name,'<button class="button" id="refresh-results">刷新结果 ↻</button>')+'<div class="result-selector"><label>分析记录<select id="select-job">'+workspace.jobs.map(x=>'<option value="'+x.id+'" '+(x.id===j.id?'selected':'')+'>'+esc(x.name)+' · '+esc(x.status)+'</option>').join('')+'</select></label>'+status(j.status)+'<span>'+date(j.created_at)+'</span><span class="approval">'+esc(approvalText)+'</span></div>'+(j.status==='completed'?'<section class="result-lead"><p class="eyebrow">COMPUTED FINDING</p><h2>'+esc(r.summary)+'</h2><div class="metrics">'+(r.metrics||[]).map(m=>'<div><span>'+esc(m.label)+'</span><strong>'+esc(fmt(m.value))+'<small>'+esc(m.unit||'')+'</small></strong></div>').join('')+'</div></section><section class="panel">'+chart(r.chart)+'</section><div class="two-columns"><section class="panel"><div class="section-title"><h2>业务解释</h2><span>由计算结果生成</span></div><ol class="questions">'+(r.findings||[]).map(v=>'<li>'+esc(v)+'</li>').join('')+'</ol>'+(r.warnings||[]).map(v=>'<p class="warning">'+esc(v)+'</p>').join('')+'</section><section class="method-sheet compact"><p class="eyebrow">REPRODUCIBILITY</p><h3>计算口径与参数</h3><p>'+esc(r.method)+'</p><pre>'+esc(JSON.stringify(j.params,null,2))+'</pre><p class="hint">结论须经双盲复核两票通过后方可分发；单人批准入口已停用。</p></section></div>'+reviewBlock+'<section class="panel"><div class="section-title"><h2>结果明细</h2><span>'+(r.table?.rows?.length||0)+' 行</span></div>'+table(r.table?.columns||[],r.table?.rows||[])+'</section>':'<section class="panel empty">'+(j.status==='failed'?'计算失败：'+esc(j.error)+'。请返回工作台调整参数或数据。':'后台正在执行计算。点击刷新结果查看最新进展。')+'<a href="#/workbench">返回工作台 ↗</a></section>');
}
export function bindResults(refresh){
 document.querySelector('#refresh-results')?.addEventListener('click',refresh);
 document.querySelector('#select-job')?.addEventListener('change',e=>{workspace.selectedJob=Number(e.target.value);location.hash='#/results/'+e.target.value;});
 bindReviewPanel(refresh);
}
