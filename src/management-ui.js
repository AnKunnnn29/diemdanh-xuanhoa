import {matchesSearch} from './ux-utils.js';
const tabs={classes:'Quản lý lớp',import:'Nhập danh sách',staff:'Hồ sơ GLV',audit:'Nhật ký',years:'Năm học',access:'Sao lưu & truy cập'};
const staffStates={active:'Đang phục vụ',paused:'Tạm nghỉ',retired:'Ngưng phục vụ'};
const reminderKinds={requests:'Đơn chờ duyệt',sessions:'Buổi chưa chốt',care:'Theo dõi đến hạn',grades:'Thiếu điểm',system:'Quản lý hệ thống'};

export function createManagementUI(ctx){
 const {esc,api,queueWrite,render,applyServer,toast}=ctx;
 let tab='classes',busy=false,error='',epoch=0,loaded={},data={},plan=null,previewValues=null,drafts={},importFile=null;
 let editingStaff=null,editingClass=null,auditQuery={},history=null,notification=null,notificationLoading=false,staffQuery='';
 const staffDialog=document.createElement('dialog');
 staffDialog.id='staff-profile-dialog';staffDialog.className='management-console staff-editor';
 staffDialog.setAttribute('aria-labelledby','staff-editor-title');document.body.append(staffDialog);
 let staffOpenerId=null;
 function focusStaffOpener(){
  const candidates=[...document.querySelectorAll(`[data-admin-action="${staffOpenerId?'edit-staff':'new-staff'}"]`)];
  (candidates.find(el=>(!staffOpenerId||el.dataset.id===staffOpenerId)&&el.getClientRects().length)||document.getElementById('staff-search'))?.focus({preventScroll:true});
 }
 staffDialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
 staffDialog.addEventListener('close',()=>{editingStaff=null;delete drafts['admin-staff-form'];error='';focusStaffOpener();});
 const classes=()=>ctx.classes(),state=()=>ctx.state();
 const button=(text,action,extra='')=>`<button type="button" class="button button-secondary" data-admin-action="${action}" ${extra}>${text}</button>`;
 const field=(title,name,type='text',value='',extra='')=>`<label class="field">${title}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
 const reason=()=>`<label class="field">Lý do thực hiện<textarea name="reason" minlength="3" maxlength="500" rows="2" required></textarea></label>`;
 const classOptions=(value='')=>classes().map(c=>`<option value="${esc(c.id)}" ${c.id===value?'selected':''}>${esc(c.name)}${c.archived?' · Đã lưu trữ':''}</option>`).join('');
 const json=(value)=>`<pre class="admin-json">${esc(JSON.stringify(value,null,2))}</pre>`;
 function clear(){epoch++;loaded={};data={};plan=null;previewValues=null;history=null;notification=null;busy=false;error='';notificationLoading=false;editingStaff=null;editingClass=null;drafts={};importFile=null;staffQuery='';staffDialog.close();staffDialog.replaceChildren();}
 function restoreDrafts(){for(const [id,values] of Object.entries(drafts)){const form=document.getElementById(id);if(!form)continue;for(const [name,value] of Object.entries(values)){const input=form.elements[name];if(input&&input.type!=='file'&&input.type!=='checkbox')input.value=value;}}if(importFile&&document.getElementById('admin-import-form')){const transfer=new DataTransfer();transfer.items.add(importFile);document.getElementById('admin-import-form').elements.file.files=transfer.files;}}
 async function load(name=tab){
  const stamp=epoch;busy=true;error='';
  try{
   if(name==='staff')data.staff=await api('admin/staff');
   if(name==='audit')data.audit=await api('admin/audit?'+new URLSearchParams(auditQuery));
   if(name==='years')data.years=await api('admin/years');
   if(name==='access')data.system=await api('system');
   if(stamp!==epoch)return;
   loaded[name]=true;
  }catch(e){if(stamp===epoch)error=e.message;}
  finally{if(stamp===epoch){busy=false;render();}}
 }
 function table(headers,rows,caption){return `<div class="table-scroll"><table><caption>${caption}</caption><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${headers.length}">Chưa có dữ liệu.</td></tr>`}</tbody></table></div>`;}
 function classPage(){
  const value=editingClass||{};
  return `<section class="card"><h2>Danh sách lớp</h2><p>Lưu trữ lớp sẽ giữ lịch sử và ngừng các thao tác điểm danh, nhập điểm. Mở lại lớp để tiếp tục làm việc.</p>${table(['Lớp','Sĩ số','Trạng thái','Thao tác'],classes().map(c=>`<tr><td>${esc(c.name)}</td><td>${c.count}/40</td><td>${c.archived?'Đã lưu trữ':'Đang hoạt động'}</td><td>${button('Chỉnh sửa','edit-class',`data-id="${esc(c.id)}"`)}</td></tr>`),'Các lớp trong năm làm việc')}</section>
   <section class="card"><h2>${value.id?'Chỉnh sửa lớp':'Tạo lớp hoặc cập nhật lớp'}</h2><form id="admin-class-form" class="admin-form">
    <label class="field">Thao tác<select name="operation"><option value="create">Tạo lớp mới từ bản mẫu</option><option value="rename" ${value.id?'selected':''}>Đổi tên lớp</option><option value="archive">Lưu trữ lớp</option><option value="reopen">Mở lại lớp</option></select></label>
    <label class="field">Lớp / bản mẫu<select name="classId">${classOptions(value.id)}</select></label>${field('Tên lớp (khối và số/tên lớp)','name','text',value.name||'','maxlength="80"')}${reason()}
    <p class="field-help">Lớp mới giữ lịch, công thức và macro của bản mẫu; danh sách và điểm được làm trống. Đổi tên giữ mã lớp và phân quyền.</p><button class="button button-primary" type="submit">Xem trước thay đổi</button></form></section>${previewPanel('class-save')}`;
 }
 function previewPanel(action){
  if(!plan)return '';
  if(action==='import-save')return `<section class="card admin-preview"><h2>Xem trước danh sách nhập (${plan.rows.length} em)</h2>${messages(plan.issues,'Lỗi cần sửa')}${messages(plan.warnings,'Hồ sơ cần kiểm tra')}${table(['Mã','Họ tên','Lớp','Nhập học'],plan.rows.map(r=>`<tr><td>${esc(r.code)}</td><td>${esc(r.saintName)} ${esc(r.fullName)}</td><td>${esc(classes().find(c=>c.id===r.classId)?.name)}</td><td>${esc(r.enrolledFrom)}</td></tr>`),'Các hồ sơ sẽ thêm')}
   ${plan.warnings.length?'<label class="admin-check"><input type="checkbox" id="import-accept-warnings">Tôi đã kiểm tra các hồ sơ có thể trùng.</label>':''}${button('Nhập toàn bộ danh sách',action,plan.issues.length?'disabled':'')}<p class="field-help">Tất cả dòng hợp lệ mới được ghi. Hệ thống tạo bản sao trước khi nhập.</p></section>`;
  if(action==='class-save')return `<section class="card admin-preview"><h2>Xác nhận thay đổi lớp</h2><p>${esc({create:'Tạo lớp mới',rename:'Đổi tên lớp',archive:'Lưu trữ lớp',reopen:'Mở lại lớp'}[plan.operation])}: <strong>${esc(plan.name)}</strong> · ${plan.count} em trong lớp/bản mẫu.</p>${button('Xác nhận thực hiện',action)}<p class="field-help">Sao lưu được tạo trước khi thay đổi.</p></section>`;
  return '';
 }
 const messages=(items,title)=>items?.length?`<div class="admin-message"><strong>${title}</strong><ul>${items.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></div>`:'';
 function importPage(){return `<section class="card"><h2>Nhập hồ sơ thiếu nhi</h2><p>Dùng mã thẻ đã được xác nhận cấp. Mã đang dùng hoặc đã có lịch sử sẽ bị từ chối.</p><a class="button button-secondary" href="/api/admin/import-template">Tải file mẫu CSV</a>
  <form id="admin-import-form" class="admin-form"><label class="field">Lớp mặc định<select name="classId">${classOptions()}</select></label><label class="field">File Excel .xlsx, CSV hoặc TSV<input type="file" name="file" accept=".xlsx,.csv,.tsv,.txt"></label><label class="field">Hoặc dán bảng CSV / TSV<textarea name="text" rows="7" spellcheck="false" placeholder="code,fullName,enrolledFrom\nXH…,Họ tên,2026-09-01"></textarea></label>${reason()}<p class="field-help">Tối đa 800 dòng, 2 MB; mỗi lớp tối đa 40 em. Định dạng ngày yyyy-mm-dd hoặc dd/mm/yyyy. Giữ số điện thoại ở dạng văn bản trong Excel. Cột classId có thể là mã hoặc tên lớp; bỏ trống để dùng lớp mặc định.</p><button type="submit" class="button button-primary">Kiểm tra & xem trước</button></form></section>${previewPanel('import-save')}`;}
 const birthLabel=p=>p.birth_date?p.birth_date.split('-').reverse().join('/'):(p.birth_year?'Năm '+p.birth_year:'Chưa cập nhật');
 const phoneLink=phone=>phone?`<a class="staff-phone" href="tel:${esc(phone.replace(/[^+\d]/g,''))}">${esc(phone)}</a>`:'Chưa cập nhật';
 function filterStaff(){
  let count=0;
  document.querySelectorAll('[data-staff-record]').forEach(row=>{row.hidden=!matchesSearch(row.dataset.staffSearch,staffQuery);if(!row.hidden&&row.tagName==='TR')count++;});
  const result=document.getElementById('staff-search-results');if(result)result.textContent=`${count} hồ sơ`;
 }
 function staffPage(){
  const model=data.staff;if(!model)return loading();
  const account=p=>model.accounts.find(a=>a.id===p.user_id);
  const role=p=>model.accounts.find(a=>a.id===p.user_id)?.role||'Chưa liên kết';
  const search=p=>esc([p.full_name,p.phone,p.birth_year||'',p.birth_date,account(p)?.username].join(' '));
  const identity=p=>`<strong>${esc(p.full_name)}</strong><small class="staff-account">${esc(account(p)?.username||'Chưa liên kết')}<span>${esc(role(p))}</span></small>`;
  const edit=(p,label)=>button(label,'edit-staff',`data-id="${esc(p.id)}" aria-label="Sửa hồ sơ của ${esc(p.full_name)}"`);
  queueMicrotask(filterStaff);
  return `<section class="card staff-directory"><div class="staff-directory-heading"><h2>Danh sách giáo lý viên & Soeur</h2>${button('Thêm hồ sơ','new-staff')}</div><label class="field staff-search">Tìm theo tên, tài khoản, số điện thoại hoặc năm sinh<input id="staff-search" type="search" value="${esc(staffQuery)}" autocomplete="off" placeholder="Tên GLV, tên đăng nhập, số điện thoại…"></label><p id="staff-search-results" role="status" aria-live="polite"></p><div class="staff-desktop-table">${table(['GLV / Soeur · Tài khoản','Ngày sinh','Liên hệ','Phục vụ','Thao tác'],model.profiles.map(p=>`<tr data-staff-record data-staff-search="${search(p)}"><td>${identity(p)}</td><td>${esc(birthLabel(p))}</td><td>${phoneLink(p.phone)}${p.email?'<br>'+esc(p.email):''}</td><td>${esc(staffStates[p.status])}${p.note?'<br><small>'+esc(p.note)+'</small>':''}</td><td>${edit(p,'Sửa')}</td></tr>`),'Danh sách hồ sơ GLV')}</div>
   <div class="staff-mobile-list">${model.profiles.map(p=>`<article class="staff-mobile-card" data-staff-record data-staff-search="${search(p)}"><h3>${esc(p.full_name)}</h3><p class="staff-account">${esc(account(p)?.username||'Chưa liên kết')}<span>${esc(role(p))}</span></p><dl><div><dt>Ngày sinh / năm sinh</dt><dd>${esc(birthLabel(p))}</dd></div><div><dt>Liên hệ</dt><dd>${phoneLink(p.phone)}${p.email?'<br>'+esc(p.email):''}</dd></div><div><dt>Phục vụ</dt><dd>${esc(staffStates[p.status])}</dd></div></dl>${p.note?`<p>${esc(p.note)}</p>`:''}${edit(p,'Sửa hồ sơ')}</article>`).join('')}</div></section>
  <details class="card staff-history"><summary>Lịch sử phân công</summary><ul class="staff-history-list">${model.history.map(h=>`<li><div><strong>${esc((model.historyAccounts||model.accounts).find(a=>a.id===h.user_id)?.displayName||h.display_name||h.user_id)}</strong><p>${esc(h.class_name)} · ${esc(h.year)}</p></div><p>${esc({initial:'Phân công ban đầu',assigned:'Nhận phân công',ended:'Kết thúc phân công',inherited:'Tiếp tục sang năm mới'}[h.event]||h.event)} · ${esc(h.slot)}</p><time datetime="${esc(h.stamp)}">${esc(new Date(h.stamp).toLocaleString('vi-VN'))}</time></li>`).join('')||'<li>Chưa có lịch sử phân công.</li>'}</ul></details>`;
 }
 function openStaffEditor(profile,opener){
  const model=data.staff,value=profile||{},currentYear=new Date().getFullYear();
  const linked=model.accounts.find(a=>a.id===value.user_id);
  editingStaff=profile;staffOpenerId=opener.dataset.id||null;error='';delete drafts['admin-staff-form'];
  staffDialog.innerHTML=`<div class="staff-editor-heading"><h2 id="staff-editor-title">${value.id?'Cập nhật hồ sơ GLV':'Thêm hồ sơ GLV'}</h2><p>${value.id?esc(value.full_name):'Thông tin liên hệ và quá trình phục vụ.'}</p></div><form id="admin-staff-form" class="staff-editor-form"><div class="admin-form staff-editor-fields"><p id="staff-form-error" role="alert" tabindex="-1"></p><input type="hidden" name="id" value="${esc(value.id||'')}">${field('Họ tên','full_name','text',value.full_name||'','required minlength="2" maxlength="100" autofocus')}<label class="field">Tài khoản liên kết<select name="user_id"><option value="">Chưa có tài khoản</option>${model.accounts.filter(a=>a.id===linked?.id||!model.profiles.some(p=>p.user_id===a.id)).map(a=>`<option value="${esc(a.id)}" ${a.id===value.user_id?'selected':''}>${esc(a.displayName)} · ${esc(a.username)}</option>`).join('')}</select></label>
   ${field('Số điện thoại','phone','tel',value.phone||'','maxlength="50" autocomplete="tel"')}${field('Email','email','email',value.email||'','maxlength="150"')}${field('Năm sinh','birth_year','number',value.birth_year||'',`min="1900" max="${currentYear}" step="1" inputmode="numeric" aria-describedby="staff-birth-help"`)}${field('Ngày sinh đầy đủ (nếu biết)','birth_date','date',value.birth_date||'',`max="${currentYear}-12-31" aria-describedby="staff-birth-help"`)}<p id="staff-birth-help" class="field-help">Chỉ nhập năm sinh nếu chưa rõ ngày, tháng. Có thể bổ sung ngày sinh đầy đủ sau.</p>${field('Ngày bổn mạng (dd/mm)','feast_day','text',value.feast_day?value.feast_day.slice(3)+'/'+value.feast_day.slice(0,2):'','maxlength="5" pattern="[0-9]{2}/[0-9]{2}" inputmode="numeric" placeholder="dd/mm" aria-describedby="staff-feast-help"')}<p id="staff-feast-help" class="field-help">Nhập ngày đã kiểm tra theo vị thánh bổn mạng. Để trống nếu chưa rõ.</p>${field('Địa chỉ','address','text',value.address||'','maxlength="500"')}
   <label class="field">Trạng thái phục vụ<select name="status">${Object.entries(staffStates).map(([k,v])=>`<option value="${k}" ${k===value.status?'selected':''}>${v}</option>`).join('')}</select></label>${field('Bắt đầu phục vụ','service_from','date',value.service_from||'')}${field('Kết thúc phục vụ','service_to','date',value.service_to||'')}<label class="field">Ghi chú<textarea name="note" rows="2" maxlength="500">${esc(value.note||'')}</textarea></label></div><div class="staff-editor-actions">${button('Đóng','close-staff')}<button type="submit" class="button button-primary">Lưu hồ sơ</button></div></form>`;
  staffDialog.showModal();
 }
 function staffDirectory(){
  if(!state().isManager)return '';
  if(!loaded.staff&&!busy&&!error)queueMicrotask(()=>load('staff'));
  return `<div class="management-console"><div class="page-heading"><div><h1>Hồ sơ GLV & Soeur</h1><p>Thông tin liên hệ, ngày sinh và quá trình phục vụ.</p></div><a class="button button-secondary" href="#teachers">Phân công vào lớp</a></div><div id="admin-feedback" role="alert">${esc(error)}</div><div class="admin-content" ${busy?'aria-busy="true" inert':''}>${staffPage()}</div>${error?button('Thử tải lại','staff-refresh'):''}</div>`;
 }
 function auditPage(){
  const model=data.audit;
  return `<section class="card"><h2>Nhật ký thao tác</h2><form id="admin-audit-form" class="admin-form">${field('Từ ngày (UTC)','from','date',auditQuery.from||'')}${field('Đến ngày (UTC)','to','date',auditQuery.to||'')}<label class="field">Người thực hiện<select name="actor"><option value="">Tất cả</option>${state().accounts.map(a=>`<option value="${esc(a.id)}" ${a.id===auditQuery.actor?'selected':''}>${esc(a.displayName)}</option>`).join('')}</select></label>${field('Thao tác chứa','action','text',auditQuery.action||'')}${field('Tìm trong chi tiết','search','search',auditQuery.search||'')}<button class="button button-primary" type="submit">Lọc nhật ký</button><a class="button button-secondary" href="/api/admin/audit-export?${esc(new URLSearchParams(auditQuery))}">Xuất CSV</a></form></section>
   <section class="card">${model?table(['Thời gian','Người thực hiện','Thao tác','Chi tiết'],model.items.map(r=>`<tr><td>${esc(new Date(r.stamp).toLocaleString('vi-VN'))}</td><td>${esc(r.display_name||'Hệ thống')}<br><small>${esc(r.username)}</small></td><td>${esc(r.action)}</td><td><details><summary>Xem trước / sau</summary>${json(r.details)}</details></td></tr>`),`Nhật ký ${model.offset+1}–${model.offset+model.items.length} / ${model.total}`):loading()}
   ${model?`<div class="admin-toolbar">${button('Trang trước','audit-prev',model.offset===0?'disabled':'')}${button('Trang sau','audit-next',model.offset+100>=model.total?'disabled':'')}</div>`:''}</section>`;
 }
 function yearsPage(){
  const model=data.years;if(!model)return loading();
  return `<section class="card"><h2>Năm học & dữ liệu lưu trữ</h2><p>Năm đang làm việc: <strong>${esc(model.years.find(y=>y.id===model.active)?.year)}</strong>. Chọn năm để xem lịch sử hoặc kích hoạt bộ năm mới đã chuẩn bị.</p><a class="button button-secondary" href="#management">Lập kế hoạch & tạo năm mới</a><form id="admin-year-history-form" class="admin-form"><label class="field">Năm cần xem<select name="id">${model.years.map(y=>`<option value="${esc(y.id)}">${esc(y.year)}${y.id===model.active?' · Đang làm việc':y.prepared?' · Đã chuẩn bị':''}</option>`).join('')}</select></label>${field('Mã thiếu nhi (tùy chọn)','code','text','','placeholder="XH…"')}<button type="submit" class="button button-primary">Xem lịch sử</button></form></section>
  ${history?`<section class="card"><h2>Lịch sử ${esc(history.year)}</h2>${table(['Mã','Thiếu nhi','Lớp','Có mặt / Phép / Vắng','Chi tiết'],history.students.map(s=>{const marks=Object.entries(history.marks).filter(([k])=>k.endsWith('|'+s.id));const count=v=>marks.filter(([,m])=>m.status===v).length;return `<tr><td>${esc(s.id)}</td><td>${esc(s.name)}</td><td>${esc(s.className)}</td><td>${count('X')} / ${count('P')} / ${count('O')}</td><td>${button('Hồ sơ & điểm','history-student',`data-id="${esc(s.id)}"`)}</td></tr>`;}),'Thiếu nhi và chuyên cần trong năm đã chọn')}${historyProfile()}</section>`:''}
  <section class="card"><h2>Chuyển năm làm việc</h2><form id="admin-year-activate-form" class="admin-form"><label class="field">Năm đích<select name="id">${model.years.filter(y=>y.id!==model.active).map(y=>`<option value="${esc(y.id)}">${esc(y.year)}</option>`).join('')}</select></label>${reason()}<button type="submit" class="button button-secondary" ${model.years.length<2?'disabled':''}>Xem trước chuyển năm</button></form>${plan?.year?`<div class="admin-preview"><p>${esc(plan.warning)}</p><p>Đích: <strong>${esc(plan.year)}</strong> · ${plan.classes} lớp · ${plan.count} em.</p><label class="field">Nhập ${esc(plan.year)} để xác nhận<input id="admin-year-confirm" autocomplete="off"></label>${button('Chuyển năm & đăng nhập lại','year-activate')}</div>`:''}</section>`;
 }
 function historyProfile(){
  if(!history?.grades)return '';
  const student=history.students[0];if(!student)return '<p>Không tìm thấy mã thiếu nhi trong năm đã chọn.</p>';
  const value=v=>v===null||v===undefined||v===''?'—':esc(v);
  return `<div class="admin-history-profile"><h3>Hồ sơ & điểm · ${esc(student.name)}</h3>${table(['Thông tin','Giá trị'],Object.entries({gender:'Giới tính',birthDate:'Ngày sinh',baptismDate:'Ngày rửa tội',parents:'Phụ huynh',phone:'Điện thoại',address:'Địa chỉ',subParish:'Giáo khu'}).map(([k,label])=>`<tr><td>${label}</td><td>${value(student[k])}</td></tr>`),'Hồ sơ trong năm đã chọn')}
    ${history.grades.map((g,index)=>(g.semester||index+1)<3?table(['Khảo bài','KT 15 phút','KT 1 tiết','Thi kinh','Thi HK','Trung bình','Xếp loại'],[`<tr><td>${g.khaoBai.map(value).join(', ')}</td><td>${value(g.kt15)}</td><td>${value(g.kt1Tiet)}</td><td>${value(g.thiKinh)}</td><td>${value(g.thiHk)}</td><td>${value(g.tbHk)}</td><td>${value(g.xepLoai)}</td></tr>`],`Điểm học kỳ ${g.semester||index+1}`):table(['Điểm HK1','Điểm HK2','Điểm giáo lý','Xếp loại','Tổng điểm','Hạng'],[`<tr><td>${value(g.diemHk1)}</td><td>${value(g.diemHk2)}</td><td>${value(g.diemGiaoLy)}</td><td>${value(g.xepLoai)}</td><td>${value(g.totalScore)}</td><td>${value(g.yearRank)}</td></tr>`],'Tổng kết năm')).join('')}
    ${table(['Ngày','Loại đơn','Lý do','Trạng thái'],(history.requests||[]).map(r=>`<tr><td>${esc(r.day)}</td><td>${r.kind==='makeup'?'Đổi lễ':'Xin phép'}</td><td>${esc(r.reason)}</td><td>${esc({pending:'Chờ duyệt',approved:'Đã duyệt',rejected:'Từ chối',completed:'Hoàn tất',missed:'Chưa hoàn thành',cancelled:'Đã hủy'}[r.status]||r.status)}</td></tr>`),'Đơn từ trong năm')}
    ${table(['Nội dung','Người ghi','Hẹn theo dõi','Trạng thái'],(history.careNotes||[]).map(n=>`<tr><td>${esc(n.content)}</td><td>${esc(n.actor)}</td><td>${value(n.due_day)}</td><td>${esc({open:'Cần xử lý',following:'Đang theo dõi',done:'Hoàn tất'}[n.status]||n.status)}</td></tr>`),'Nhật ký đồng hành trong năm')}
    ${table(['Ngày áp dụng','Tình trạng','Người xử lý','Lý do'],(history.studentStatuses||[]).map(s=>`<tr><td>${esc(s.effective_day)}</td><td>${esc({active:'Đang học',paused:'Tạm nghỉ',left:'Nghỉ học'}[s.status]||s.status)}</td><td>${esc(s.actor)}</td><td>${esc(s.reason)}</td></tr>`),'Lịch sử tình trạng học tập')}</div>`;
 }
 function accessPage(){
  const model=data.system;if(!model)return loading();
  const accountSnapshots=model.snapshots.filter(s=>s.includesAccounts);
  return `<section class="card"><h2>Sao lưu đầy đủ</h2><p>Bản sao mới gồm Excel, dữ liệu nghiệp vụ, tài khoản, phân quyền, hồ sơ GLV và các năm đã kích hoạt. Phiên đăng nhập không được lưu trong bản sao.</p><a class="button button-primary" href="#management">Tạo / tải / khôi phục dữ liệu</a><p>Khôi phục dữ liệu lớp giữ nguyên tài khoản. Khôi phục tài khoản cần xác nhận riêng ở dưới.</p></section>
  <section class="card"><h2>Khôi phục tài khoản & phân quyền</h2><form id="admin-account-restore-form" class="admin-form"><label class="field">Bản sao<select name="id">${accountSnapshots.map(s=>`<option value="${esc(s.id)}">${esc(s.label)} · ${esc(s.stamp)}</option>`).join('')}</select></label>${reason()}<button type="submit" class="button button-secondary" ${accountSnapshots.length?'':'disabled'}>Xem trước khôi phục tài khoản</button></form>${accountSnapshots.length?'':'<p>Chưa có bản sao chứa tài khoản. Tạo bản sao mới trong Sao lưu & năm học.</p>'}
   ${plan?.users?`<div class="admin-preview"><p>${esc(plan.warning)}</p>${table(['Đăng nhập','Họ tên','Quyền','Trạng thái'],plan.users.map(u=>`<tr><td>${esc(u.username)}</td><td>${esc(u.name)}</td><td>${esc(u.role)}</td><td>${u.active?'Hoạt động':'Đã khóa'}</td></tr>`),'Tài khoản trong bản sao')}<label class="field">Nhập KHÔI PHỤC TÀI KHOẢN<input id="admin-accounts-confirm" autocomplete="off"></label>${button('Khôi phục & đăng nhập lại','accounts-restore')}</div>`:''}</section>
  ${state().mode==='cloud'?'<section class="card"><h2>Truy cập trực tuyến</h2><p>Dữ liệu được lưu trên Supabase. GLV đăng nhập bằng Wi-Fi hoặc 4G, sử dụng các chức năng trong lớp được phân công mà không cần bật máy quản lý.</p></section>':`<section class="card"><h2>Chuẩn bị truy cập từ xa</h2><p>Hệ thống hiện chạy trên máy quản lý. GLV dùng qua 4G cần đường truy cập HTTPS công khai và máy này bật trong giờ sử dụng.</p><ol><li>Chọn một tên miền và tạo tài khoản dịch vụ tunnel.</li><li>Thiết lập tunnel đến dịch vụ loopback của máy quản lý.</li><li>Chạy cấu hình HTTPS công khai đã chuẩn bị, kiểm tra đăng nhập Admin / GLV từ mạng ngoài.</li></ol><p>Hướng dẫn và mẫu cấu hình nằm trong REMOTE-ACCESS.md và thư mục deploy của dự án. Hiện chưa có địa chỉ công khai.</p></section>`}`;
 }
 const loading=()=>'<p role="status">Đang tải thông tin…</p>';
 function page(){
  if(!state().isManager)return '';
  if(['staff','audit','years','access'].includes(tab)&&!loaded[tab]&&!busy&&!error)queueMicrotask(()=>load(tab));
  const body={classes:classPage,import:importPage,staff:staffPage,audit:auditPage,years:yearsPage,access:accessPage}[tab]();
  return `<div class="management-console"><div class="page-heading"><h1>Quản trị hệ thống</h1><p>Quản lý lớp, hồ sơ, lịch sử và năm học của giáo xứ.</p></div><nav class="admin-tabs" aria-label="Các chức năng quản trị">${Object.entries(tabs).map(([k,v])=>`<button type="button" data-admin-tab="${k}" class="button ${k===tab?'button-primary':'button-secondary'}" ${k===tab?'aria-current="page"':''}>${v}</button>`).join('')}</nav><div id="admin-feedback" role="alert">${esc(error)}</div><div class="admin-content" ${busy?'aria-busy="true" inert':''}>${body}</div>${busy?loading():''}</div>`;
 }
 async function loadNotifications(){const stamp=epoch;notificationLoading=true;error='';try{const result=await api('notifications');if(stamp===epoch)notification=result;}catch(e){if(stamp===epoch)error=e.message;}finally{if(stamp===epoch){notificationLoading=false;render();}}}
 function notificationsPage(){
  if(!notification&&!notificationLoading&&!error)queueMicrotask(loadNotifications);
  return `<div class="management-reminders"><div class="page-heading"><h1>Thông báo & nhắc việc</h1><p>Công việc trong phạm vi các lớp bạn được quản lý.</p></div><div role="alert">${esc(error)}</div><section class="card"><div class="admin-toolbar"><h2>${notification?notification.unread+' việc chưa đọc':'Nhắc việc'}</h2>${button('Làm mới','notifications-refresh')}${button('Đánh dấu tất cả đã đọc','notifications-read-all',!notification?.unread?'disabled':'')}</div>${notificationLoading?loading():notification?`<ul class="admin-notifications">${notification.items.map(n=>`<li class="${n.read?'is-read':''}"><div><strong>${esc(n.title)}</strong><p>${esc(n.detail)}</p><a href="#${esc(n.target)}">Mở công việc →</a></div>${n.read?'<small>Đã đọc</small>':button('Đã đọc','notification-read',`data-id="${esc(n.id)}"`)}</li>`).join('')||'<li>Chưa có công việc cần nhắc.</li>'}</ul>`:''}</section>
  ${notification?`<section class="card"><h2>Tùy chọn nhắc việc</h2><form id="notification-preferences-form">${Object.entries(reminderKinds).filter(([k])=>k!=='system'||state().isManager).map(([k,v])=>`<label class="admin-check"><input type="checkbox" name="${k}" ${notification.preferences[k]?'checked':''}>${v}</label>`).join('')}<button type="submit" class="button button-primary">Lưu tùy chọn</button></form></section>`:''}</div>`;
 }
 async function perform(fn,form=null){
  if(busy)return;const stamp=epoch;busy=true;error='';
 const controls=[...(form||document.getElementById('page'))?.querySelectorAll('button')||[]],disabled=controls.map(el=>el.disabled);controls.forEach(el=>el.disabled=true);
  try{await fn();}catch(e){if(stamp===epoch){error=e.message;const isStaff=form?.getAttribute('id')==='admin-staff-form',feedback=document.getElementById(isStaff?'staff-form-error':'admin-feedback');if(feedback){feedback.textContent=error;feedback.scrollIntoView({block:'nearest'});if(isStaff)feedback.focus({preventScroll:true});}else toast(error);}}
  finally{if(stamp===epoch){busy=false;controls.forEach((el,index)=>el.disabled=disabled[index]);if(!error)render();}}
 }
 async function write(name,values){const result=await queueWrite(()=>api('admin/'+name,values));if(result.requireReauth){toast('Đã hoàn tất. Đăng nhập lại để tiếp tục.');ctx.reauthenticate();return result;}if(result.state)applyServer(result.state);return result;}
 function resetPlan(){plan=null;previewValues=null;}
 document.addEventListener('submit',async event=>{
  const form=event.target;
  if(!(form.getAttribute('id')||'').startsWith('admin-')&&form.getAttribute('id')!=='notification-preferences-form')return;
  event.preventDefault();if(!form.reportValidity())return;
  await perform(async()=>{
   const values=Object.fromEntries(new FormData(form));
   drafts[form.getAttribute('id')]=Object.fromEntries(Object.entries(values).filter(([,v])=>typeof v==='string'));
   if(form.getAttribute('id')==='admin-class-form'){plan=await api('admin/class-preview',values);previewValues=values;}
   if(form.getAttribute('id')==='admin-import-form'){
    const file=form.elements.file.files[0];delete values.file;
    if(file){if(file.size>2_000_000)throw new Error('File nhập tối đa 2 MB.');values.filename=file.name;values.fileBase64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Chưa đọc được file.'));reader.readAsDataURL(file);});delete values.text;}
    plan=await api('admin/import-preview',values);previewValues=values;
   }
   if(form.getAttribute('id')==='admin-staff-form'){data.staff=(await write('staff-save',values)).staff;ctx.onStaffChanged?.();editingStaff=null;delete drafts[form.getAttribute('id')];staffDialog.close();toast('Đã lưu hồ sơ GLV.');}
   if(form.getAttribute('id')==='admin-audit-form'){auditQuery=Object.fromEntries(Object.entries(values).filter(([,v])=>v));data.audit=await api('admin/audit?'+new URLSearchParams(auditQuery));}
   if(form.getAttribute('id')==='admin-year-history-form'){history=await api('admin/year-history?'+new URLSearchParams(values));history.sourceId=values.id;}
   if(form.getAttribute('id')==='admin-year-activate-form'){plan=await api('admin/year-activate-preview',values);previewValues=values;}
   if(form.getAttribute('id')==='admin-account-restore-form'){plan=await api('admin/accounts-restore-preview',values);previewValues=values;}
   if(form.getAttribute('id')==='notification-preferences-form'){notification=await queueWrite(()=>api('notifications/preferences',{preferences:Object.fromEntries(Object.keys(reminderKinds).map(k=>[k,form.elements[k]?.checked??notification.preferences[k]]))}));toast('Đã lưu tùy chọn.');}
  },form);
 });
 document.addEventListener('click',async event=>{
  const tabButton=event.target.closest('[data-admin-tab]');
  if(tabButton){if(busy){toast('Chờ thao tác hiện tại hoàn tất.');return;}tab=tabButton.dataset.adminTab;resetPlan();error='';render();return;}
  const target=event.target.closest('[data-admin-action]');if(!target)return;
  const action=target.dataset.adminAction;
  if(action==='staff-refresh'){await load('staff');return;}
  if(action==='edit-class'){editingClass=classes().find(c=>c.id===target.dataset.id);delete drafts['admin-class-form'];resetPlan();render();document.getElementById('admin-class-form')?.scrollIntoView({block:'start'});return;}
  if(action==='edit-staff'||action==='new-staff'){if(!busy)openStaffEditor(action==='edit-staff'?data.staff.profiles.find(p=>p.id===target.dataset.id):null,target);return;}
  if(action==='close-staff'){if(!busy)staffDialog.close();return;}
  await perform(async()=>{
   if(['class-save','import-save','year-activate','accounts-restore'].includes(action)){
    if(!plan||!previewValues)throw new Error('Xem trước lại trước khi xác nhận.');
    const extra=action==='import-save'?{acceptWarnings:document.getElementById('import-accept-warnings')?.checked===true}:action==='year-activate'?{confirmation:document.getElementById('admin-year-confirm').value}:action==='accounts-restore'?{confirmation:document.getElementById('admin-accounts-confirm').value}:{};
    const result=await write(action,{...previewValues,previewToken:plan.token,...extra});
    if(result.requireReauth)return;
    if(action==='import-save'){importFile=null;delete drafts['admin-import-form'];}
    toast(action==='import-save'?`Đã thêm ${result.count} thiếu nhi.`:'Đã cập nhật lớp.');resetPlan();
   }
   if(action.startsWith('audit-')){auditQuery.offset=Math.max(0,(data.audit?.offset||0)+(action==='audit-next'?100:-100));data.audit=await api('admin/audit?'+new URLSearchParams(auditQuery));}
   if(action==='history-student'){const sourceId=history.sourceId;history=await api('admin/year-history?'+new URLSearchParams({id:sourceId,code:target.dataset.id}));history.sourceId=sourceId;}
   if(action==='notifications-refresh'){notification=await api('notifications');error='';}
   if(action==='notification-read'||action==='notifications-read-all')notification=await queueWrite(()=>api('notifications/read',{ids:action==='notification-read'?[target.dataset.id]:notification.items.filter(n=>!n.read).map(n=>n.id)}));
  });
 });
 document.addEventListener('input',event=>{
  if(event.target.id==='staff-search'){staffQuery=event.target.value;filterStaff();return;}
  const form=event.target.form;if(!form?.getAttribute('id')?.startsWith('admin-'))return;
  drafts[form.getAttribute('id')]=Object.fromEntries([...new FormData(form)].filter(([,v])=>typeof v==='string'));
  if(event.target.type==='file')importFile=event.target.files[0]||null;
  if(['admin-class-form','admin-import-form','admin-year-activate-form','admin-account-restore-form'].includes(form.getAttribute('id'))&&plan){resetPlan();document.querySelectorAll('.admin-preview').forEach(el=>el.remove());}
 });
 return {page,staffDirectory,notificationsPage,clear,restoreDrafts};
}
