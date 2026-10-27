import {celebrationEvents,feastParts} from './celebrations.js';

export function staffCelebrationPeople(profiles){
  return profiles.map(p=>({id:p.id,name:p.name,birthDate:p.birthDay?'2000-'+p.birthDay:'',feastDay:p.feastDay,feastConfirmed:!!feastParts(p.feastDay)}));
}

export function createStaffCelebrationsUI({api,state,render,esc,today}){
  let model=null,loading=false,error='',epoch=0;
  const filters={range:'week',month:today().slice(0,7),kind:'all',term:''};
  function clear(){epoch++;model=null;loading=false;error='';filters.term='';}
  async function load(){
    if(loading||!state().isManager)return;
    const stamp=epoch;loading=true;error='';render();
    try{const data=await api('admin/celebrations');if(stamp===epoch&&state().isManager)model=data;}
    catch(e){if(stamp===epoch)error=e.message;}
    finally{if(stamp===epoch){loading=false;render();}}
  }
  function page(){
    if(!state().isManager)return '';
    if(!model&&!loading&&!error)queueMicrotask(load);
    const people=staffCelebrationPeople(model?.profiles||[]);
    const events=celebrationEvents(people,{today:today(),...filters});
    return `<div class="page-heading"><div><h1>Sinh nhật & bổn mạng GLV</h1><p>Xem các dịp của GLV đang phục vụ để chuẩn bị thông báo.</p></div></div><section class="card celebrations-card"><div class="card-body"><div class="celebration-filters"><label class="field">Khoảng thời gian<select id="celebration-range">${[['today','Hôm nay'],['week','7 ngày tới'],['month','Theo tháng']].map(([k,v])=>`<option value="${k}" ${filters.range===k?'selected':''}>${v}</option>`).join('')}</select></label><label class="field" ${filters.range==='month'?'':'hidden'}>Tháng<input id="celebration-month" type="month" value="${esc(filters.month)}" min="2000-01" max="2100-12"></label><label class="field">Dịp<select id="celebration-kind">${[['all','Sinh nhật và bổn mạng'],['birthday','Sinh nhật'],['patron','Bổn mạng']].map(([k,v])=>`<option value="${k}" ${filters.kind===k?'selected':''}>${v}</option>`).join('')}</select></label><label class="field">Tìm GLV<input id="celebration-search" type="search" value="${esc(filters.term)}" placeholder="Họ tên GLV" aria-controls="celebration-list" autocomplete="off"></label></div><p class="field-help">Chỉ hiển thị ngày đã nhập trong hồ sơ GLV đang phục vụ. Chưa rõ ngày sinh hoặc ngày bổn mạng thì không tạo lịch nhắc. Dịp 29/02 được nhắc vào 28/02 trong năm không nhuận.</p><div class="feature-actions"><button type="button" class="button button-secondary" id="celebrations-refresh" ${loading?'disabled':''}>${error?'Thử lại':'Làm mới'}</button><a class="button button-secondary" href="#staff">Hồ sơ GLV</a></div>${error?`<p role="alert">${esc(error)}</p>`:''}<p role="status" aria-live="polite" aria-atomic="true">${loading?'Đang tải lịch GLV…':model?`${events.length} dịp trong khoảng thời gian đang xem.`:''}</p><ul id="celebration-list" class="celebration-list" ${loading?'aria-busy="true"':''}>${!loading&&model?events.map(e=>`<li><div class="celebration-date"><strong>${e.date.slice(8)}</strong><span>Tháng ${Number(e.date.slice(5,7))}</span></div><div class="celebration-person"><span class="celebration-kind">${e.kind==='birthday'?'Sinh nhật':'Bổn mạng'}${e.date===today()?' · Hôm nay':''}</span><strong>${esc(e.student.name)}</strong><small>${e.original==='29/02'&&e.date.endsWith('02-28')?'Ngày gốc 29/02':''}</small></div></li>`).join('')||'<li class="celebration-empty">Chưa có dịp nào phù hợp với bộ lọc đang chọn.</li>':''}</ul></div></section>`;
  }
  document.addEventListener('click',e=>{if(e.target.closest('#celebrations-refresh')&&state().isManager)load();});
  document.addEventListener('change',e=>{
    if(!state().isManager)return;
    if(e.target.id==='celebration-range')filters.range=e.target.value;
    else if(e.target.id==='celebration-kind')filters.kind=e.target.value;
    else if(e.target.id==='celebration-month'&&/^\d{4}-\d{2}$/.test(e.target.value))filters.month=e.target.value;
    else return;
    render();
  });
  document.addEventListener('input',e=>{if(e.target.id==='celebration-search'&&state().isManager){filters.term=e.target.value;render();}});
  return {page,clear};
}
