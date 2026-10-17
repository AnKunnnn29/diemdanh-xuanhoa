import {attendanceHistory} from './attendance-metrics.js';

export function monthSummary(marks, code=null) {
  const months=new Map();
  for(const h of attendanceHistory(marks,code)){
    const month=h.date.slice(0,7);
    if(!months.has(month))months.set(month,{month,X:0,P:0,O:0});
    months.get(month)[h.status]++;
  }
  return [...months.values()].sort((a,b)=>a.month.localeCompare(b.month));
}

export function absenceStreak(marks,code,activity='mass',through='9999-12-31') {
  const history=attendanceHistory(marks,code).filter(h=>h.activity===activity&&h.date<=through);
  let count=0;
  for(const h of history){if(h.status!=='O')break;count++;}
  return count;
}

export function lifecycleStatus(records,code,date) {
  const list=records.filter(r=>r.code===code&&r.effective_day<=date).sort((a,b)=>b.effective_day.localeCompare(a.effective_day)||b.stamp.localeCompare(a.stamp));
  // Keep the last stored record when two changes share an effective date and timestamp.
  const same=list.filter(r=>r.effective_day===list[0]?.effective_day&&r.stamp===list[0]?.stamp);
  return same.at(-1)?.status||list[0]?.status||'active';
}

export function csvText(rows) {
  const cell=value=>{
    let text=String(value??'');
    if(/^[\s]*[=+@-]/.test(text))text="'"+text;
    return '"'+text.replaceAll('"','""')+'"';
  };
  return '\ufeff'+rows.map(row=>row.map(cell).join(',')).join('\r\n');
}
