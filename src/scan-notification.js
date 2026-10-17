export function scanAnnouncement(feedback) {
  const s=feedback.student;
  return [feedback.title,s?`Mã số ${s.id}. Tên thánh ${s.saintName||'chưa có trong danh sách'}. Họ và tên ${s.fullName}. Lớp ${s.className}.`:'',feedback.description].filter(Boolean).join('. ');
}

export function scanBubbleHtml(feedback,{esc,i,classLevelKey}) {
  const s=feedback.student,kind=feedback.kind||'duplicate';
  const icon=kind==='error'?'info':kind==='pending'?'qr':kind==='warning'?'info':'checkcircle';
  return `<div class="scan-bubble-header"><span class="scan-bubble-icon" aria-hidden="true">${i(icon)}</span><h2 id="scan-bubble-title" class="text-balance">${esc(feedback.title)}</h2><button type="button" id="scan-bubble-close" class="icon-button" data-dismiss-scan-bubble aria-label="Đóng thông tin thiếu nhi vừa quét">${i('close')}</button></div>
  ${s?`<dl class="scan-bubble-details"><div><dt>Mã số</dt><dd class="tabular-nums">${esc(s.id)}</dd></div><div><dt>Tên thánh</dt><dd>${esc(s.saintName||'Chưa có trong danh sách')}</dd></div><div class="scan-bubble-full-name"><dt>Họ và tên</dt><dd>${esc(s.fullName)}</dd></div><div class="scan-bubble-class"><dt>Lớp</dt><dd><span class="class-pill" data-level="${esc(classLevelKey(s.className))}">${esc(s.className)}</span></dd></div></dl>`:''}
  <p class="scan-bubble-description text-pretty">${esc(feedback.description)}</p>`;
}
