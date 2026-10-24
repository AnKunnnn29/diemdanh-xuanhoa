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

export function sessionSummaryHtml(groups,{esc,timeOf}) {
  const permitted=groups.absent.filter(({mark})=>mark.status==='P').length;
  const roster=(entries,kind)=>entries.length?`<ol class="session-summary-list">${entries.map(({student:s,mark},index)=>`<li>
    <span class="session-summary-number tabular-nums" aria-hidden="true">${index+1}</span>
    <div class="session-summary-person"><strong>${esc([s.saintName,s.fullName||s.name].filter(Boolean).join(' '))}</strong><small>${esc(s.className)} · <span class="tabular-nums">${esc(s.id)}</span></small></div>
    ${kind==='absent'?`<span class="status ${mark.status.toLowerCase()}">${mark.status==='P'?'Nghỉ phép':'Vắng không phép'}</span>`:kind==='present'&&mark?.timestamp?`<span class="session-summary-time tabular-nums">${esc(timeOf(mark.timestamp))}</span>`:''}
  </li>`).join('')}</ol>`:`<p class="session-summary-empty">${kind==='present'?'Chưa có em nào được ghi nhận có mặt.':'Không có em nào vắng trong buổi này.'}</p>`;
  const panel=(kind,title,description)=>`<section class="card session-summary-group" data-summary-group="${kind}" aria-labelledby="summary-${kind}-title"><div class="card-body"><h3 id="summary-${kind}-title" class="text-balance">${title} <span class="tabular-nums">${groups[kind].length} em</span></h3><p class="field-help">${description}</p>${roster(groups[kind],kind)}</div></section>`;
  const extra=[['waiting','Chờ lễ bù'],['makeup','Đã đi lễ bù cho buổi khác'],['unrecorded','Chưa có kết quả ghi nhận']].filter(([kind])=>groups[kind].length);
  return `<section class="session-summary mt-6" aria-labelledby="session-summary-title">
    <h2 id="session-summary-title" class="text-balance">Tổng kết buổi điểm danh</h2>
    <p class="text-pretty">Danh sách theo kết quả đã lưu của buổi đang xem.</p>
    <div class="session-summary-grid">${panel('present','Có mặt','Các em đã được ghi nhận có mặt trong buổi này.')}${panel('absent','Vắng',`${permitted} em nghỉ phép · ${groups.absent.length-permitted} em vắng không phép.`)}</div>
    ${extra.length?`<aside class="card session-summary-followup"><div class="card-body"><h3 class="text-balance">Các em cần theo dõi riêng</h3><p class="field-help">Những em dưới đây chưa được tính vào danh sách có mặt hoặc vắng của buổi này.</p>${extra.map(([kind,title])=>`<details data-summary-group="${kind}"><summary>${title} <span class="tabular-nums">${groups[kind].length} em</span></summary>${roster(groups[kind],kind)}</details>`).join('')}</div></aside>`:''}
  </section>`;
}
