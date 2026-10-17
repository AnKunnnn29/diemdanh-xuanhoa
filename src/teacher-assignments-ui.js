import plan from './data/parish-year.json';

export const teacherSlots=[['glv1','GLV 1'],['glv2','GLV 2'],['glv3','GLV 3'],['souer','Soeur đồng hành']];
const normalize=text=>String(text).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
export function classStaffPlan(name,year,groups=[]){return year===plan.year?groups.find(c=>c.name===name)?.staffPlan:null;}
export function createTeacherAssignmentsUI({classes,state,esc,i,year}){
  let query='',status='all';
  function filter(){
    const words=normalize(query).split(/\s+/).filter(Boolean);let count=0;
    document.querySelectorAll('[data-teacher-card]').forEach(card=>{
      const matches=words.every(word=>card.dataset.staffSearch.includes(word))&&(status==='all'||card.dataset.staffStatus===status);
      card.hidden=!matches;if(matches)count++;
    });
    const result=document.getElementById('teacher-results');if(result)result.textContent=`${count} / ${classes().length} lớp`;
    const empty=document.getElementById('teacher-empty');if(empty)empty.hidden=count>0;
  }
  document.addEventListener('input',event=>{if(event.target.id==='teacher-search'){query=event.target.value;filter();}});
  document.addEventListener('change',event=>{if(event.target.id==='teacher-status'){status=event.target.value;filter();}});
  function page(){
    const all=classes(),assigned=all.filter(c=>Object.values(c.teachers||{}).some(Boolean)).length;
    const people=new Set(all.flatMap(c=>Object.values(c.teachers||{})).filter(Boolean));
    queueMicrotask(filter);
    return `<section aria-labelledby="teachers-title"><div class="page-heading"><div><h1 id="teachers-title">Phân công giáo lý viên</h1><p>Xem người phụ trách từng lớp, tìm theo tên và cập nhật phân công.</p></div>${state().isManager?'<div class="feature-actions"><button type="button" class="button button-primary" data-intake-class>Tạo lớp mới</button><a class="button button-secondary" href="#staff">Hồ sơ & liên hệ GLV</a><a class="button button-secondary" href="#accounts">Tài khoản</a></div>':''}</div>
      <section class="workspace-facts" aria-label="Tình hình phân công"><span><strong>${assigned} / ${all.length}</strong> lớp có người phụ trách</span><span><strong>${people.size}</strong> GLV & Soeur</span><small>Năm học ${esc(year())}</small></section>
      <div class="teacher-toolbar"><label class="field">Tìm lớp hoặc giáo lý viên<input type="search" id="teacher-search" value="${esc(query)}" placeholder="Tên lớp, tên GLV…" autocomplete="off"></label><label class="field">Tình trạng phân công<select id="teacher-status">${[['all','Tất cả lớp'],['assigned','Đã có người phụ trách'],['unassigned','Chưa có người phụ trách']].map(([value,label])=>`<option value="${value}" ${status===value?'selected':''}>${label}</option>`).join('')}</select></label></div>
      <p id="teacher-results" role="status" aria-live="polite" class="teacher-source-note"></p>
      <div class="teachers-grid">${all.map(c=>{
        const source=classStaffPlan(c.name,year(),all),teachers=c.teachers||{},hasStaff=Object.values(teachers).some(Boolean);
        return `<article class="teacher-card" data-teacher-card="${esc(c.id)}" data-staff-status="${hasStaff?'assigned':'unassigned'}" data-staff-search="${esc(normalize([c.name,...Object.values(teachers),...(source?.futureTeachers||[]).map(t=>t.name)].join(' ')))}">
          <div class="teacher-card-head"><div><h2 class="teacher-card-title">${esc(c.name)}</h2><small>${c.count} thiếu nhi${source?.location?' · '+esc(source.location):''}</small></div><span class="class-pill">${hasStaff?'Đã phân công':'Chưa phân công'}</span></div>
          <dl class="teacher-roles-list">${teacherSlots.map(([slot,label])=>`<div class="teacher-role-row"><dt class="teacher-role-label">${label}</dt><dd class="teacher-role-val">${esc(teachers[slot]||'Chưa phân công')}</dd></div>`).join('')}</dl>
          ${source?.futureTeachers.length?`<div class="teacher-plan-note">${source.futureTeachers.map(t=>`<p><strong>${esc(t.name)} · ${esc(t.term)}</strong><br>${esc(t.note)}</p>`).join('')}</div>`:''}
          ${state().isManager?`<button type="button" class="button button-secondary" data-edit-teachers="${esc(c.id)}" aria-label="Chỉnh phân công ${esc(c.name)}">${i('teacher')}Chỉnh phân công</button>`:''}
        </article>`;
      }).join('')}</div><p id="teacher-empty" class="teacher-empty" hidden>Không có lớp phù hợp. Thử tên khác hoặc chọn tất cả tình trạng.</p>
      </section>`;
  }
  return {page};
}
