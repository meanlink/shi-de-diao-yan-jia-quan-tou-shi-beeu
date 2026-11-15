import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const reviews={
  rounds:jobId=>api('/reviews/jobs/'+jobId+'/rounds'),
  open:()=>api('/reviews/open'),
  get:roundId=>api('/reviews/rounds/'+roundId),
  submit:jobId=>api('/reviews/jobs/'+jobId+'/submit',{method:'POST'}),
  resubmit:roundId=>api('/reviews/rounds/'+roundId+'/resubmit',{method:'POST'}),
  vote:(roundId,data)=>api('/reviews/rounds/'+roundId+'/vote',{method:'POST',body:JSON.stringify(data)}),
  lateVote:(roundId,data)=>api('/reviews/rounds/'+roundId+'/late-vote',{method:'POST',body:JSON.stringify(data)}),
  takeArbitration:roundId=>api('/reviews/rounds/'+roundId+'/arbitration',{method:'POST'}),
  arbitrate:(roundId,data)=>api('/reviews/rounds/'+roundId+'/arbitrate',{method:'POST',body:JSON.stringify(data)})
};
