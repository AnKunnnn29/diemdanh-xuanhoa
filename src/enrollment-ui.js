import {matchesSearch} from './ux-utils.js';
import {contactFields,encodeContactFields} from './parent-contacts.js';

export function createEnrollmentUI(ctx){
 const {esc,api,queueWrite,applyServer,render,toast}=ctx;
 let busy=false,opener=null,query='',generation=0;
 const classes=()=>ctx.classes();
 const dialog=document.createElement('dialog');
 dialog.id='enrollment-dialog';dialog.className='management-console staff-editor';dialog.setAttribute('aria-labelledby','enrollment-title');
 document.body.append(dialog);
 const input=(label,name,type='text',value='',extra='')=>`<label class="field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra} aria-describedby="enrollment-error"></label>`;
 const classOptions=(selected='')=>classes().filter(c=>!c.archived).map(c=>`<option value="${esc(c.id)}" ${selected===c.id?'selected':''}>${esc(c.name)} · ${c.count} / 40 em</option>`).join('');
 function focusOpener(){
  if(opener?.isConnected){opener.focus({preventScroll:true});return;}
  const selector=opener?.hasAttribute('data-intake-student')?'[data-intake-student]':'[data-intake-class]';
  document.querySelector(selector)?.focus({preventScroll:true});
 }
 dialog.addEventListener('close',focusOpener);
 dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
 function show(action,title,description,body){
  dialog.innerHTML=`<div class="staff-editor-heading"><h2 id="enrollment-title">${title}</h2><p>${description}</p></div><form id="enrollment-form" class="staff-editor-form" data-action="${action}"><div class="admin-form staff-editor-fields"><p id="enrollment-error" role="alert" tabindex="-1"></p>${body}</div><div class="staff-editor-actions"><button type="button" class="button button-secondary" data-intake-close>Đóng</button><button type="submit" class="button button-primary">${action==='class'?'Tạo lớp':'Thêm thiếu nhi'}</button></div></form>`;
  dialog.showModal();
 }
 async function openStudent(id){
  const stamp=generation;
  show('student','Thêm thiếu nhi vào giáo xứ','Chọn lớp để hồ sơ được thêm vào danh sách và sổ giáo lý.','<p class="field-help">Đang chuẩn bị mã và thông tin nhập học…</p>');
  dialog.querySelector('button[type=submit]').disabled=true;
  try{
   const options=await api('admin/admission-options');if(stamp!==generation||!dialog.open)return;
   const fields=`<label class="field">Lớp giáo lý (bắt buộc)<select name="classId" required aria-describedby="enrollment-error"><option value="">Chọn lớp</option>${classOptions(id)}</select></label>${input('Mã thiếu nhi (bắt buộc)','code','text',options.suggestedCode,'required pattern="XH[0-9]+" maxlength="40" autocapitalize="characters" spellcheck="false"')}
    <p class="field-help enrollment-wide">Mã được đề xuất theo danh sách đã cấp. Kiểm tra mã trước khi lưu; mã cũ không được dùng lại.</p>
    ${input('Tên thánh','saintName','text','','maxlength="100"')}${input('Họ và tên (bắt buộc)','fullName','text','','required minlength="2" maxlength="150" autocomplete="name"')}
    ${input('Tháng nhập học (bắt buộc)','enrolledMonth','month',options.enrolledMonth,`required min="${options.startMonth}" max="${options.endMonth}"`)}<label class="field">Giới tính<select name="gender"><option value="">Chưa cập nhật</option><option>Nam</option><option>Nữ</option></select></label>
    ${input('Ngày sinh','birthDate','date','','max="'+ctx.today()+'"')}${input('Ngày rửa tội','baptismDate','date','','max="'+ctx.today()+'"')}
    <details class="enrollment-wide intake-contact"><summary>Thông tin gia đình & liên hệ</summary><div class="intake-contact-fields">${contactFields({},{esc,helpId:'enrollment-contact-help'})}${input('Địa chỉ','address','text','','maxlength="500"')}${input('Giáo họ','subParish','text','','maxlength="150"')}</div></details>`;
   dialog.querySelector('.staff-editor-fields').innerHTML='<p id="enrollment-error" role="alert" tabindex="-1"></p>'+fields;
   dialog.querySelector('button[type=submit]').disabled=false;
   dialog.querySelector('[name=fullName]').focus({preventScroll:true});
  }catch(error){if(stamp===generation&&dialog.open)document.getElementById('enrollment-error').textContent=error.message;}
 }
 function openClass(){
  show('class','Tạo lớp giáo lý','Lớp mới bắt đầu với danh sách trống và lịch học theo lớp mẫu.',
   `${input('Tên lớp mới (bắt buộc)','name','text','','required minlength="3" maxlength="80" placeholder="Ví dụ: Thiếu Nhi 1 C" autofocus')}<label class="field">Lớp mẫu cho lịch và sổ (bắt buộc)<select name="classId" required>${classOptions()}</select></label><p class="field-help enrollment-wide">Chọn lớp cùng khối để dùng lịch học phù hợp. Sau khi tạo, bạn có thể thêm thiếu nhi và phân công GLV ngay.</p>`);
 }
 function filter(){
  let count=0;document.querySelectorAll('[data-class-directory]').forEach(el=>{el.hidden=!matchesSearch(el.dataset.classDirectory,query);if(!el.hidden)count++;});
  const result=document.getElementById('class-directory-results');if(result)result.textContent=`${count} / ${classes().length} lớp`;
 }
 function page(){
  queueMicrotask(filter);
  return `<div class="page-heading"><div><h1>Lớp giáo lý</h1><p>Tạo lớp, tiếp nhận thiếu nhi và phân công người phụ trách.</p></div><button type="button" class="button button-primary" data-intake-class>Tạo lớp mới</button></div>
   <div class="teacher-toolbar"><label class="field">Tìm lớp<input id="class-directory-search" type="search" value="${esc(query)}" placeholder="Tên lớp hoặc GLV phụ trách…"></label><a class="button button-secondary" href="#administration">Thiết lập & lưu trữ lớp</a></div><p id="class-directory-results" role="status" aria-live="polite"></p>
   <div class="class-directory-grid">${classes().map(c=>`<article class="card class-directory-card" data-class-directory="${esc(c.name+' '+Object.values(c.teachers||{}).join(' '))}"><div><h2>${esc(c.name)}</h2><p>${c.count} / 40 thiếu nhi · ${c.archived?'Đã lưu trữ':'Đang hoạt động'}</p></div><p class="field-help">${Object.values(c.teachers||{}).filter(Boolean).map(esc).join(' · ')||'Chưa phân công GLV'}</p><div class="class-directory-actions"><button type="button" class="button button-secondary" data-intake-view-class="${esc(c.id)}">Danh sách lớp</button>${!c.archived?`<button type="button" class="button button-primary" data-intake-student="${esc(c.id)}" ${c.count>=40?'disabled':''}>${c.count>=40?'Lớp đã đủ 40 em':'Thêm thiếu nhi'}</button><button type="button" class="button button-secondary" data-edit-teachers="${esc(c.id)}">Phân công GLV</button>`:''}</div></article>`).join('')}</div>`;
 }
 document.addEventListener('input',event=>{if(event.target.id==='class-directory-search'){query=event.target.value;filter();}});
 document.addEventListener('click',event=>{
  if(event.target.closest('[data-intake-close]')){if(!busy){generation++;dialog.close();}return;}
  const button=event.target.closest('[data-intake-student],[data-intake-class],[data-intake-view-class]');
  if(!button||!ctx.state().isManager||busy)return;
  opener=button;generation++;
  if(button.hasAttribute('data-intake-view-class')){const group=classes().find(c=>c.id===button.dataset.intakeViewClass);if(group)ctx.openStudents(group.name);}
  else if(button.hasAttribute('data-intake-class'))openClass();else openStudent(button.dataset.intakeStudent||'');
 });
 document.addEventListener('submit',event=>{
  if(event.target.getAttribute('id')!=='enrollment-form')return;
  event.preventDefault();if(busy)return;
  const form=event.target,error=document.getElementById('enrollment-error'),button=form.querySelector('button[type=submit]'),label=button.textContent;
  const action=form.dataset.action;error.textContent='';busy=true;form.setAttribute('aria-busy','true');form.querySelectorAll('button').forEach(b=>b.disabled=true);button.textContent='Đang lưu…';
  queueWrite(async()=>{
   try{
    let values=Object.fromEntries(new FormData(form));
    if(action==='student'){values=encodeContactFields(values);values.enrolledFrom=values.enrolledMonth+'-01';delete values.enrolledMonth;}
    const result=await api(action==='class'?'admin/class-create':'admin/student-create',values);
    applyServer(result.state);ctx.onChanged();dialog.close();render();
    toast(action==='class'?'Đã tạo lớp mới. Có thể thêm thiếu nhi và phân công GLV.':`Đã thêm thiếu nhi ${result.code} vào lớp và giáo xứ.`);
   }catch(failure){error.textContent=failure.message;error.focus();error.scrollIntoView({block:'nearest'});}
   finally{busy=false;form.removeAttribute('aria-busy');form.querySelectorAll('button').forEach(b=>b.disabled=false);button.textContent=label;}
  });
 });
 return {page,clear(){generation++;query='';dialog.close();dialog.replaceChildren();}};
}
