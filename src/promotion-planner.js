import {matchesSearch} from './ux-utils.js';
export function promotionResult(data,code){
 const row=data?.students?.find(r=>r.code===code),number=v=>typeof v==='number'&&Number.isFinite(v);
 if(!row||data.calculationIssues?.length||!number(row.diemGiaoLy)||!number(row.combinedMassScore)||!number(data.thresholds?.catechism)||!number(data.thresholds?.attendance))return {kind:'missing',label:'Cần kiểm tra dữ liệu',row};
 if(row.assessment==='ĐẠT'&&row.diemGiaoLy>=data.thresholds.catechism&&row.combinedMassScore>=data.thresholds.attendance)return {kind:'passed',label:'ĐẠT',row};
 if(String(row.assessment||'').startsWith('KHÔNG ĐẠT'))return {kind:'failed',label:row.assessment,row};
 return {kind:'missing',label:'Cần kiểm tra dữ liệu',row};
}
export function promotionMatches(r,f){return (!f.classId||r.student.classId===f.classId)&&(!f.result||r.result.kind===f.result)&&(!f.review||(f.review==='pending'?!r.approved:f.review==='auto'?r.autoApproved:r.approved&&!r.autoApproved))&&matchesSearch(`${r.student.name} ${r.student.fullName||''} ${r.student.id}`,f.query||'');}
