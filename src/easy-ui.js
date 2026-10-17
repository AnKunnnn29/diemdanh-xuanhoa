/* Hallmark · pre-emit critique: P4 H5 E4 S5 R5 V4 · existing parish theme · motion: cut */
export function flowSteps(stage='setup') {
  const current={setup:0,scan:1,review:2,finished:3}[stage]??0;
  return `<ol class="easy-steps" aria-label="Các bước điểm danh">${['Chọn buổi','Điểm danh','Kiểm tra','Tải sổ'].map((label,n)=>`<li ${n===current?'aria-current="step"':''} class="${n<current?'done':''}"><span aria-hidden="true">${n+1}</span>${label}</li>`).join('')}</ol>`;
}
import {gradeFields, scorePattern, scoreValue, dailyWork} from './ux-utils.js';
import {celebrationEvents} from './celebrations.js';

export function startPage({esc,i,workingClass,today,longDate,students,requests,sessions=[],careNotes=[]}) {
  const scoped=students.filter(s=>!workingClass||workingClass==='all'||s.className===workingClass);
  const codes=new Set(scoped.map(s=>s.id));
  const pending=requests.filter(r=>r.status==='pending'&&codes.has(r.code)).length;
  return `<section class="easy-start"><div class="page-heading"><div><h1>Hôm nay bạn muốn làm gì?</h1><p>${esc(longDate(today()))}</p></div></div><p class="easy-class-note" ${workingClass?'hidden':''}>${workingClass?`Lớp đang chọn: <strong>${esc(workingClass==='all'?'Tất cả lớp':workingClass)}</strong>`:'Chọn lớp ở phía trên để dùng cho các công việc bên dưới.'}</p><div class="easy-tasks">${[['attendance','qr','Điểm danh hôm nay','Quét thẻ hoặc nhập tên khi em quên thẻ.'],['students','search','Tìm thiếu nhi','Xem hồ sơ và số liên lạc phụ huynh.'],['grades','chart','Nhập điểm','Chọn em và loại điểm cần nhập.'],['files','download','Tải sổ lớp','Tải sổ có điểm danh và kết quả học tập.']].map(([a,icon,label,help],n)=>`<div class="easy-task ${n===0?'primary':''}"><button class="button ${n===0?'button-primary':'button-secondary'}" data-easy-action="${a}">${i(icon)}${label}</button><p>${help}</p></div>`).join('')}</div>${workReminders({esc,i,workingClass,today,students,requests,sessions,careNotes})}${pending?`<a class="easy-reminder" href="#requests">${i('calendar')}Có ${pending} đơn đang chờ xử lý ${i('arrow')}</a>`:''}<details class="easy-help"><summary>Hướng dẫn nhanh</summary><ol><li>Chọn lớp ở đầu trang.</li><li>Chọn việc cần làm, đọc hướng dẫn ngay trên màn hình.</li><li>Khi điểm danh xong, kiểm tra danh sách rồi kết thúc buổi.</li></ol><p>Nếu camera chưa mở được, bạn có thể nhập tên hoặc mã trên thẻ.</p></details></section>`;
}
export function attendanceSetup({esc,classes,draft,error='',activities,maxDate='',setupAnimation=''}) {
  return `${flowSteps('setup')}<section class="card easy-setup"><div class="card-body"><div class="setup-welcome"><div><h2>Kiểm tra buổi điểm danh</h2><p>Chọn đúng lớp, ngày và hoạt động trước khi bắt đầu.</p></div>${setupAnimation}</div><form id="attendance-setup-form"><label class="field">Lớp cần điểm danh<select id="quick-scope" name="scope" required><option value="">Chọn lớp…</option><option value="all" ${draft.scope==='all'?'selected':''}>Tất cả lớp</option>${classes.map(c=>`<option value="${esc(c.name)}" ${draft.scope===c.name?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><div class="dialog-fields"><label class="field">Ngày điểm danh<input type="date" id="quick-date" name="date" value="${esc(draft.date)}" ${maxDate?`max="${esc(maxDate)}"`:''} required></label><label class="field">Hoạt động<select id="quick-activity" name="activity">${Object.entries(activities).map(([v,label])=>`<option value="${v}" ${draft.activity===v?'selected':''}>${label}</option>`).join('')}</select></label></div><p id="attendance-setup-error" role="alert">${esc(error)}</p><p class="field-help">Giáo lý và lễ sớm chỉ vào Chủ Nhật. Lễ sớm từ 06:00 đến 06:20.</p><button type="submit" class="button button-primary" id="begin-attendance">Bắt đầu điểm danh</button></form></div></section>`;
}
export function gradeEditor(student,{esc,kind='kt15'}) {
  const fields=gradeFields.map(([name,label])=>[name,label,scoreValue(student,name)]);
  return `<div class="grade-entry-toolbar"><label class="field" id="grade-kind-label">Loại điểm<select id="grade-kind">${fields.map(([name,label])=>`<option value="${name}" ${name===kind?'selected':''}>${label}</option>`).join('')}</select></label><button type="button" class="button button-secondary" id="grade-show-all" aria-expanded="false" aria-controls="grade-fields">Nhập nhiều loại điểm</button></div><p id="grades-score-help" class="field-help">Nhập điểm từ 0 đến 10. Để trống nếu chưa có điểm; điểm 0 vẫn được tính.</p><div id="grade-fields" class="easy-grade-fields" data-entry="single">${fields.map(([name,label,value])=>`<label class="field" data-grade-field="${name}" ${name===kind?'':'hidden'}>${label}<input type="text" name="${name}" inputmode="decimal" pattern="${scorePattern}" value="${esc(value??'')}" class="grade-cell-input" aria-describedby="grades-score-help grades-dialog-error" placeholder="Nhập điểm"></label>`).join('')}</div><button type="button" class="button button-soft" id="grade-permitted" aria-pressed="${String(student.kt15).toUpperCase()==='P'}">${String(student.kt15).toUpperCase()==='P'?'Bỏ nghỉ phép':'Đánh dấu nghỉ phép'}</button>`;
}

export function requestWizard(form,review,validate=()=> '') {
  if(!form.dataset.wizard){
    const stages=['Thiếu nhi và loại đơn','Ngày và hoạt động','Kiểm tra và gửi đơn'].map((label,n)=>{
      const fieldset=document.createElement('fieldset');fieldset.dataset.requestStep=String(n+1);
      const legend=document.createElement('legend');legend.textContent=label;fieldset.append(legend);return fieldset;
    });
    const heading=form.querySelector('.dialog-heading');
    const code=form.querySelector('#request-code').closest('label'),kind=form.querySelector('#request-kind').closest('label');
    stages[0].append(code,form.querySelector('#request-students'),form.querySelector('#request-person'),kind);
    stages[1].append(form.querySelector('.dialog-fields'),form.querySelector('#request-calendar-help'));
    stages[2].append(form.querySelector('[name=reason]').closest('label'),form.querySelector('[name=actor]').closest('label'));
    const summary=document.createElement('div');summary.id='request-review';summary.className='request-review';stages[2].prepend(summary);
    const progress=document.createElement('p');progress.id='request-progress';progress.className='wizard-progress';progress.setAttribute('aria-live','polite');heading.after(progress,...stages);
    const nav=document.createElement('div');nav.className='wizard-actions';nav.innerHTML='<button type="button" class="button button-secondary" id="request-previous">Quay lại bước trước</button><button type="button" class="button button-primary" id="request-next">Tiếp tục</button>';
    form.querySelector('.dialog-actions').before(nav);
    form.dataset.wizard='true';
    form.addEventListener('submit',event=>{if(form.dataset.step!=='3'){event.preventDefault();event.stopPropagation();advance();}});
    form.querySelector('#request-next').addEventListener('click',advance);
    form.querySelector('#request-previous').addEventListener('click',()=>show(Number(form.dataset.step)-1));
    function advance(){
      const current=stages[Number(form.dataset.step)-1];
      for(const input of current.querySelectorAll('input,select,textarea'))if(!input.disabled&&!input.closest('[hidden]')&&!input.reportValidity())return;
      const error=validate(Number(form.dataset.step));
      form.querySelector('#request-error').textContent=error;
      if(error){form.querySelector('#request-error').focus();return;}
      show(Math.min(3,Number(form.dataset.step)+1));
    }
    function show(step){
      form.dataset.step=String(step);
      stages.forEach((stage,n)=>{stage.hidden=n+1!==step;stage.disabled=step!==3&&n+1!==step;});
      progress.textContent=`Bước ${step} / 3 · ${stages[step-1].querySelector('legend').textContent}`;
      form.querySelector('#request-previous').hidden=step===1;form.querySelector('#request-next').hidden=step===3;
      form.querySelectorAll('.dialog-actions button[type=submit]').forEach(button=>button.hidden=step!==3);
      summary.textContent=step===3?review():'';
      stages[step-1].querySelector('input:not([type=hidden]),select,textarea')?.focus({preventScroll:true});
    }
    form._showRequestStep=show;
  }
  form._showRequestStep(1);
}

function workReminders({esc,i,workingClass,today,students,requests,sessions,careNotes}){
  const work=dailyWork({students,requests,sessions,careNotes,className:workingClass,date:today()});
  const occasions=celebrationEvents(students,{today:today(),className:workingClass||'all'}).length;
  const links=[...work.sessions.filter(s=>s.scope!=='all'||workingClass==='all').slice(0,1).map(s=>`<button type="button" class="button button-secondary" data-open-session="${esc(s.id)}">${i('qr')}Tiếp tục buổi hôm nay</button>`),
    work.makeups?`<a class="button button-secondary" href="#requests">${work.makeups} lịch lễ bù đến hạn</a>`:'',
    work.care?`<a class="button button-secondary" href="#care">${work.care} việc chăm sóc đến hẹn</a>`:'',
    occasions?`<a class="button button-secondary" href="#celebrations">${occasions} dịp sinh nhật / bổn mạng trong 7 ngày tới</a>`:''].filter(Boolean);
  return links.length?`<section class="easy-today"><h2>Việc cần xử lý</h2><div class="feature-actions">${links.join('')}</div><p class="field-help">Theo lớp đang chọn. Kiểm tra trước khi kết thúc buổi.</p></section>`:'';
}
