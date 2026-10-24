export function scanAnnouncement(feedback) {
  const s=feedback.student;
  return [feedback.title,s?`Mã số ${s.id}. Tên thánh ${s._identityOnly?'xem khi có kết nối':s.saintName||'chưa có trong danh sách'}. Họ và tên ${s.fullName}. Lớp ${s.className}.`:'',feedback.description].filter(Boolean).join('. ');
}

export function scanBubbleHtml(feedback,{esc,i,classLevelKey}) {
  const s=feedback.student,kind=feedback.kind||'duplicate';
  const icon=kind==='error'?'info':kind==='pending'?'qr':kind==='warning'?'info':'checkcircle';
  return `<div class="scan-bubble-header"><span class="scan-bubble-icon" aria-hidden="true">${i(icon)}</span><h2 id="scan-bubble-title" class="text-balance">${esc(feedback.title)}</h2><button type="button" id="scan-bubble-close" class="icon-button" data-dismiss-scan-bubble aria-label="Đóng thông tin thiếu nhi vừa quét">${i('close')}</button></div>
  ${s?`<dl class="scan-bubble-details"><div><dt>Mã số</dt><dd class="tabular-nums">${esc(s.id)}</dd></div><div><dt>Tên thánh</dt><dd>${esc(s._identityOnly?'Xem khi có kết nối':s.saintName||'Chưa có trong danh sách')}</dd></div><div class="scan-bubble-full-name"><dt>Họ và tên</dt><dd>${esc(s.fullName)}</dd></div><div class="scan-bubble-class"><dt>Lớp</dt><dd><span class="class-pill" data-level="${esc(classLevelKey(s.className))}">${esc(s.className)}</span></dd></div></dl>`:''}
  <p class="scan-bubble-description text-pretty">${esc(feedback.description)}</p>`;
}

export function scanConfirmationHtml(candidate,{esc,i,classLevelKey,shortDate,activities}) {
  const {student:s,phase,feedback,proxy,session}=candidate;
  const waiting=phase==='lookup',saving=phase==='saving',ready=phase==='confirm',done=phase==='result';
  const title=waiting?'Đang đọc thẻ QR':ready?'Đã nhận diện thiếu nhi':feedback?.title||'Đang ghi nhận điểm danh';
  const description=waiting?'Đang tìm thông tin thiếu nhi. Chưa gửi điểm danh.':ready?
    proxy?'Em thuộc lớp khác. Bấm gửi để GLV của lớp nhận yêu cầu và duyệt điểm danh.':'Kiểm tra đúng tên em rồi bấm xác nhận để điểm danh.':feedback?.description||'Chờ hệ thống xác nhận kết quả.';
  return `<div class="scan-confirmation-heading"><span class="scan-bubble-icon" aria-hidden="true">${i(done&&feedback?.kind==='success'?'checkcircle':'qr')}</span><h2 id="scan-confirmation-title" class="text-balance">${esc(title)}</h2></div>
    ${s?`<p class="scan-confirmation-saint">${esc(s._identityOnly?'Thông tin chi tiết khi có kết nối':s.saintName||'Chưa có tên thánh')}</p><p class="scan-confirmation-name text-balance">${esc(s.fullName)}</p><div class="scan-confirmation-identity"><span class="class-pill" data-level="${esc(classLevelKey(s.className))}">${esc(s.className)}</span><span class="tabular-nums">${esc(s.id)}</span></div>`:`<p class="scan-confirmation-name tabular-nums">${esc(candidate.code)}</p>`}
    <p class="scan-confirmation-session">${esc(activities[session.activity])} · ${esc(shortDate(session.date))}</p>
    <p id="scan-confirmation-description" class="scan-bubble-description text-pretty" role="status" aria-live="polite">${esc(description)}</p>
    <div class="scan-confirmation-actions">${ready?`<button type="button" class="button button-secondary" data-cancel-scan>Hủy</button><button type="button" class="button button-primary" id="confirm-scanned-student" data-confirm-scan>${i(proxy?'arrow':'check')}${proxy?'Gửi điểm danh giùm':'Xác nhận điểm danh'}</button>`:saving?'<button type="button" class="button button-primary" disabled>Đang ghi nhận…</button>':`<button type="button" class="button ${done?'button-primary':'button-secondary'}" data-cancel-scan>${done?'Quét tiếp':'Hủy'}</button>`}</div>`;
}
