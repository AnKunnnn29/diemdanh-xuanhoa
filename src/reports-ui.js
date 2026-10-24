const activities={mass:'Thánh lễ',lesson:'Giáo lý',early:'Lễ sớm'};

export function reportFiltersFromHash(hash,currentMonth){
  const params=new URLSearchParams(hash.split('?')[1]||'');
  const month=params.get('month');
  return {
    month:/^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(month||'')?month:currentMonth,
    activity:Object.hasOwn(activities,params.get('activity'))?params.get('activity'):'mass',
  };
}

export function createReportsUI({api,esc,state}){
  let generation=0,identityEpoch=0,loading=false,groupSaving=false,draftScope='',groupMessage='',groupsOpen=false;
  let groupRows=[],groupDrafts=new Map(),serverGroups=new Map();
  const currentMonth=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit'}).format(new Date());
  let filters={month:currentMonth(),activity:'mass'};
  const scope=()=>JSON.stringify([state().user?.id,state().yearId]);
  const status=()=>document.getElementById('attendance-report-status');
  const cell=value=>value===null?'Chưa đủ dữ liệu':`${value}%`;

  function resetGroups(){
    identityEpoch++;groupRows=[];groupDrafts.clear();serverGroups.clear();groupSaving=false;groupMessage='';groupsOpen=false;
  }
  function checkScope(){
    if(draftScope!==scope()){resetGroups();draftScope=scope();}
  }
  function groupFeedback(){
    const message=document.getElementById('report-groups-status');
    if(message)message.textContent=groupMessage|| (groupDrafts.size?'Có thay đổi chưa lưu. Bản nháp được giữ khi đổi tháng hoặc chuyển trang trong phiên này.':'Chưa có thay đổi cần lưu.');
    const form=document.getElementById('report-groups-form');
    if(!form)return;
    form.setAttribute('aria-busy',String(groupSaving));
    form.querySelectorAll('input,button').forEach(control=>{control.disabled=groupSaving;});
    form.querySelector('[type=submit]').textContent=groupSaving?'Đang lưu…':'Lưu phân khối báo cáo';
    form.querySelector('[type=submit]').disabled=groupSaving||!groupDrafts.size;
    form.querySelector('[data-discard-groups]').disabled=groupSaving||!groupDrafts.size;
  }
  function renderGroups(){
    const slot=document.getElementById('report-groups-slot');
    if(!slot||!state().isManager||!groupRows.length)return;
    if(!slot.querySelector('form')){
      slot.innerHTML=`<details id="report-groups-panel" class="card report-groups" ${groupsOpen?'open':''}><summary>Phân khối báo cáo</summary><form id="report-groups-form"><p class="field-help" id="report-groups-help">Đặt khối cho từng lớp. Thay đổi chỉ có hiệu lực sau khi lưu.</p><div class="report-group-fields">${groupRows.map(row=>`<label class="field">Khối của ${esc(row.className)}<input name="${esc(row.classId)}" value="${esc(groupDrafts.get(row.classId)??serverGroups.get(row.classId)??'')}" maxlength="80" autocomplete="off" aria-describedby="report-groups-help report-groups-status"></label>`).join('')}</div><p id="report-groups-status" role="status" aria-live="polite"></p><div class="feature-actions"><button type="submit" class="button button-secondary">Lưu phân khối báo cáo</button><button type="button" class="button button-text" data-discard-groups>Bỏ thay đổi</button></div></form></details>`;
      slot.querySelector('details').addEventListener('toggle',event=>{groupsOpen=event.target.open;});
    }
    groupFeedback();
  }
  function page(){
    checkScope();filters=reportFiltersFromHash(location.hash,currentMonth());
    queueMicrotask(()=>{renderGroups();load(filters,'replace');});
    return `<div class="page-heading"><h1>Báo cáo chuyên cần</h1><p>Tổng hợp theo lớp và khối.</p></div><section class="card report-card"><form id="attendance-report-form" class="report-filters"><label class="field">Tháng<input type="month" name="month" value="${filters.month}" required></label><label class="field">Hoạt động<select name="activity">${Object.entries(activities).map(([key,label])=>`<option value="${key}" ${filters.activity===key?'selected':''}>${label}</option>`).join('')}</select></label><button type="submit" class="button button-primary">Xem báo cáo</button></form><p id="attendance-report-status" role="status" aria-live="polite">Đang tải…</p><button type="button" id="attendance-report-retry" class="button button-secondary" hidden>Thử lại</button><div id="attendance-report-content"></div><div class="feature-actions"><button type="button" id="attendance-report-export" class="button button-secondary" disabled>Tải CSV tổng hợp</button></div></section><div id="report-groups-slot"></div>`;
  }
  async function load(requested=filters,historyMode=false){
    const form=document.getElementById('attendance-report-form');if(!form)return;
    checkScope();
    const epoch=++generation,owner=draftScope,content=document.getElementById('attendance-report-content');
    const exportButton=document.getElementById('attendance-report-export'),submit=form.querySelector('[type=submit]');
    const retry=document.getElementById('attendance-report-retry');
    filters={...requested};
    const query=new URLSearchParams(filters);
    if(historyMode){
      const hash='#reports?'+query;
      if(location.hash!==hash)history[historyMode==='push'?'pushState':'replaceState'](null,'',hash);
    }
    loading=true;form.setAttribute('aria-busy','true');submit.disabled=true;submit.textContent='Đang tải…';
    exportButton.disabled=true;retry.hidden=true;content.setAttribute('aria-busy','true');
    status().textContent=content.childElementCount?'Đang tải báo cáo mới; số liệu bên dưới là lần tải trước.':'Đang tính số liệu…';
    try{
      const report=await api('reports/attendance?'+query);
      if(epoch!==generation||!content.isConnected||scope()!==owner)return;
      status().textContent=`${activities[filters.activity]} · Tháng ${report.month.slice(5)}/${report.month.slice(0,4)}`;
      exportButton.disabled=false;exportButton.dataset.query=query.toString();
      content.innerHTML=`<p class="report-total"><strong>Tỷ lệ có mặt: ${cell(report.totals.ratio)}</strong><span>${report.totals.X} có mặt · ${report.totals.P} nghỉ phép · ${report.totals.O} vắng không phép</span></p>${report.groups.length?`<p class="report-group-summary">${report.groups.map(group=>`${esc(group.name)}: ${cell(group.ratio)}`).join(' · ')}</p>`:''}<details class="report-method"><summary>Cách tính và phạm vi</summary><p>${esc(report.notice)}</p></details><div class="table-wrap"><table class="attendance-report-table"><caption>Chuyên cần ${esc(report.month)} so với ${esc(report.previousMonth)}</caption><thead><tr>${['Lớp','Khối','Có mặt','Phép','Vắng','Đã ghi','Tỷ lệ','Thay đổi'].map((label,index)=>`<th scope="col" ${index>1?'class="report-number"':''}>${label}</th>`).join('')}</tr></thead><tbody>${report.classes.map(row=>`<tr><th scope="row" data-label="Lớp">${esc(row.className)}</th><td data-label="Khối">${esc(row.group||'Chưa phân khối')}</td>${[['Có mặt',row.X],['Phép',row.P],['Vắng',row.O],['Đã ghi',row.recorded],['Tỷ lệ',cell(row.ratio)],['Thay đổi',row.changePoints===null?'Chưa đủ dữ liệu':`${row.changePoints>0?'+':''}${row.changePoints} điểm %`]].map(([label,value])=>`<td data-label="${label}" class="report-number">${esc(value)}</td>`).join('')}</tr>`).join('')||'<tr><td colspan="8" class="report-empty">Chưa có lớp trong phạm vi báo cáo.</td></tr>'}</tbody></table></div>`;
      groupRows=report.classes;
      for(const row of groupRows){
        serverGroups.set(row.classId,row.group||'');
        const input=[...document.querySelectorAll('#report-groups-form input')].find(input=>input.name===row.classId);
        if(input&&!groupDrafts.has(row.classId)&&!groupSaving)input.value=row.group||'';
      }
      renderGroups();
    }catch(error){
      if(epoch!==generation||!content.isConnected||scope()!==owner)return;
      if([401,403].includes(error.status)){content.replaceChildren();document.getElementById('report-groups-slot')?.replaceChildren();resetGroups();}
      status().textContent=`${error.message}${content.childElementCount?' Số liệu bên dưới là lần tải trước.':''}`;
      retry.hidden=false;
    }finally{
      if(epoch===generation&&form.isConnected&&scope()===owner){
        loading=false;form.setAttribute('aria-busy','false');content.setAttribute('aria-busy','false');submit.disabled=false;submit.textContent='Xem báo cáo';
      }
    }
  }
  document.addEventListener('input',event=>{
    if(event.target.form?.id!=='report-groups-form')return;
    checkScope();
    const {name,value}=event.target;
    if(value===(serverGroups.get(name)||''))groupDrafts.delete(name);else groupDrafts.set(name,value);
    groupMessage='';groupFeedback();
  });
  window.addEventListener('beforeunload',event=>{
    if(groupDrafts.size||groupSaving){event.preventDefault();event.returnValue='';}
  });
  document.addEventListener('submit',async event=>{
    const form=event.target;
    if(form.id==='attendance-report-form'){
      event.preventDefault();if(!loading)load(Object.fromEntries(new FormData(form)),'push');
    }
    if(form.id!=='report-groups-form')return;
    event.preventDefault();if(groupSaving||!groupDrafts.size)return;
    const owner=scope(),ticket=identityEpoch,submitted=new Map(groupDrafts);
    const stillCurrent=()=>owner===scope()&&owner===draftScope&&ticket===identityEpoch;
    // This API replaces the complete mapping, so include unchanged classes too.
    const groups=Object.fromEntries(groupRows.map(row=>[row.classId,groupDrafts.get(row.classId)??serverGroups.get(row.classId)??'']));
    groupSaving=true;groupMessage='Đang lưu phân khối…';groupFeedback();
    try{
      await api('reports/groups',{groups});
      if(!stillCurrent())return;
      for(const [id,value] of submitted){if(groupDrafts.get(id)===value)groupDrafts.delete(id);serverGroups.set(id,value.trim());}
      groupMessage='Đã lưu phân khối báo cáo.';
    }catch(error){
      if(stillCurrent())groupMessage=`${error.message} Bản nháp vẫn được giữ; hãy thử lưu lại.`;
    }finally{
      if(stillCurrent()){groupSaving=false;groupFeedback();}
    }
    if(stillCurrent()&&!groupDrafts.size)load(filters);
  });
  document.addEventListener('click',async event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.id==='attendance-report-retry'){if(!loading)load(filters);return;}
    if(button.hasAttribute('data-discard-groups')){
      if(groupSaving||!confirm('Bỏ các thay đổi phân khối chưa lưu?'))return;
      groupDrafts.clear();groupMessage='Đã bỏ thay đổi chưa lưu.';
      document.querySelectorAll('#report-groups-form input').forEach(input=>{input.value=serverGroups.get(input.name)||'';});groupFeedback();return;
    }
    if(button.id!=='attendance-report-export')return;
    const epoch=generation,owner=scope();button.disabled=true;
    try{
      const response=await fetch('/api/reports/attendance-export?'+button.dataset.query,{cache:'no-store'});
      if(!response.ok)throw new Error((await response.json()).error);
      const blob=await response.blob();if(epoch!==generation||scope()!==owner||!button.isConnected)return;
      const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='Chuyen-can.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
    }catch(error){if(epoch===generation&&scope()===owner&&button.isConnected)status().textContent=error.message;}
    finally{if(epoch===generation&&scope()===owner&&button.isConnected)button.disabled=false;}
  });
  return {page,clear:()=>{generation++;loading=false;resetGroups();draftScope='';}};
}
