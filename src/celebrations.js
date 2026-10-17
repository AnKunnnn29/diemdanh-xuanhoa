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
  if(range==='month'){endDate.setUTCMonth(endDate.getUTCMonth()+1);endDate.setUTCDate(0);}else endDate.setUTCDate(endDate.getUTCDate()+6);
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
export function feastProfileFields(student,{esc}){
  const date=feastParts(student.feastDay),value=date?`${String(date.day).padStart(2,'0')}/${String(date.month).padStart(2,'0')}`:'';
  return `<label class="field">Ngày bổn mạng<input name="feastDay" type="text" inputmode="numeric" maxlength="5" pattern="[0-9]{2}/[0-9]{2}" value="${esc(value)}" placeholder="dd/mm" aria-describedby="feast-day-help profile-dialog-error"></label><label class="celebration-confirm"><input type="checkbox" name="feastConfirmed" ${student.feastConfirmed?'checked':''} ${value?'required':''}>Tôi đã kiểm tra và xác nhận ngày bổn mạng</label><p id="feast-day-help" class="field-help">Chọn theo vị thánh bổn mạng của em. Để trống nếu chưa xác nhận được; hệ thống không suy đoán từ tên thánh.</p>`;
}
export function celebrationsPage({students,workingClass,today,filters,esc,i,shortDate}){
  const people=students.filter(s=>!workingClass||workingClass==='all'||s.className===workingClass);
  const events=celebrationEvents(people,{today,range:filters.range,month:filters.month,kind:filters.kind,term:filters.term});
  const missing=people.filter(s=>s.feastConfirmed!==true||!feastParts(s.feastDay));
  return `<div class="page-heading"><div><h1>Sinh nhật & bổn mạng</h1><p>Cùng lớp chuẩn bị những lời chúc và giờ cầu nguyện cho các em.</p></div></div><section class="card celebrations-card"><div class="card-body"><div class="celebration-filters"><label class="field">Khoảng thời gian<select id="celebration-range"><option value="week" ${filters.range==='week'?'selected':''}>7 ngày tới</option><option value="month" ${filters.range==='month'?'selected':''}>Theo tháng</option></select></label><label class="field" ${filters.range==='month'?'':'hidden'}>Tháng<input id="celebration-month" type="month" value="${esc(filters.month)}" min="2000-01" max="2100-12"></label><label class="field">Dịp<select id="celebration-kind"><option value="all" ${filters.kind==='all'?'selected':''}>Sinh nhật và bổn mạng</option><option value="birthday" ${filters.kind==='birthday'?'selected':''}>Sinh nhật</option><option value="patron" ${filters.kind==='patron'?'selected':''}>Bổn mạng</option></select></label><label class="field">Tìm thiếu nhi<input id="celebration-search" type="search" value="${esc(filters.term)}" placeholder="Tên hoặc mã thẻ" aria-controls="celebration-list"></label></div><p class="field-help">Theo lớp đang chọn ở đầu trang. Dịp 29/02 được nhắc vào 28/02 trong năm không nhuận và vẫn hiển thị ngày gốc.</p><p role="status" aria-live="polite" aria-atomic="true">${events.length} dịp trong khoảng thời gian đang xem.</p><ul id="celebration-list" class="celebration-list">${events.length?events.map(e=>`<li><div class="celebration-date"><strong>${e.date.slice(8)}</strong><span>Tháng ${Number(e.date.slice(5,7))}</span></div><div class="celebration-person"><span class="celebration-kind">${e.kind==='birthday'?'Sinh nhật':'Bổn mạng'}${e.date===today?' · Hôm nay':''}</span><strong>${esc(e.student.name)}</strong><small>${esc(e.student.className)} · ${esc(e.student.id)}${e.original==='29/02'&&e.date.endsWith('02-28')?' · Ngày gốc 29/02':''}</small></div><button type="button" class="button button-secondary" data-open-profile="${esc(e.student.id)}" aria-label="Xem hồ sơ ${esc(e.student.name)}">${i('users')}Hồ sơ</button></li>`).join(''):'<li class="celebration-empty">Chưa có dịp nào phù hợp. Thử xem theo tháng hoặc chọn lớp khác.</li>'}</ul></div></section><details class="card celebration-missing"><summary>${missing.length} em chưa xác nhận ngày bổn mạng</summary><p class="field-help">Mở hồ sơ để nhập ngày dd/mm và xác nhận sau khi kiểm tra.</p><ul>${missing.map(s=>`<li><div><strong>${esc(s.name)}</strong><small>${esc(s.className)} · ${esc(s.id)}</small></div><button type="button" class="button button-secondary" data-open-profile="${esc(s.id)}" aria-label="Cập nhật ngày bổn mạng của ${esc(s.name)}">Cập nhật hồ sơ</button></li>`).join('')||'<li>Đã có ngày bổn mạng được xác nhận cho các em trong lớp.</li>'}</ul></details>`;
}
