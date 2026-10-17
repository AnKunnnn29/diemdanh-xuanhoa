import {gradeFields, scorePattern, scoreValue, normalizedScore, matchesSearch, gradesMatch} from './ux-utils.js';

export function createGradeColumnUI({data, api, queueWrite, update, esc, render, kind, rememberKind}) {
  const drafts=new Map();
  let visible=false, message='',conflict=false,latest=null,lastContext='';
  let saving=false,pending=null;
  const key=()=>`${data().classId}|${data().semester}|${kind()}`;
  function draft() {
    const book=data();
    if(!drafts.has(key()))drafts.set(key(),{revision:book.revision,values:new Map()});
    if(!drafts.get(key()).values.size)drafts.get(key()).revision=book.revision;
    return drafts.get(key());
  }
  function reset(){visible=false;message='';}
  function toggle(){if(saving)return;visible=!visible;message='';render();}
  function changeKind(value){if(saving)return;rememberKind(value);message='';conflict=false;latest=null;render();}
  function input(element){
    if(saving)return;
    draft().values.set(element.dataset.columnCode,element.value);
    if(element.validity.valid){element.removeAttribute('aria-invalid');element.closest('label')?.querySelector('.grade-field-error')?.remove();element.setAttribute('aria-describedby','grade-column-help grade-column-message');}
  }
  function page(query='') {
    const book=data();
    if(!visible||!book?.revision||![1,2].includes(book.semester))return '';
    if(lastContext!==key()){message='';conflict=false;latest=null;lastContext=key();}
    const current=draft(),field=kind(),label=gradeFields.find(([k])=>k===field)?.[1];
    const rows=book.students.filter(s=>matchesSearch(`${s.name} ${s.code}`,query));
    return `<section class="card grade-column-panel"><div class="card-body"><h2>Nhập cùng loại điểm</h2>
      <p>${esc(book.className)} · Học kỳ ${book.semester}. Enter để sang em tiếp theo; chỉ các ô thay đổi được lưu.</p>
      <label class="field">Loại điểm<select id="grade-column-kind" ${saving?'disabled':''}>${gradeFields.map(([k,l])=>`<option value="${k}" ${k===field?'selected':''}>${l}</option>`).join('')}</select></label>
      <form id="grade-column-form" ${saving?'aria-busy="true"':''}><p id="grade-column-help" class="field-help">Nhập 0–10, P nếu nghỉ phép, hoặc để trống. Bản nháp được giữ khi chuyển trang; bấm Lưu để ghi nhận.</p>
      <div class="grade-column-rows">${rows.map(s=>`<label class="grade-column-row"><span><strong>${esc(s.name)}</strong><small>${esc(s.code)}</small></span><input id="column-${esc(s.code)}" data-column-code="${esc(s.code)}" type="text" ${saving?'disabled':''} inputmode="decimal" pattern="${scorePattern}" value="${esc(current.values.has(s.code)?current.values.get(s.code):scoreValue(s,field)??'')}" aria-label="${esc(label+' của '+s.name)}" aria-describedby="grade-column-help grade-column-message"></label>`).join('')}</div>
      ${rows.length?'':'<p>Không có em phù hợp. Xóa từ khóa để xem cả lớp.</p>'}
      <p id="grade-column-message" role="status" aria-live="polite">${esc(message)}</p>
      ${conflict?'<button type="button" class="button button-secondary" id="review-grade-column">Đối chiếu điểm mới với bản nháp</button>':''}
      ${latest?`<section class="grade-draft-review" aria-label="Đối chiếu bản nháp"><h3>Điểm hiện tại và bản nháp của bạn</h3><p>Chỉ các ô bạn đã nhập được giữ. Các loại điểm khác dùng dữ liệu mới nhất. Kiểm tra trước khi tiếp tục lưu.</p><ul>${[...current.values].map(([code,value])=>{const student=latest.students.find(s=>s.code===code);return student?`<li><strong>${esc(student.name)}</strong>: hiện tại ${esc(scoreValue(student,field)??'Chưa nhập')} → bản nháp ${esc(value||'Chưa nhập')}</li>`:'';}).join('')}</ul><button type="button" class="button button-secondary" id="accept-grade-column">Dùng điểm mới, giữ các ô tôi đã nhập</button></section>`:''}
      <div class="feature-actions"><button type="submit" id="save-grade-column" class="button button-primary" ${rows.length&&!saving?'':'disabled'}>Lưu các điểm đã thay đổi</button><button type="button" class="button button-secondary" data-toggle-grade-column ${saving?'disabled':''}>Quay lại xem điểm</button></div></form></div></section>`;
  }
  async function submit(event) {
    event.preventDefault();
    const book=data(),field=kind(),current=draft(),button=event.target.querySelector('[type=submit]');
    const grades=[];
    for(const [code,value] of current.values){
      const student=book.students.find(s=>s.code===code);
      if(!student||normalizedScore(value)===normalizedScore(scoreValue(student,field)))continue;
      const score=normalizedScore(value);
      if(score!=='P'&&score!==null&&(!Number.isFinite(score)||score<0||score>10)){
        message='Điểm phải từ 0 đến 10, P hoặc để trống.';
        const input=document.getElementById('column-'+code);input?.setAttribute('aria-invalid','true');input?.focus();
        document.getElementById('grade-column-message').textContent=message;return;
      }
      if(field.startsWith('kb_')){
        const scores=Array.from({length:20},(_,i)=>student.khaoBai?.[i]??null);scores[Number(field.slice(3))]=score;
        grades.push({code,khaoBai:scores});
      }else grades.push({code,[field]:score});
    }
    if(!grades.length){message='Chưa có điểm thay đổi cần lưu.';document.getElementById('grade-column-message').textContent=message;return;}
    button.disabled=true;event.target.setAttribute('aria-busy','true');
    saving=true;event.target.querySelectorAll('input').forEach(input=>input.disabled=true);document.getElementById('grade-column-kind').disabled=true;
    message='Đang lưu điểm cho '+grades.length+' em…';document.getElementById('grade-column-message').textContent=message;
    await queueWrite(async()=>{
      try{
        const result=await api('grades',{classId:book.classId,semester:book.semester,expectedRevision:current.revision,grades});
        drafts.delete(`${book.classId}|${book.semester}|${field}`);
        for(const [draftKey,other] of drafts)if(draftKey.startsWith(`${book.classId}|${book.semester}|`)&&other.revision===current.revision)other.revision=result.grades.revision;
        update(result);
        message=result.excelReady===false?result.message:`Đã lưu điểm cho ${grades.length} em.`;render();
      }catch(error){if(error.uncertain)pending={classId:book.classId,semester:book.semester,field,grades,revision:current.revision};message=error.message;conflict=error.status===409&&/phiên khác/.test(error.message);if(conflict)render();else document.getElementById('grade-column-message').textContent=message;}
      finally{saving=false;button.disabled=false;document.getElementById('grade-column-form')?.removeAttribute('aria-busy');document.querySelectorAll('[data-column-code],#grade-column-kind,#save-grade-column,[data-toggle-grade-column]').forEach(input=>input.disabled=false);}
    });
  }
  async function review(){
    const book=data(),originalKey=key(),button=document.getElementById('review-grade-column');button.disabled=true;
    try{const result=await api(`grades?classId=${encodeURIComponent(book.classId)}&semester=${book.semester}`);if(key()===originalKey){latest=result;render();}}
    catch(error){message=error.message;document.getElementById('grade-column-message').textContent=message;}
    finally{button.disabled=false;}
  }
  function accept(){
    if(!latest)return;
    draft().revision=latest.revision;update({grades:latest});latest=null;conflict=false;
    message='Bản nháp đã được đối chiếu. Kiểm tra các ô rồi bấm Lưu để ghi nhận.';render();
  }
  async function verifyPending(){
    if(!pending)return;
    const attempt=pending,fresh=await api(`grades?classId=${encodeURIComponent(attempt.classId)}&semester=${attempt.semester}`);
    if(gradesMatch(fresh,attempt.grades)){
      drafts.delete(`${attempt.classId}|${attempt.semester}|${attempt.field}`);
      if(data()?.classId===attempt.classId&&data()?.semester===attempt.semester){update({grades:fresh});message='Đã kiểm tra: các điểm vừa nhập đã được ghi nhận. Không cần lưu lại.';}
    }else if(fresh.revision!==attempt.revision){conflict=true;message='Bảng điểm đã thay đổi. Đối chiếu điểm mới với bản nháp trước khi lưu.';}
    else message='Lượt lưu vừa rồi chưa được ghi nhận. Bản nháp vẫn được giữ; bạn có thể bấm Lưu.';
    pending=null;
  }
  return {clear:()=>{drafts.clear();visible=false;message="";conflict=false;latest=null;pending=null;lastContext="";},page,toggle,changeKind,input,submit,review,accept,verifyPending,reset,isVisible:()=>visible,hasPending:()=>!!pending};
}
