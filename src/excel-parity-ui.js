import {gradeValue} from './grade-summary.js';
import {csvText} from './care-insights.js';
import {contactFields,encodeContactFields,parentNames,parentPhones} from './parent-contacts.js';

const days=['Chủ Nhật','Thứ Hai','Thứ Ba','Thứ Tư','Thứ Năm','Thứ Sáu','Thứ Bảy'];
const months=[9,10,11,12,1,2,3,4,5,6,7,8];
export function createExcelParityUI(ctx) {
  const {esc,api,queueWrite,render,applyServer,toast,downloadBlob,today}=ctx;
  let classId='',details=null,loading=false,error='',loadToken=0,plan=null,action='',fixed={},opener=null;
  const people=()=>ctx.students().filter(s=>s.classId===classId);
  const classes=()=>ctx.classes();
  async function load(id=classes().find(c=>c.name===ctx.workingClass?.())?.id||classId||classes()[0]?.id) {
    const token=++loadToken;classId=id;ctx.onClassChange?.(classes().find(c=>c.id===id)?.name||'');details=null;loading=true;error='';render();
    try {const r=await api(`excel-details?classId=${encodeURIComponent(id)}`);if(token===loadToken)details=r;}
    catch(e){if(token===loadToken)error=e.message;}
    finally{if(token===loadToken){loading=false;render();}}
  }
  function page() {
    if(!ctx.state().isManager)return '<section class="card p-6"><h1>Quản lý sổ lớp</h1><p>Mở mục này trên máy Excel để tiếp nhận thiếu nhi, cấu hình sổ và ghi nhận lễ bổ sung.</p></section>';
    return `<div class="page-heading"><div><p class="eyebrow">SỔ LỚP</p><h1>Quản lý sổ & báo cáo</h1><p>Thao tác theo mẫu Excel, xem trước trước khi ghi dữ liệu.</p></div></div><div class="feature-actions"><label class="field">Lớp<select id="parity-class">${classes().map(c=>`<option value="${esc(c.id)}" ${c.id===classId?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><button class="button button-secondary" data-parity="refresh">Làm mới sổ</button></div>
    <p id="parity-message" role="status" aria-live="polite">${loading?'Đang đọc sổ lớp…':esc(error)}</p>
    ${details?`<section class="card"><div class="card-header"><h2>${esc(details.className)}</h2><span>${people().length} / 40 em</span></div><div class="card-body"><div class="feature-actions">${[['student-add','Thêm thiếu nhi'],['enrollment','Sửa tháng nhập học']].map(([a,t])=>`<button class="button button-secondary" data-parity="${a}">${t}</button>`).join('')}</div><p class="field-help">Mẫu quản lý nhập học theo tháng. Mã mới phải được xác nhận cấp; mã đã có lịch sử không được sử dụng lại.</p></div></section>
    <details class="card easy-advanced mt-6"><summary>Thiết lập nâng cao</summary><div class="card-body"><div class="feature-actions">${[['configuration','Cấu hình sổ'],['bulk-grades','Nhập điểm hàng loạt'],['bulk-attendance','Điểm danh hàng loạt'],['scratch','Vùng nhập Excel']].map(([a,t])=>`<button class="button button-secondary" data-parity="${a}">${t}</button>`).join('')}</div></div></details>
    <section class="card mt-6"><div class="card-header"><h2>Lễ bổ sung ngoài lịch</h2><button class="button button-primary" data-parity="supplemental">Ghi lễ bổ sung</button></div><div class="card-body"><p>Lễ ngoài lịch được cộng vào cột “Đi Lễ Bù”. Đổi ngày đã ghi X về ngày gốc không được cộng lần nữa. Số cũ trong Excel được giữ nguyên.</p>${details.supplements.length?`<ul class="feature-list">${details.supplements.map(r=>`<li><div><strong>${esc(ctx.students().find(s=>s.id===r.code)?.name||r.code)}</strong><p>${esc(r.code)} · ${esc(r.actual_day)} · ${r.status==='active'?'Đã cộng 1 buổi':'Đã hủy'}</p><small>${esc(r.actor)} · ${esc(r.reason)}</small></div>${r.status==='active'?`<button class="button button-text" data-parity="cancel-supplement" data-id="${esc(r.id)}">Hủy lượt</button>`:''}</li>`).join('')}</ul>`:'<p class="field-help">Chưa có lượt bổ sung ghi từ web. Các buổi cũ chưa có lịch sử ngày không được tự tạo lại.</p>'}</div></section>
    <section class="card mt-6"><div class="card-header"><h2>Ghi chú sổ lớp</h2><button class="button button-secondary" data-parity="note">Thêm ghi chú</button></div><div class="card-body"><p class="field-help">Ghi chú dưới đây nằm trong sheet Ghi Chú của sổ lớp. Nhật ký chăm sóc theo em lưu ở dữ liệu web, có thể tải CSV riêng và nằm trong bản sao lưu đầy đủ.</p>${details.notes.length?`<ul class="feature-list">${details.notes.map(n=>`<li><div><strong>${esc(n.cell)}</strong><p class="parity-note">${esc(n.content)}</p></div>${n.editable?`<button class="button button-text" data-parity="edit-note" data-cell="${esc(n.cell)}">Sửa</button>`:''}</li>`).join('')}</ul>`:'<p>Chưa có ghi chú trong sổ lớp.</p>'}<button class="button button-secondary" data-parity="export-care">Tải nhật ký chăm sóc CSV</button></div></section>
    <section class="card mt-6"><div class="card-header"><h2>In / Lưu PDF</h2></div><div class="card-body"><p>Chọn phạm vi cho chuyên cần; bảng điểm chọn học kỳ. Trong cửa sổ in có thể lưu PDF.</p><div class="feature-actions"><label class="field">Phạm vi chuyên cần<select id="parity-report-range"><option value="year">Cả năm</option><option value="hk1">Học kỳ 1</option><option value="hk2">Học kỳ 2</option><option value="month">Theo tháng</option></select></label><label class="field">Tháng<input id="parity-report-month" type="month" value="${today().slice(0,7)}"></label><label class="field">Bảng điểm<select id="parity-report-semester"><option value="1">Học kỳ 1</option><option value="2">Học kỳ 2</option></select></label></div><div class="feature-actions">${[['roster','Danh sách lớp'],['attendance','Chuyên cần'],['term','Bảng điểm'],['year','Tổng kết năm']].map(([a,t])=>`<button class="button button-secondary" data-parity="print-${a}">${t}</button>`).join('')}</div></div></section>
    <details class="card mt-6 p-4"><summary>Lịch sử quản lý gần đây</summary><ul class="feature-list">${details.history.map(e=>`<li><div><strong>${esc(e.actor)} · ${esc(e.action)}</strong><p>${esc(e.reason)}</p><small>${esc(e.stamp)}</small></div></li>`).join('')}</ul></details>`:''}`;
  }
  function dialogs(){return `<dialog id="parity-dialog" aria-labelledby="parity-title"><form id="parity-form"><div class="dialog-heading"><h2 id="parity-title"></h2><button type="button" class="icon-button" data-close-dialog aria-label="Đóng">${ctx.i('close')}</button></div><div id="parity-fields"></div><p id="parity-error" role="alert" tabindex="-1"></p><div id="parity-preview" aria-live="polite"></div><div class="dialog-actions"><button type="button" class="button button-secondary" data-close-dialog>Quay lại</button><button id="parity-submit" class="button button-primary" type="submit">Xem trước</button></div></form></dialog>`;}
  const selectPerson=code=>`<label class="field">Thiếu nhi<select name="code" required>${people().map(s=>`<option value="${esc(s.id)}" ${code===s.id?'selected':''}>${esc(s.id)} · ${esc(s.name)}</option>`).join('')}</select></label>`;
  const input=(name,label,value='',type='text',required=false)=>`<label class="field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${required?'required':''} maxlength="500" aria-describedby="parity-error"></label>`;
  function show(op,body,extra={},title='') {
    action=op;fixed=extra;plan=null;opener=document.activeElement;
    document.getElementById('parity-title').textContent=title||({configuration:'Cấu hình sổ lớp','student-add':'Tiếp nhận thiếu nhi',enrollment:'Tháng nhập học',supplemental:'Lễ bổ sung ngoài lịch',note:'Ghi chú sổ lớp',scratch:'Vùng nhập Excel','bulk-grades':'Nhập điểm hàng loạt','bulk-attendance':'Điểm danh có mặt hàng loạt'}[op]);
    document.getElementById('parity-fields').innerHTML=body+input('actor','Người xác nhận',ctx.actor(),'text',true)+`<label class="field">Lý do<textarea name="reason" minlength="3" maxlength="500" required rows="2" aria-describedby="parity-error"></textarea></label>`;
    document.getElementById('parity-error').textContent='';document.getElementById('parity-preview').innerHTML='';document.getElementById('parity-submit').textContent='Xem trước';
    document.getElementById('parity-dialog').showModal();document.getElementById('parity-form').querySelector('input:not([type=hidden]),select,textarea')?.focus();
  }
  function values() {
    const form=document.getElementById('parity-form'),v=Object.fromEntries(new FormData(form));
    const common={...fixed,...v,classId,operation:action,expectedRevision:details.revision};
    if(action==='configuration')common.configuration={semesters:months.map((_,i)=>v['semester_'+i]),allowMass:Number(v.allowMass),allowLesson:Number(v.allowLesson),catechismThreshold:Number(v.catechismThreshold),attendanceThreshold:Number(v.attendanceThreshold),schedules:details.configuration.schedules.map(s=>({row:s.row,massDays:days.map((_,d)=>d).filter(d=>form.querySelector(`[name="mass_${s.row}_${d}"]`).checked),lessonDays:[0]}))};
    if(action==='student-add'||action==='enrollment')common.enrolledFrom=v.enrolledMonth+'-01';
    if(action.startsWith('bulk-')){common.kind=action.slice(5);common.semester=Number(v.semester||1);delete common.operation;}
    return encodeContactFields(common);
  }
  async function open(op,target) {
    if(!details)await load();if(!details)return;
    if(op==='student-add')show(op,input('code','Mã đã xác nhận cấp',details.suggestedCode,'text',true)+`<p class="field-help">Mã đề xuất là số tiếp theo chưa cấp trong danh sách hiện có. Kiểm tra quy tắc cấp mã của giáo xứ trước khi xác nhận.</p>`+input('saintName','Tên thánh')+input('fullName','Họ và tên','','text',true)+input('enrolledMonth','Tháng nhập học',today().slice(0,7),'month',true)+`<label class="field">Giới tính<select name="gender"><option value="">Chưa rõ</option><option>Nam</option><option>Nữ</option></select></label>`+'<details><summary>Thông tin gia đình và liên lạc</summary>'+input('birthDate','Ngày sinh','','date')+input('baptismDate','Ngày rửa tội','','date')+contactFields({},{esc,helpId:'parity-parent-contact-help'})+input('address','Địa chỉ')+input('subParish','Giáo họ')+'</details>');
    else if(op==='enrollment')show(op,selectPerson(target.dataset.code)+input('enrolledMonth','Tháng nhập học mới',people().find(s=>s.id===target.dataset.code)?.enrolledFrom?.slice(0,7)||details.yearStart.slice(0,7),'month',true)+`<p class="field-help">Thay đổi sẽ được kiểm tra với chuyên cần, đơn và điểm đã nhập. Sổ hiện tại tính theo tháng.</p>`);
    else if(op==='supplemental')show(op,selectPerson()+input('actualDate','Ngày đã đi lễ',today(),'date',true)+`<p class="field-help">Chỉ ghi lễ thực tế ngoài lịch lớp, trong năm học. Mỗi em mỗi ngày tối đa một lượt; không dùng lượt đã điểm danh/đổi lễ.</p>`,{action:'add'});
    else if(op==='cancel-supplement'){const r=details.supplements.find(r=>r.id===target.dataset.id);show('supplemental',`<p>Hủy 1 buổi của ${esc(r.code)} ngày ${esc(r.actual_day)}; giữ lịch sử và tính lại tổng kết.</p>`,{action:'cancel',id:r.id,code:r.code},'Hủy lượt lễ bổ sung');}
    else if(op==='note'||op==='edit-note'){const n=details.notes.find(n=>n.cell===target.dataset.cell);show('note',`<p>Sheet Ghi Chú · ô ${esc(n?.cell||details.nextNoteCell)}</p><label class="field">Nội dung<textarea name="content" rows="5" maxlength="2000" aria-describedby="parity-error">${esc(n?.content||'')}</textarea></label>`,{cell:n?.cell||details.nextNoteCell});}
    else if(op==='configuration'){
      const c=details.configuration;
      show(op,`<label class="field">Phạm vi<select name="scope"><option value="class">Lớp đang xem</option><option value="all">Tất cả lớp</option></select></label><div class="dialog-fields">${input('allowMass','Số buổi lễ được nghỉ mỗi tháng',c.allowMass,'number',true)+input('allowLesson','Số buổi giáo lý được nghỉ mỗi tháng',c.allowLesson,'number',true)+input('catechismThreshold','Ngưỡng đạt Giáo Lý',c.catechismThreshold,'number',true)+input('attendanceThreshold','Ngưỡng đạt Thánh Lễ',c.attendanceThreshold,'number',true)}</div><details><summary>Phân chia học kỳ</summary><div class="dialog-fields">${months.map((m,i)=>`<label class="field">Tháng ${m}<select name="semester_${i}"><option value="HKI" ${c.semesters[i]==='HKI'?'selected':''}>HK I</option><option value="HKII" ${c.semesters[i]==='HKII'?'selected':''}>HK II</option></select></label>`).join('')}</div></details><details><summary>Lịch lễ theo khối trong sổ này</summary><p class="field-help">Giáo lý và lễ sớm giữ Chủ Nhật. Thay lịch sẽ kiểm tra ngày đã ghi, đơn, buổi chốt và giới hạn cột của mẫu.</p>${c.schedules.map(s=>`<fieldset class="parity-days"><legend>${esc(s.label)}</legend>${days.map((d,i)=>`<label><input type="checkbox" name="mass_${s.row}_${i}" ${s.massDays.includes(i)?'checked':''}>${d}</label>`).join('')}</fieldset>`).join('')}</details>`);
      document.querySelectorAll('#parity-form input[type=number]').forEach(i=>{i.min='0';i.max=i.name.startsWith('allow')?'31':'10';i.step=i.name.startsWith('allow')?'1':'0.1';});
    }else if(op==='scratch')show(op,`<label class="field">Thao tác<select name="mode"><option value="restore">Khôi phục vùng nhập theo mẫu</option><option value="clear">Xóa dữ liệu trong vùng nhập</option></select></label><p>Chỉ sửa vùng nhập của DiemDanhAuto. Các lượt điểm danh đã ghi và bảng điểm được giữ.</p>`);
    else if(op==='bulk-grades')show(op,`<label class="field">Học kỳ<select name="semester"><option value="1">HK 1</option><option value="2">HK 2</option></select></label><p id="bulk-help">Dán từ Excel, mỗi dòng 25 cột: mã → KB1…KB20 → KT15 → KT1 tiết → Thi Kinh → Thi HK. Không dán hàng tiêu đề. Ô trống sẽ xóa điểm hiện có; 0 và P được giữ riêng.</p><button type="button" class="button button-secondary" data-parity="bulk-template">Tải mẫu TSV của lớp</button><label class="field">Danh sách điểm<textarea name="text" rows="8" required maxlength="30000" aria-describedby="bulk-help parity-error"></textarea></label>`);
    else if(op==='bulk-attendance')show(op,input('date','Ngày thực tế',today(),'date',true)+`<label class="field">Hoạt động<select name="activity"><option value="mass">Thánh lễ</option><option value="lesson">Giáo lý</option><option value="early">Lễ sớm</option></select></label>${input('attendedTime','Giờ đi thực tế (cần khi bổ sung lễ sớm ngoài giờ)','','time')}<p id="bulk-help">Mỗi dòng một mã. Chỉ ghi có mặt X, áp dụng đơn đổi lễ đã duyệt. P/O hoặc buổi đã chốt cần chỉnh riêng. Nếu ghi bị gián đoạn, danh sách đã lưu được giữ và có thể nhập lại để tiếp tục.</p><label class="field">Các mã thiếu nhi<textarea name="text" rows="8" required maxlength="30000" aria-describedby="bulk-help parity-error"></textarea></label>`);
  }
  async function submit(e) {
    e.preventDefault();const button=document.getElementById('parity-submit'),err=document.getElementById('parity-error');
    let v;try{v=values();}catch(e){err.textContent=e.message;return;}
    const signature=JSON.stringify(v);button.disabled=true;err.textContent='';
    await queueWrite(async()=>{
      try {
        if(!plan){
          document.getElementById('parity-preview').textContent='Đang kiểm tra và chuẩn bị bản sao Excel…';
          const r=await api(action.startsWith('bulk-')?'bulk-preview':'excel-preview',v);
          if(JSON.stringify(values())!==signature){document.getElementById('parity-preview').textContent='Nội dung đã thay đổi khi kiểm tra. Xem trước lại.';return;}
          plan=r;
          document.getElementById('parity-preview').innerHTML=`<h3>Kết quả xem trước</h3><ul>${(r.description||r.entries?.map(s=>`${s.code} · ${s.name||'Điểm'}${s.targetDate?' → '+s.targetDate:''}${s.duplicate?' · Đã có mặt':''}`)||[]).map(s=>`<li>${esc(s)}</li>`).join('')}</ul>${r.calendarChanges?`<ul>${r.calendarChanges.map(c=>`<li>${esc(c.className)}: ${Object.values(c.added).flat().length} ngày thêm; ${Object.values(c.removed).flat().length} ngày bỏ.</li>`).join('')}</ul>`:''}${r.issues?.length?`<p>Cần xử lý trước khi lưu:</p><ul>${r.issues.map(s=>`<li>${esc(s)}</li>`).join('')}</ul>`:'<p>Đã kiểm tra. Xác nhận để ghi vào sổ; có bản sao trước khi thay dữ liệu.</p>'}`;
          button.textContent=r.issues?.length?'Xem trước lại':'Xác nhận lưu';if(r.issues?.length)plan=null;return;
        }
        const r=await api(action.startsWith('bulk-')?'bulk-save':'excel-save',{...v,previewToken:plan.token});
        applyServer(r.state);ctx.invalidateGrades();ctx.rememberActor(v.actor);plan=null;
        if(r.saved===false){err.textContent=`Đã lưu ${r.completed.length} em; dừng tại ${r.failedCode}: ${r.error}. Giữ kết quả đã lưu. Làm mới sổ và xem trước lại để tiếp tục.`;button.textContent='Xem trước';details=await api(`excel-details?classId=${classId}`);return;}
        if(r.excelReady===false)toast(r.message||'Điểm đã lưu, Excel còn chờ cập nhật.');else toast('Đã cập nhật sổ lớp.');
        document.getElementById('parity-dialog').close();await load(classId);
        if(opener?.dataset.parity)document.querySelector(`[data-parity="${CSS.escape(opener.dataset.parity)}"]`)?.focus({preventScroll:true});
      }catch(e){err.textContent=e.message;err.focus();plan=null;button.textContent='Xem trước';document.getElementById('parity-preview').innerHTML='';}
      finally{button.disabled=false;}
    });
  }
  function exportCare(){
    const codes=new Set(people().map(s=>s.id)),rows=[['Mã','Họ tên','Hoạt động','Nội dung','Người phụ trách','Ngày hẹn','Trạng thái','Cập nhật']];
    for(const n of ctx.state().careNotes||[])if(codes.has(n.code))rows.push([n.code,people().find(s=>s.id===n.code)?.name,n.kind,n.content,n.actor,n.due_day,n.status,n.updated_at]);
    downloadBlob(csvText(rows),`NhatKyChamSoc-${details.className}-${today()}.csv`,'text/csv;charset=utf-8');
  }
  async function printReport(kind) {
    const win=window.open('','_blank');if(!win)throw new Error('Cho phép mở cửa sổ in trên trình duyệt.');win.opener=null;
    const scoped=people(),range=document.getElementById('parity-report-range').value,month=document.getElementById('parity-report-month').value;
    let title,headers,rows;
    try {
      if(kind==='roster'){title='Danh sách lớp';headers=['Mã','Tên thánh','Họ tên','Giới tính','Ngày sinh','Tên cha','Tên mẹ','Tên phụ huynh','SĐT phụ huynh 1','SĐT phụ huynh 2','Liên hệ khác'];rows=scoped.map(s=>{const n=parentNames(s.parents),p=parentPhones(s.phone);return [s.id,s.saintName,s.fullName,s.gender,s.birthDate,n.fatherName,n.motherName,n.guardianName,p.phones[0]||'',p.phones[1]||'',[...p.phones.slice(2),p.phoneNote].filter(Boolean).join('; ')];});}
      else if(kind==='attendance'){
        title=`Chuyên cần · ${range==='year'?'Cả năm':range==='month'?month:range==='hk1'?'HK I':'HK II'}`;headers=['Mã','Họ tên','Lễ X/P/O','Giáo lý X/P/O','Lễ sớm X/P/O','Lễ bổ sung (cả năm)'];
        const c=classes().find(c=>c.id===classId);rows=scoped.map(s=>{
          const counts=activity=>{const v={X:0,P:0,O:0};for(const [key,m] of Object.entries(ctx.state().marks)){const[d,a,code]=key.split('|');if(code!==s.id||a!==activity)continue;if(range==='month'&&d.slice(0,7)!==month||['hk1','hk2'].includes(range)&&!c.semesterMonths[range].includes(d.slice(0,7)))continue;if(m.status in v)v[m.status]++;}return `${v.X}/${v.P}/${v.O}`;};
          return [s.id,s.name,counts('mass'),counts('lesson'),counts('early'),'…'];
        });
        const g=await api(`grades?classId=${classId}&semester=3`);for(const row of rows)row[5]=g.students.find(s=>s.code===row[0])?.supplementalMass;
      }else{
        const sem=kind==='year'?3:Number(document.getElementById('parity-report-semester').value);
        const g=await api(`grades?classId=${classId}&semester=${sem}`);title=sem===3?'Tổng kết năm':`Bảng điểm HK ${sem}`;
        headers=sem===3?['Mã','Họ tên','HK1','HK2','Giáo Lý','Xếp loại','CC lễ','CC GL','TL tổng hợp','Đánh giá','Tổng','Hạng','Lễ bổ sung']:['Mã','Họ tên',...Array.from({length:20},(_,i)=>'KB'+(i+1)),'KT15','KT1 tiết','Thi Kinh','Thi HK','TB','Xếp loại','Hạng'];
        rows=g.students.map(s=>sem===3?[s.code,s.name,s.diemHk1,s.diemHk2,s.diemGiaoLy,s.xepLoai,s.massScore,s.lessonScore,s.combinedMassScore,s.assessment,s.totalScore,s.yearRank,s.supplementalMass]:[s.code,s.name,...s.khaoBai,s.kt15,s.kt1Tiet,s.thiKinh,s.thiHk,s.tbHk,s.xepLoai,s.xepHang]);
      }
      win.document.write(`<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>@page{size:A4 landscape;margin:12mm}body{font:14px Arial,sans-serif;color:#111;margin:20px}h1{font-size:22px}table{width:100%;border-collapse:collapse;font-size:${kind==='term'?9:12}px}th,td{border:1px solid #999;padding:5px;overflow-wrap:anywhere;text-align:left}thead{display:table-header-group}tr{break-inside:avoid}button{padding:12px;font:inherit}.wrap{overflow:auto}@media print{button{display:none}body{margin:0}.wrap{overflow:visible}}</style><p>GIÁO XỨ XUÂN HOÀ · ${esc(ctx.year())}</p><h1>${esc(title)}</h1><p>${esc(details.className)} · ${rows.length} em · Xuất ${esc(today())}</p><button id="print">In / Lưu PDF</button><div class="wrap"><table><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${esc(gradeValue(v))}</td>`).join('')}</tr>`).join('')}</tbody></table></div></html>`);win.document.close();win.document.getElementById('print').addEventListener('click',()=>win.print());
    }catch(e){win.close();throw e;}
  }
  document.addEventListener('click',async e=>{
    const target=e.target.closest('[data-parity]');if(!target)return;
    try{
      const op=target.dataset.parity;
      if(op==='refresh')await load();
      else if(op==='export-care')exportCare();
      else if(op.startsWith('print-'))await printReport(op.slice(6));
      else if(op==='bulk-template'){
        const sem=Number(document.querySelector('#parity-form [name=semester]').value),g=await api(`grades?classId=${classId}&semester=${sem}`);
        downloadBlob(g.students.map(s=>[s.code,...s.khaoBai,s.kt15,s.kt1Tiet,s.thiKinh,s.thiHk].map(v=>v??'').join('\t')).join('\n'),`Diem-HK${sem}-${details.className}.tsv`,'text/tab-separated-values;charset=utf-8');
      }else await open(op,target);
    }catch(e){toast(e.message);}
  });
  document.addEventListener('change',e=>{if(e.target.id==='parity-class')load(e.target.value);});
  document.addEventListener('input',e=>{if(e.target.closest('#parity-form')){plan=null;document.getElementById('parity-submit').textContent='Xem trước';document.getElementById('parity-preview').innerHTML='';}});
  document.addEventListener('submit',e=>{if(e.target.id==='parity-form')submit(e);});
  function bind(){document.getElementById('parity-dialog').addEventListener('close',()=>{opener?.focus({preventScroll:true});});}
  return {clear:()=>{loadToken++;classId='';details=null;loading=false;plan=null;fixed={};opener=null;},page,dialogs,load,bind,ready:()=>loading||(details&&(!ctx.workingClass?.()||ctx.workingClass?.()==='all'||details.className===ctx.workingClass?.()))};
}
