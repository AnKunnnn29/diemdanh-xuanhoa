import {createYearUploadUI} from './year-upload-ui.js';
import {createPromotionUI} from './promotion-ui.js';
import {renderPrintWindow} from './print-window.js';
import {absenceStreak,monthSummary,csvText,lifecycleStatus} from './care-insights.js';
import {summarizeAttendance} from './attendance-metrics.js';
import {downloadResponse} from './cloud-download.js';

const weekdays=['Thứ Hai','Thứ Ba','Thứ Tư','Thứ Năm','Thứ Sáu','Thứ Bảy'];
const statuses={active:'Đang học',paused:'Tạm nghỉ',left:'Nghỉ học'};
const noteStatuses={open:'Cần xử lý',following:'Đang theo dõi',done:'Đã hoàn tất'};
const noteKinds={contact:'Liên hệ phụ huynh',visit:'Thăm hỏi',followup:'Theo dõi'};

export function createDevelopmentUI(ctx){
 const {esc,i,api,queueWrite,applyServer,render,today,shortDate,downloadBlob}=ctx;
 let system=null,systemLoading=false,recurringPlan=null,restorePlan=null,yearPlan=null;
 const promotionUI=createPromotionUI({esc,api,onChange:()=>{yearPlan=null;document.getElementById('year-preview')?.replaceChildren();}});let promotionEditor=null;
 const yearUploadUI=createYearUploadUI({api,esc});let yearUploadEditor=null;
 const state=()=>ctx.state(),people=()=>ctx.students(),classes=()=>ctx.classes();
 const personOptions=()=>people().map(s=>`<option value="${esc(s.id)}">${esc(s.name)} · ${esc(s.className)}</option>`).join('');
 const actorField=()=>`<label class="field">Tên người xác nhận<input name="actor" required minlength="2" maxlength="100" value="${esc(ctx.actor())}" aria-describedby="feature-error"></label>`;
 const reasonField=()=>`<label class="field">Lý do<textarea name="reason" required minlength="3" maxlength="500" rows="2" aria-describedby="feature-error"></textarea></label>`;
 const dialog=()=>document.getElementById('feature-dialog');
 function show(title,body,action){
  promotionUI.clear();promotionEditor=null;yearUploadUI.clear();yearUploadEditor=null;
  document.getElementById('feature-title').textContent=title;
  document.getElementById('feature-fields').innerHTML=action==='upload-year'?'<fieldset class="year-import-fields">'+body+'</fieldset>':body;
  document.getElementById('feature-error').textContent='';
  const form=document.getElementById('feature-form');form.dataset.action=action;
  document.getElementById('feature-submit').hidden=false;
  document.getElementById('feature-submit').textContent=action==='recurring'?'Xem trước lịch':action==='restore'?'Xem trước khôi phục':'Lưu xác nhận';
  dialog().showModal();form.querySelector('input:not([type=hidden]),select,textarea')?.focus();
 }
 function dialogs(){return `<dialog id="feature-dialog" aria-labelledby="feature-title"><form id="feature-form"><div class="dialog-heading"><h2 id="feature-title">Quản lý</h2><button type="button" class="icon-button" data-close-dialog aria-label="Đóng">${i('close')}</button></div><div id="feature-fields"></div><p id="feature-error" role="alert" tabindex="-1"></p><div class="dialog-actions"><button type="button" class="button button-secondary" data-close-dialog>Quay lại</button><button type="submit" class="button button-primary" id="feature-submit">Lưu xác nhận</button></div></form></dialog>`;}
 function recurringPanel(){
  const schedules=state().recurringMass||[];
  return `<section class="card mt-6"><div class="card-header"><h2>${i('calendar')}Lịch đổi lễ hằng tuần</h2><button class="button button-soft" data-feature="recurring">Thêm lịch hằng tuần</button></div><div class="card-body"><p class="field-help">Xác nhận lịch một lần cho khoảng ngày đã chọn. Mỗi buổi có một đơn riêng; dời riêng một buổi giữ lịch của các tuần sau.</p>${schedules.length?`<ul class="feature-list">${schedules.map(r=>{const s=people().find(s=>s.id===r.code);return `<li><div><strong>${esc(s?.name||r.code)}</strong><p>${weekdays[r.original_weekday]} → ${weekdays[r.target_weekday]} · ${shortDate(r.starts)} – ${shortDate(r.ends)}</p><small>${r.status==='active'?'Lịch đã xác nhận':'Đã dừng tạo lịch tương lai'} · ${esc(r.actor)}</small></div>${r.status==='active'?`<button class="button button-secondary" data-feature="stop-recurring" data-id="${r.id}">Dừng lịch</button>`:''}</li>`;}).join('')}</ul>`:'<p class="empty-state">Chưa có lịch hằng tuần. Các đơn đổi một buổi vẫn hoạt động bình thường.</p>'}</div></section>`;
 }
 function status(code,date=today()){return lifecycleStatus(state().studentStatuses||[],code,date);}
 function profileActions(s){return `<div class="feature-actions"><button type="button" class="button button-secondary" data-feature="status" data-code="${esc(s.id)}">${statuses[status(s.id)]} · Cập nhật</button><button type="button" class="button button-secondary" data-feature="print" data-code="${esc(s.id)}">${i('qr')}In lại thẻ QR</button><button type="button" class="button button-secondary" data-feature="transfer" data-code="${esc(s.id)}">Chuyển lớp</button></div>`;}
 function notesPanel(code=null){
  const visible=new Set((ctx.carePeople?.()||people()).map(s=>s.id));
  const notes=(state().careNotes||[]).filter(n=>code?n.code===code:visible.has(n.code));
  return `<section class="card mt-6"><div class="card-header"><h2>${i('heart')}Nhật ký đồng hành</h2><button type="button" class="button button-soft" data-feature="note" ${code?`data-code="${esc(code)}"`:''}>Thêm ghi chú</button></div><div class="card-body">${notes.length?`<ul class="feature-list">${notes.map(n=>`<li><div><strong>${esc(people().find(s=>s.id===n.code)?.name||n.code)} · ${noteKinds[n.kind]}</strong><p class="note-content">${esc(n.content)}</p><small>${noteStatuses[n.status]} · ${esc(n.actor)}${n.due_day?` · Hẹn ${shortDate(n.due_day)}${n.status!=='done'&&n.due_day<today()?' · Quá hẹn':''}`:''}</small></div><button type="button" class="button button-secondary" data-feature="note" data-id="${n.id}">Cập nhật</button></li>`).join('')}</ul>`:'<p class="field-help">Chưa có ghi chú. Nhật ký này được lưu cùng lịch sử web trong các bản sao lưu đầy đủ.</p>'}</div></section>`;
 }
 function insights(code=null){
  const codes=new Set(code?[code]:(ctx.carePeople?.()||people()).map(s=>s.id));
  const marks=Object.fromEntries(Object.entries(ctx.careMarks?.()||state().marks).filter(([k])=>codes.has(k.split('|')[2])));
  const months=monthSummary(marks);
  const maximum=Math.max(1,...months.map(m=>m.X+m.P+m.O));
  return `<section class="card mt-6"><div class="card-header"><h2>Chuyên cần theo tháng</h2></div><div class="card-body"><p class="field-help">Tổng lượt X / P / O từ sổ Excel; ô trống chưa tính. Lễ bù tính về tháng của ngày gốc.</p>${months.length?`<div class="month-bars" aria-hidden="true">${months.map(m=>`<div><span>${esc(m.month)}</span><div class="month-bar" style="width:${(m.X+m.P+m.O)/maximum*100}%"><b class="bar-present" style="flex:${m.X}"></b><b class="bar-permitted" style="flex:${m.P}"></b><b class="bar-absent" style="flex:${m.O}"></b></div></div>`).join('')}</div><div class="table-wrap"><table><caption class="sr-only">Số lượt chuyên cần từng tháng</caption><thead><tr><th scope="col">Tháng</th><th scope="col">Có mặt X</th><th scope="col">Có phép P</th><th scope="col">Vắng O</th></tr></thead><tbody>${months.map(m=>`<tr><th scope="row">${esc(m.month)}</th><td>${m.X}</td><td>${m.P}</td><td>${m.O}</td></tr>`).join('')}</tbody></table></div>`:'<p class="empty-state">Chưa có dữ liệu chuyên cần.</p>'}</div></section>`;
 }
 function alerts(){
  const list=(ctx.carePeople?.()||people()).map(s=>({s,mass:absenceStreak(state().marks,s.id,'mass',today()),lesson:absenceStreak(state().marks,s.id,'lesson',today())})).filter(r=>r.mass>=3||r.lesson>=3);
  return `<section class="card mt-6"><div class="card-header"><h2>Vắng liên tiếp cần quan tâm</h2><button class="button button-secondary" data-feature="care-export">${i('download')}Tải báo cáo CSV</button></div><div class="card-body"><p class="field-help">Từ 3 buổi vắng O liên tiếp trong các buổi đã ghi nhận, tính riêng lễ và giáo lý. X hoặc P ngắt chuỗi; ô trống không tính là vắng.</p>${list.length?`<ul class="feature-list">${list.map(({s,mass,lesson})=>`<li><div><strong>${esc(s.name)}</strong><p>${esc(s.className)} · Lễ ${mass} buổi · Giáo lý ${lesson} buổi</p></div><button class="button button-soft" data-feature="note" data-code="${esc(s.id)}">Ghi nhận chăm sóc</button></li>`).join('')}</ul>`:'<p>Chưa có em nào đạt ngưỡng cảnh báo này.</p>'}</div></section>`;
 }
 async function loadSystem(){
  if(systemLoading||!state().isManager)return;systemLoading=true;
  try{system=await api('system');}catch(error){system={error:error.message};}finally{systemLoading=false;render();}
 }
 function managementPage(){
  if(!state().isManager)return `<div class="page-heading"><div><h1>Sao lưu & năm học</h1><p>Mở mục này trên máy Excel để quản lý sao lưu và phục hồi.</p></div></div>`;
  if(!system&&!systemLoading)queueMicrotask(loadSystem);
  return `<div class="page-heading"><div><h1>Sao lưu & năm học</h1><p>Giữ sổ Excel, dữ liệu nghiệp vụ, tài khoản, phân quyền và các năm học.</p></div><button class="button button-secondary" data-feature="refresh-system">Làm mới</button></div>${system?.error?`<p role="alert">${esc(system.error)}</p>`:''}<section class="card"><div class="card-header"><h2>${i('file')}Sao lưu đầy đủ</h2><button class="button button-primary" data-feature="snapshot">Tạo bản sao ngay</button></div><div class="card-body"><p>Nơi lưu dữ liệu: <strong class="path-text">${esc(system?.dataRoot||'Đang đọc…')}</strong></p><p class="field-help">${state().mode==='cloud'?'Dữ liệu được lưu riêng trên Supabase; sử dụng qua Wi-Fi hoặc 4G mà không cần bật máy cá nhân.':`${system?.localFiles??'…'} file lớp có sẵn trên máy. Trạng thái OneDrive/Google Drive chưa được xác minh; kiểm tra ứng dụng đồng bộ trên máy.`}</p><form id="backup-settings-form" class="feature-actions"><label class="field">${state().mode==='cloud'?'Chu kỳ sao lưu khi có cập nhật dữ liệu':'Sao lưu định kỳ khi dịch vụ chạy'}<select name="hours">${[[0,'Tắt'],[12,'Mỗi 12 giờ'],[24,'Mỗi 24 giờ'],[168,'Mỗi 7 ngày']].map(([h,t])=>`<option value="${h}" ${h===system?.backupHours?'selected':''}>${t}</option>`).join('')}</select></label><button class="button button-secondary" type="submit">Lưu lịch sao lưu</button></form><p id="management-message" role="status" aria-live="polite">${esc(system?.lastBackupError||'')}</p>${system?.snapshots?.length?`<ul class="feature-list">${system.snapshots.map(s=>`<li><div><strong>${esc(s.label)}</strong><p>${esc(s.stamp.slice(0,19).replace('T',' '))} · ${s.count} lớp · ${esc(s.actor)}</p></div><div class="feature-actions"><button class="button button-secondary" ${state().mode==='cloud'?'disabled title="Dùng công cụ backup mã hóa riêng"':''} data-feature="download-snapshot" data-id="${s.id}">Tải ZIP</button><button class="button button-text" data-feature="restore" data-id="${s.id}">Xem khôi phục</button></div></li>`).join('')}</ul>`:'<p class="field-help">Chưa có bản sao đầy đủ. Bản sao từng file trước mỗi lần ghi vẫn được giữ.</p>'}</div></section><section class="card mt-6"><div class="card-header"><h2>Chuẩn bị năm học mới</h2></div><div class="card-body"><p><a href="#administration">Xem lịch sử, chuyển năm làm việc và khôi phục tài khoản →</a></p><p>Chuẩn bị danh sách và lịch năm mới trong các sổ lớp Excel, rồi tải lên để kiểm tra và tạo năm học mới. Năm hiện tại được giữ nguyên.</p><div class="feature-actions"><button class="button button-secondary" data-feature="archive">Lưu trữ năm hiện tại</button><button class="button button-primary" data-feature="upload-year" ${state().mode==='cloud'?'':'disabled title="Tải sổ năm mới trên website cloud"'}>Tải sổ Excel năm mới</button></div>${(state().yearPlans||[]).length?`<ul class="feature-list">${state().yearPlans.map(p=>`<li><div><strong>${p.start_year}–${p.start_year+1} · ${p.status==='prepared'?'Đã tạo Excel':'Bản dự thảo'}</strong><p>${esc(p.actor)} · ${esc(p.reason)}</p></div><span>Bản đề xuất cũ được giữ lại; xét lên lớp trên web đang tạm ngưng.</span>${p.export_id?`<button class="button button-secondary" data-feature="download-year" data-id="${p.export_id}">Tải bộ Excel năm mới</button>`:''}</li>`).join('')}</ul>`:''}</div></section>`;
 }
 function recurrenceForm(){
  recurringPlan=null;show('Đổi lễ hằng tuần',`<label class="field">Thiếu nhi<select name="code" required>${personOptions()}</select></label><div class="dialog-fields"><label class="field">Thứ lễ gốc<select name="originalWeekday">${weekdays.map((t,v)=>`<option value="${v}" ${v===1?'selected':''}>${t}</option>`).join('')}</select></label><label class="field">Thứ đi thay thế<select name="targetWeekday">${weekdays.map((t,v)=>`<option value="${v}">${t}</option>`).join('')}</select></label><label class="field">Từ ngày<input type="date" name="startDate" value="${today()}" required></label><label class="field">Đến ngày<input type="date" name="endDate" value="${classes().flatMap(c=>c.calendar.mass).sort().at(-1)||today()}" required></label></div>${actorField()}${reasonField()}<div id="recurring-preview" aria-live="polite"></div>`,'recurring');
 }
 function noteForm(code,id){
  const n=(state().careNotes||[]).find(n=>n.id===id);
  show(n?'Cập nhật đồng hành':'Ghi nhận đồng hành',`${n?`<input type="hidden" name="id" value="${n.id}">`:''}<label class="field">Thiếu nhi<select name="code" required>${people().map(s=>`<option value="${s.id}" ${s.id===(n?.code||code)?'selected':''}>${esc(s.name)} · ${esc(s.className)}</option>`).join('')}</select></label><label class="field">Hoạt động<select name="kind">${Object.entries(noteKinds).map(([v,t])=>`<option value="${v}" ${v===n?.kind?'selected':''}>${t}</option>`).join('')}</select></label><label class="field">Nội dung<textarea name="content" required minlength="3" maxlength="500" rows="3" aria-describedby="feature-error">${esc(n?.content||'')}</textarea></label><div class="dialog-fields"><label class="field">Hẹn theo dõi<input type="date" name="dueDate" value="${esc(n?.due_day||'')}"></label><label class="field">Tình hình<select name="status">${Object.entries(noteStatuses).map(([v,t])=>`<option value="${v}" ${v===n?.status?'selected':''}>${t}</option>`).join('')}</select></label></div>${actorField()}${n?`<details><summary>Lịch sử cập nhật</summary><ul class="feature-list">${(state().managementEvents||[]).filter(e=>e.entity==='care'&&e.entity_id===n.id).map(e=>`<li><div><strong>${esc(e.actor)}</strong><p>${esc(e.reason)}</p><small>${esc(e.stamp)}</small></div></li>`).join('')}</ul></details>`:''}`,'note');
 }
 async function printCards(code=null,className='all'){
  const list=people().filter(s=>code?s.id===code:className==='all'||s.className===className);
  const win=window.open('/print.html','_blank');if(!win)throw new Error('Cho phép mở cửa sổ in trên trình duyệt.');
  win.opener=null;
  await renderPrintWindow(win,`<!doctype html><html lang="vi"><meta charset="utf-8"><title>Thẻ QR · Giáo Xứ Xuân Hoà</title><style>body{font:16px system-ui;margin:20px;color:#111}main{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.card{border:1px solid #999;padding:12px;text-align:center;break-inside:avoid}.card img{display:block;width:140px;height:140px;margin:auto}.card p{margin:4px;overflow-wrap:anywhere}button{padding:12px;font:inherit} @media print{button,header{display:none}body{margin:0}main{grid-template-columns:repeat(3,1fr)}}@media(max-width:600px){main{grid-template-columns:repeat(2,1fr)}}</style><header><h1>Thẻ QR thiếu nhi</h1><p>${list.length} thẻ · In hoặc chọn “Lưu dưới dạng PDF”. In lại giữ nguyên mã đã cấp.</p><button id="print" disabled>In / Lưu PDF</button></header><main>${list.map(s=>`<article class="card"><strong>Giáo Xứ Xuân Hoà</strong><img src="${location.origin}/api/qr?code=${encodeURIComponent(s.id)}" alt="QR ${esc(s.id)}"><p>${esc(s.saintName)}</p><p><b>${esc(s.fullName)}</b></p><p>${esc(s.className)}</p><p><b>${esc(s.id)}</b></p></article>`).join('')}</main></html>`);

 }
 async function careExport(){
  const metrics=summarizeAttendance(ctx.carePeople?.()||people(),ctx.careMarks?.()||state().marks);
  const rows=[['Mã','Tên thánh','Họ tên','Lớp','Có mặt X','Có phép P','Vắng O','Tỷ lệ %','Vắng lễ liên tiếp','Vắng giáo lý liên tiếp']];
  for(const r of metrics)rows.push([r.student.id,r.student.saintName,r.student.fullName,r.student.className,r.presentCount,r.permittedCount,r.absentCount,r.ratio??'',absenceStreak(state().marks,r.student.id,'mass',today()),absenceStreak(state().marks,r.student.id,'lesson',today())]);
  downloadBlob(csvText(rows),`ChuyenCan-${today()}.csv`,'text/csv;charset=utf-8');
 }
 async function binaryDownload(path,filename){const r=await fetch('/api/'+path,{cache:'no-store'});await downloadResponse(r,filename,downloadBlob,text=>{const message=document.getElementById('management-message');if(message)message.textContent=text;});const message=document.getElementById('management-message');if(message)message.textContent='Đã tải đầy đủ gói file.';}
 async function execute(action,values){
  if(action==='upload-year'){
   let result;
   try{result=await yearUploadEditor.submit(values);}catch(error){if(error.status===409)yearUploadEditor?.invalidate();throw error;}
   if(!result)return;
   applyServer(result.state);ctx.onYearPrepared?.();ctx.toast(`Đã chuẩn bị năm học ${result.year}: ${result.classes} lớp, ${result.count} em. Năm hiện tại vẫn được sử dụng.`);
  }else if(action==='recurring'){
   const payload={...values,originalWeekday:Number(values.originalWeekday),targetWeekday:Number(values.targetWeekday)};
   if(!recurringPlan){
    recurringPlan=await api('recurring-preview',payload);
    document.getElementById('recurring-preview').innerHTML=`<p><strong>${recurringPlan.occurrences.length} buổi phù hợp</strong> · Chưa tạo đơn, chưa đánh có mặt.</p>${recurringPlan.issues.length?`<ul>${recurringPlan.issues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}<ol class="feature-list">${recurringPlan.occurrences.map(o=>`<li>${shortDate(o.date)} → ${shortDate(o.targetDate)}</li>`).join('')}</ol>`;
    document.getElementById('feature-submit').textContent=recurringPlan.issues.length?'Xem trước lại':'Xác nhận lịch đã duyệt';
    if(recurringPlan.issues.length)recurringPlan=null;
    return;
   }
   const r=await api('recurring-mass',{...payload,previewToken:recurringPlan.token});applyServer(r.state);ctx.toast(`Đã tạo ${r.count} đơn theo lịch hằng tuần.`);
  }else if(action==='restore'){
   if(!restorePlan){restorePlan=await api('restore-preview',values);document.getElementById('restore-preview').innerHTML=`<p><strong>Khôi phục toàn bộ ${restorePlan.count} lớp</strong> về ${esc(restorePlan.stamp.slice(0,19))}. Excel, đơn từ, buổi chốt và ghi chú đều được thay bằng bản sao này. Tài khoản và mật khẩu hiện tại được giữ nguyên. Hệ thống tạo bản sao hiện tại trước khi phục hồi.</p>${restorePlan.removedFiles?.length?`<p>File lớp hiện tại sẽ bỏ:</p><ul>${restorePlan.removedFiles.map(f=>`<li>${esc(f)}</li>`).join('')}</ul>`:''}${restorePlan.addedFiles?.length?`<p>File lớp sẽ khôi phục thêm:</p><ul>${restorePlan.addedFiles.map(f=>`<li>${esc(f)}</li>`).join('')}</ul>`:''}<label class="field">Nhập KHÔI PHỤC để xác nhận<input name="confirmation" required pattern="KHÔI PHỤC" aria-describedby="feature-error"></label>`;document.getElementById('feature-submit').textContent='Khôi phục toàn bộ';return;}
   const r=await api('restore',{...values,previewToken:restorePlan.token});if(r.requireReauth){dialog().close();ctx.toast('Đã khôi phục dữ liệu. Đăng nhập lại để tiếp tục.');ctx.reauthenticate();return;}applyServer(r.state);system=r.system;ctx.toast('Đã khôi phục Excel và dữ liệu web.');
  }else if(action==='snapshot'||action==='archive'){
   const r=await api('snapshot',{...values,label:action==='archive'?'Lưu trữ năm học '+document.querySelector('.year-card strong').textContent:values.reason});system=r.system;ctx.toast('Đã sao lưu Excel, dữ liệu web, tài khoản và các năm học.');
  }else if(action==='promotion'){
   const placements=promotionEditor.placements();
   const payload={startYear:Number(values.startYear),placements,actor:values.actor,reason:values.reason};
   if(values._intent==='preview'){
    yearPlan=await api('year-preview',payload);document.getElementById('year-preview').innerHTML=`<p>${yearPlan.issues.length?`${yearPlan.issues.length} mục cần xử lý`:'Đủ điều kiện tạo bộ Excel mới'}.</p><ul>${yearPlan.issues.slice(0,20).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;return;
   }else if(values._intent==='export'){
    const rows=[['Mã','Tên thánh','Họ tên','Lớp hiện tại','Lớp đề xuất','Duyệt']];
    for(const s of people()){const p=placements.find(p=>p.code===s.id);rows.push([s.id,s.saintName,s.fullName,s.className,classes().find(c=>c.id===p.classId)?.name||(p.classId==='graduate'?'Kết thúc chương trình':''),p.approved?'Đã duyệt':'Chưa duyệt']);}
    downloadBlob(csvText(rows),`DeXuatLenLop-${today()}.csv`,'text/csv;charset=utf-8');return;
   }else if(values._intent==='build'){
    if(!yearPlan||yearPlan.issues.length)throw new Error('Xem trước và xử lý các trường hợp còn chờ trước khi tạo năm mới.');
    const r=await api('prepare-year',{...payload,previewToken:yearPlan.token});applyServer(r.state);ctx.toast('Đã tạo bộ năm mới riêng. Năm hiện tại tiếp tục được sử dụng.');
   }else{const r=await api('year-plan',payload);applyServer(r.state);ctx.toast('Đã lưu dự thảo lên lớp.');}
  }else if(action==='transfer'){
   const payload={...values};
   if(!recurringPlan){recurringPlan=await api('transfer-preview',payload);document.getElementById('transfer-preview').innerHTML=`<p>${esc(recurringPlan.description)}</p>${recurringPlan.issues.length?`<ul>${recurringPlan.issues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p>Đã kiểm tra sức chứa, mã và lịch. Bản sao đầy đủ được tạo trước khi chuyển.</p>'}`;document.getElementById('feature-submit').textContent=recurringPlan.issues.length?'Xem lại':'Xác nhận chuyển lớp';if(recurringPlan.issues.length)recurringPlan=null;return;}
   const r=await api('transfer',{...payload,previewToken:recurringPlan.token});applyServer(r.state);ctx.toast('Đã chuyển lớp và giữ mã, hồ sơ, điểm, chuyên cần.');
  }else{
   const path={note:'care-note',status:'student-status','stop-recurring':'recurring-stop'}[action];
   const r=await api(path,values);applyServer(r.state);ctx.toast('Đã lưu và cập nhật trên web.');
  }
  ctx.rememberActor(values.actor||ctx.actor());dialog().close();render();
 }
 document.addEventListener('submit',event=>{
  if(event.target.getAttribute('id')==='feature-form'){
   event.preventDefault();const form=event.target,button=document.getElementById('feature-submit');button.disabled=true;form.setAttribute('aria-busy','true');document.getElementById('feature-error').textContent='Đang xử lý…';
   const values={...Object.fromEntries(new FormData(form)),_intent:event.submitter?.value};const uploadBusy=form.dataset.action==='upload-year';if(uploadBusy){form.querySelector('.year-import-fields').disabled=true;form.querySelectorAll('[data-close-dialog]').forEach(b=>b.disabled=true);}
   form.querySelectorAll('button[type=submit]').forEach(b=>b.disabled=true);
   queueWrite(async()=>{try{await execute(form.dataset.action,values);document.getElementById('feature-error').textContent='';}catch(error){document.getElementById('feature-error').textContent=error.message;if(form.dataset.action==='restore'){restorePlan=null;document.getElementById('restore-preview').innerHTML='';document.getElementById('feature-submit').textContent='Xem trước khôi phục';}if(['recurring','transfer'].includes(form.dataset.action)){recurringPlan=null;document.getElementById('feature-submit').textContent='Xem trước lại';}}finally{form.querySelectorAll('button[type=submit]').forEach(b=>b.disabled=false);form.removeAttribute('aria-busy');if(uploadBusy){const fields=form.querySelector('.year-import-fields');if(fields)fields.disabled=false;form.querySelectorAll('[data-close-dialog]').forEach(b=>b.disabled=false);}}});
  }else if(event.target.getAttribute('id')==='backup-settings-form'){
   event.preventDefault();const form=event.target,button=form.querySelector('button');button.disabled=true;
   queueWrite(async()=>{try{const r=await api('backup-settings',{hours:Number(new FormData(form).get('hours'))});system=r.system;render();document.getElementById('management-message').textContent='Đã lưu lịch sao lưu.';}catch(e){document.getElementById('management-message').textContent=e.message;}finally{button.disabled=false;}});
  }
 });
 document.addEventListener('input',event=>{if(event.target.closest('#feature-form')&&!event.target.matches('[name=confirmation]')){if(['recurring','transfer'].includes(event.target.closest('form').dataset.action)&&recurringPlan){recurringPlan=null;document.getElementById('feature-submit').textContent='Xem trước lại';}event.target.removeAttribute('aria-invalid');}});
 document.addEventListener('change',event=>{if(event.target.closest('#feature-form')){if(['recurring','transfer'].includes(event.target.closest('form').dataset.action)){recurringPlan=null;document.getElementById('feature-submit').textContent='Xem trước lại';}if(event.target.closest('form').dataset.action==='promotion'&&!event.target.hasAttribute('data-promotion-filter'))yearPlan=null;}});
 document.addEventListener('click',async event=>{
  const b=event.target.closest('[data-feature]');if(!b)return;
  const action=b.dataset.feature,code=b.dataset.code,id=b.dataset.id;
  try{
   if(action==='promotion'){ctx.toast('Tự động xét lên lớp đang tạm ngưng. Chuẩn bị sổ Excel năm mới để tải lên.');return;}
   if(action==='upload-year'){
    if(!state().isManager){ctx.toast('Chuẩn bị năm học dành cho Admin.');return;}
    show('Tải sổ Excel năm học mới',`<label class="field">Năm bắt đầu<input name="startYear" type="number" min="${Number(document.querySelector('.year-card strong').textContent.slice(0,4))+1}" max="2099" required value="${Number(document.querySelector('.year-card strong').textContent.slice(0,4))+1}"></label><details><summary>Thêm ghi chú (tuỳ chọn)</summary><label class="field">Ghi chú<textarea name="reason" maxlength="500" rows="2"></textarea></label></details><div id="year-upload-editor"></div>`,'upload-year');
    yearUploadEditor=yearUploadUI.mount(document.getElementById('year-upload-editor'));
    dialog().addEventListener('close',()=>yearUploadUI.clear(),{once:true});return;
   }

   if(action==='recurring')recurrenceForm();
   else if(action==='note')noteForm(code,id);
   else if(action==='status')show('Trạng thái học giáo lý',`<input type="hidden" name="code" value="${esc(code)}"><p>Giữ nguyên mã và dữ liệu lịch sử. Tạm nghỉ/nghỉ học không thuộc danh sách chốt từ ngày hiệu lực.</p><label class="field">Trạng thái<select name="status">${Object.entries(statuses).map(([v,t])=>`<option value="${v}" ${v===status(code)?'selected':''}>${t}</option>`).join('')}</select></label><label class="field">Từ ngày<input name="effectiveDate" type="date" required min="${today()}" value="${today()}"></label>${actorField()}${reasonField()}`,'status');
   else if(action==='stop-recurring')show('Dừng lịch tương lai',`<input type="hidden" name="id" value="${esc(id)}"><p>Huỷ các đơn chưa hoàn thành từ ngày đã chọn. Buổi đã đi, vắng hoặc có ngoại lệ trước ngày này được giữ nguyên.</p><label class="field">Dừng từ ngày<input type="date" name="effectiveDate" value="${today()}" min="${today()}" required></label>${actorField()}${reasonField()}`,'stop-recurring');
   else if(action==='print')await printCards(code,ctx.studentFilter());
   else if(action==='care-export')await careExport();
   else if(action==='grade-progress'){
    const s=people().find(s=>s.id===code);ctx.toast('Đang đọc điểm từ Excel…');
    const [one,two]=await Promise.all([api(`grades?classId=${s.classId}&semester=1`),api(`grades?classId=${s.classId}&semester=2`)]);
    const rows=[one,two].map((data,index)=>({semester:index+1,row:data.students.find(r=>r.code===code)}));
    show('Điểm học tập từ Excel',`<p>${esc(s.name)} · ${esc(s.className)}</p><div class="table-wrap"><table><thead><tr><th scope="col">Học kỳ</th><th scope="col">Điểm TB</th><th scope="col">Xếp loại</th><th scope="col">Xếp hạng</th></tr></thead><tbody>${rows.map(({semester,row})=>`<tr><th scope="row">HK${semester}</th><td>${esc(row?.tbHk??'Chưa có điểm')}</td><td>${esc(row?.xepLoai||'—')}</td><td>${esc(row?.xepHang??'—')}</td></tr>`).join('')}</tbody></table></div><p class="field-help">Công thức và xếp loại do Excel tính. Ô trống không coi là điểm 0.</p>`,'read-only');document.getElementById('feature-submit').hidden=true;
   }
   else if(action==='refresh-system'){system=null;loadSystem();}
   else if(action==='snapshot'||action==='archive')show(action==='archive'?'Lưu trữ năm học hiện tại':'Sao lưu đầy đủ',`${actorField()}${reasonField()}`,action);
   else if(action==='download-snapshot')await binaryDownload('snapshot-export?id='+encodeURIComponent(id),`XuanHoa-${id}.zip`);
   else if(action==='download-year')await binaryDownload('year-export?id='+encodeURIComponent(id),`XuanHoa-NamHoc-${id}.zip`);
   else if(action==='restore'){restorePlan=null;show('Xem trước khôi phục',`<input type="hidden" name="id" value="${esc(id)}">${actorField()}${reasonField()}<div id="restore-preview" aria-live="polite"></div>`,'restore');}
   else if(action==='transfer'){
    if(!state().isManager){ctx.toast('Chuyển lớp trên máy Excel.');return;}
    recurringPlan=null;show('Chuyển lớp',`<input name="code" type="hidden" value="${esc(code)}"><p>Chuyển cả sổ năm hiện tại, giữ nguyên mã. Lịch sử web vẫn theo mã này.</p><label class="field">Lớp đích<select name="classId" required>${classes().filter(c=>c.id!==people().find(s=>s.id===code)?.classId).map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label>${actorField()}${reasonField()}<div id="transfer-preview" aria-live="polite"></div>`,'transfer');
   }else if(action==='promotion'){
    yearPlan=null;const old=state().yearPlans?.find(p=>p.id===id),placements=old?JSON.parse(old.placements):[];
    show('Xét lên lớp năm học mới',`<label class="field">Năm bắt đầu<input name="startYear" type="number" min="${Number(document.querySelector('.year-card strong').textContent.slice(0,4))+1}" max="2099" required value="${old?.start_year||Number(document.querySelector('.year-card strong').textContent.slice(0,4))+1}"></label>${actorField()}${reasonField()}<div id="promotion-editor"></div><div id="year-preview" aria-live="polite"></div><div class="feature-actions"><button type="submit" class="button button-secondary" value="export">Tải CSV</button><button type="submit" class="button button-secondary" value="preview">Xem trước</button><button type="submit" class="button button-primary" value="build">Tạo bộ Excel năm mới</button></div>`,'promotion');
    promotionEditor=promotionUI.mount(document.getElementById('promotion-editor'),{students:people(),classes:classes(),saved:placements});
    dialog().addEventListener('close',()=>promotionUI.clear(),{once:true});
    document.getElementById('feature-submit').textContent='Lưu dự thảo';
   }
  }catch(error){ctx.toast(error.message);}
 });
 return {clear:()=>{yearUploadUI.clear();yearUploadEditor=null;promotionUI.clear();promotionEditor=null;system=null;systemLoading=false;recurringPlan=null;restorePlan=null;yearPlan=null;},dialogs,recurringPanel,profileActions,notesPanel,insights,alerts,managementPage,status};
}
