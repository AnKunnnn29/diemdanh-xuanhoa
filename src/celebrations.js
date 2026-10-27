import {matchesSearch} from './ux-utils.js';

export function birthParts(value){
  const text=String(value||'').trim();
  let parts;
  if(/^\d{4}-\d{2}-\d{2}$/.test(text))parts=text.split('-').map(Number);
  else if(/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(text))parts=text.split('/').map(Number).reverse();
  else return null;
  const [year,month,day]=parts,date=new Date(Date.UTC(year,month-1,day));
  return year>=1900&&date.getUTCFullYear()===year&&date.getUTCMonth()===month-1&&date.getUTCDate()===day?{year,month,day}:null;
}
export function feastParts(value){
  const text=String(value||'').trim();
  if(!/^\d{2}-\d{2}$/.test(text))return null;
  const [month,day]=text.split('-').map(Number),date=new Date(Date.UTC(2000,month-1,day));
  return date.getUTCMonth()===month-1&&date.getUTCDate()===day?{month,day}:null;
}
const iso=date=>date.toISOString().slice(0,10);
const occurrence=(parts,year)=>{
  const date=new Date(Date.UTC(year,parts.month-1,parts.day));
  // Keep the original anniversary visible; use Feb 28 in non-leap years.
  if(parts.month===2&&parts.day===29&&date.getUTCMonth()===2)date.setUTCDate(0);
  return iso(date);
};
export function celebrationEvents(students,{today,range='week',month=today.slice(0,7),kind='all',className='all',term=''}={}){
  if(!birthParts(today)||!/^\d{4}-(0[1-9]|1[0-2])$/.test(month))return [];
  const start=range==='month'?month+'-01':today;
  const endDate=new Date(start+'T00:00:00Z');
  if(range==='month'){endDate.setUTCMonth(endDate.getUTCMonth()+1);endDate.setUTCDate(0);}else if(range!=='today')endDate.setUTCDate(endDate.getUTCDate()+6);
  const end=iso(endDate),years=[...new Set([Number(start.slice(0,4)),Number(end.slice(0,4))])];
  return students.filter(s=>(!className||className==='all'||s.className===className)&&matchesSearch(`${s.name} ${s.id} ${s.className}`,term)).flatMap(student=>{
    const dates=[['birthday',birthParts(student.birthDate)],['patron',student.feastConfirmed===true?feastParts(student.feastDay):null]];
    return dates.flatMap(([type,parts])=>{
      if(!parts||kind!=='all'&&kind!==type)return [];
      return years.map(year=>({student,kind:type,date:occurrence(parts,year),original:`${String(parts.day).padStart(2,'0')}/${String(parts.month).padStart(2,'0')}`}))
        .filter(e=>e.date>=start&&e.date<=end&&(!parts.year||Number(e.date.slice(0,4))>=parts.year));
    });
  }).sort((a,b)=>a.date.localeCompare(b.date)||a.student.name.localeCompare(b.student.name,'vi')||a.kind.localeCompare(b.kind));
}
