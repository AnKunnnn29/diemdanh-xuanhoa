import {matchesSearch} from './ux-utils.js';

export function gradeValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  return typeof value === 'number' ? new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 1}).format(value) : String(value);
}
const entered=value=>value!==null&&value!==undefined&&value!=='';
export function missingGradeInputs(row){
  const average=typeof row.tbHk==='number'?row.tbHk:Number(String(row.tbHk??'').replace(',','.'));
  return Number.isFinite(average)&&average!==0&&![...(row.khaoBai||[]),row.kt15,row.kt1Tiet,row.thiKinh,row.thiHk].some(entered);
}
export function khaoBaiDetails(row,{esc,disclosure=true}={}){
  const values=Array.from({length:20},(_,n)=>row.khaoBai?.[n]);
  const count=values.filter(entered).length;
  const summary=count?`${count}/20 lượt đã nhập`:'Chưa nhập khảo bài';
  const list=`<ol class="grade-khao-bai">${values.map((value,n)=>`<li><span>KB ${n+1}</span><strong>${esc(gradeValue(value))}</strong></li>`).join('')}</ol>`;
  return disclosure?`<details class="grade-khao-bai-details"><summary>${summary}</summary>${list}</details>`:`<div class="grade-khao-bai-details"><p>Khảo bài · ${summary}</p>${list}</div>`;
}
export function selectGradeRows(rows, {query = '', assessment = 'all', sort = 'roster'} = {}) {
  const selected = rows.filter(row => matchesSearch(`${row.code} ${row.name}`,query) &&
    (assessment === 'all' || (assessment === 'passed' ? row.assessment === 'ĐẠT' : assessment === 'failed' ? String(row.assessment || '').startsWith('KHÔNG ĐẠT') : !row.assessment)));
  return sort === 'rank' ? selected.sort((a,b) => (typeof a.yearRank === 'number' ? a.yearRank : Infinity) - (typeof b.yearRank === 'number' ? b.yearRank : Infinity) || a.rosterRow - b.rosterRow) : selected;
}
