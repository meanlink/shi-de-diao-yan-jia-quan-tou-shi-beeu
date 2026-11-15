/** @typedef {{id:number,name:string,source:string,rows:number,checksum:string}} Dataset */
/** @typedef {{id:number,name:string,dataset_id:number,status:string,result:Object,approved:boolean,legacy_approved:boolean}} AnalysisJob */
/** @typedef {{id:number,name:string,job_id:number,destination:string,next_run:number,enabled:boolean,review_pending:boolean}} ReportSchedule */
/** @typedef {{id:number,code:string,job_id:number,sequence:number,status:string,blinded:boolean,votes:Array,initiator:Object,arbiter:?Object,viewer_can_vote:boolean,viewer_can_arbitrate:boolean,viewer_can_resubmit:boolean}} ReviewRound */
export {};
