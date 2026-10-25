// Only saved marks determine presence or absence; unrecorded pupils stay separate.
export function groupSessionAttendance(people,{markFor,isWaiting=()=>false,isMakeupDone=()=>false}) {
  const groups={present:[],absent:[],waiting:[],makeup:[],unrecorded:[]};
  for(const student of [...people].sort((a,b)=>(a.fullName||a.name).localeCompare(b.fullName||b.name,'vi')||a.id.localeCompare(b.id))){
    const mark=markFor(student),entry={student,mark};
    if(mark?.status==='X')groups.present.push(entry);
    else if(['P','O'].includes(mark?.status))groups.absent.push(entry);
    else if(isWaiting(student))groups.waiting.push(entry);
    else if(isMakeupDone(student))groups.makeup.push(entry);
    else groups.unrecorded.push(entry);
  }
  return groups;
}

export function earlyMassAttendance(people,marks,date) {
  return groupSessionAttendance(people,{markFor:student=>marks[`${date}|early|${student.id}`]});
}

const oneLine=value=>String(value??'').replace(/\s+/g,' ').trim();

export function sessionStudentName(student) {
  return student.fullName?[student.saintName,student.fullName].map(oneLine).filter(Boolean).join(' '):oneLine(student.name||student.saintName);
}

export function presentClipboardText(groups,kind) {
  if(!['codes','names'].includes(kind))throw new Error('Chỉ sao chép mã hoặc tên của các em có mặt.');
  return groups.present.filter(({mark})=>mark?.status==='X').map(({student})=>kind==='codes'?oneLine(student.id):sessionStudentName(student)).filter(Boolean).join('\n');
}

export async function copySessionText(text,{navigator=globalThis.navigator,document=globalThis.document,isCurrent=()=>true}={}) {
  if(!text||!isCurrent())return false;
  try{
    if(navigator?.clipboard?.writeText){await navigator.clipboard.writeText(text);return true;}
  }catch{}
  if(!isCurrent()||!document?.execCommand)return false;
  const active=document.activeElement,selection=document.getSelection();
  const ranges=selection?Array.from({length:selection.rangeCount},(_,index)=>selection.getRangeAt(index).cloneRange()):[];
  const input=document.createElement('textarea');
  input.value=text;input.readOnly=true;input.tabIndex=-1;input.setAttribute('aria-hidden','true');
  input.style.cssText='position:fixed;inset:0 auto auto -10000px;opacity:0;';
  document.body.append(input);
  try{input.select();input.setSelectionRange(0,text.length);return document.execCommand('copy')===true;}
  catch{return false;}
  finally{
    input.remove();
    if(active?.isConnected)active.focus({preventScroll:true});
    if(selection){selection.removeAllRanges();for(const range of ranges)if(range.commonAncestorContainer.isConnected)selection.addRange(range);}
  }
}

export function sessionSummaryHtml(groups,{esc,timeOf,closed=true,context='',earlyGroups=null}) {
  const permitted=groups.absent.filter(({mark})=>mark.status==='P').length;
  const roster=(entries,kind)=>entries.length?`<div class="session-summary-columns" aria-hidden="true"><span>Mã số</span><span>Tên Thánh, họ và tên</span></div><ol class="session-summary-list">${entries.map(({student:s,mark})=>`<li>
    <span class="session-summary-code tabular-nums"><span class="sr-only">Mã số </span>${esc(s.id)}</span>
    <div class="session-summary-person"><strong>${esc(sessionStudentName(s)||'Chưa có tên')}</strong><small>${esc(s.className)}</small></div>
    ${kind==='absent'?`<span class="status ${mark.status.toLowerCase()}">${mark.status==='P'?'Nghỉ phép':'Vắng không phép'}</span>`:['present','early'].includes(kind)&&mark?.timestamp?`<span class="session-summary-time tabular-nums">${esc(timeOf(mark.timestamp))}</span>`:''}
  </li>`).join('')}</ol>`:`<p class="session-summary-empty">${kind==='early'?'Chưa có em nào được ghi nhận đi lễ sớm trong ngày này.':kind==='present'?'Chưa có em nào được ghi nhận có mặt.':'Không có em nào vắng trong buổi này.'}</p>`;
  const copyActions=`<div class="session-summary-actions"><button type="button" class="button button-secondary" data-copy-present="codes" ${groups.present.length?'':'disabled'}>Sao chép tất cả mã số</button><button type="button" class="button button-secondary" data-copy-present="names" ${groups.present.length?'':'disabled'}>Sao chép tên Thánh, họ và tên</button></div><p class="field-help session-summary-copy-status" data-summary-copy-status role="status" aria-live="polite" aria-atomic="true">Mỗi em một dòng. Chỉ sao chép các em có mặt đã được lưu.</p><div data-summary-copy-fallback hidden><label class="field">Sao chép thủ công<textarea data-summary-copy-text readonly rows="6" spellcheck="false" aria-describedby="summary-copy-help"></textarea></label><p id="summary-copy-help" class="field-help">Chọn và sao chép nội dung bên trên bằng chức năng của thiết bị.</p></div>`;
  const panel=(kind,title,description,entries=groups[kind])=>`<section class="card session-summary-group ${kind==='absent'&&earlyGroups?'session-summary-group-wide':''}" data-summary-group="${kind}" aria-labelledby="summary-${kind}-title"><div class="card-body"><h3 id="summary-${kind}-title" class="text-balance">${title} <span class="tabular-nums">${entries.length} em</span></h3><p class="field-help">${description}</p>${kind==='present'?copyActions:''}${roster(entries,kind)}</div></section>`;
  const extra=[['waiting','Chờ lễ bù'],['makeup','Đã đi lễ bù cho buổi khác'],['unrecorded','Chưa có kết quả ghi nhận']].filter(([kind])=>groups[kind].length);
  return `<section class="session-summary mt-6" aria-labelledby="session-summary-title">
    <div class="session-summary-heading"><h2 id="session-summary-title" class="text-balance">${closed?'Tổng kết buổi điểm danh':'Kết quả buổi điểm danh'}</h2><button type="button" class="button button-secondary" data-print-session-summary>In / Lưu PDF</button></div>
    <p class="text-pretty">${context?esc(context)+' · ':''}Danh sách theo kết quả đã lưu.</p>
    <p class="field-help" data-summary-print-status role="status" aria-live="polite"></p>
    <div class="session-summary-grid ${closed||earlyGroups?'':'session-summary-grid-open'}">${panel('present','Có mặt','Các em đã được ghi nhận có mặt trong buổi này.')}${earlyGroups?panel('early','Đi lễ sớm','Kết quả lễ sớm đã lưu cùng ngày và lớp. Thống kê riêng với danh sách Thánh lễ.',earlyGroups.present):''}${closed?panel('absent','Vắng',`${permitted} em nghỉ phép · ${groups.absent.length-permitted} em vắng không phép.`):''}</div>
    ${closed&&extra.length?`<aside class="card session-summary-followup"><div class="card-body"><h3 class="text-balance">Các em cần theo dõi riêng</h3><p class="field-help">Những em dưới đây chưa được tính vào danh sách có mặt hoặc vắng của buổi này.</p>${extra.map(([kind,title])=>`<details data-summary-group="${kind}"><summary>${title} <span class="tabular-nums">${groups[kind].length} em</span></summary>${roster(groups[kind],kind)}</details>`).join('')}</div></aside>`:''}
  </section>`;
}
