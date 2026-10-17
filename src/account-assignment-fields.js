export const assignmentSlots=[['glv1','GLV 1'],['glv2','GLV 2'],['glv3','GLV 3'],['souer','Soeur đồng hành']];
export function assignmentRow({classes,accounts,esc,targetId='',selected={}}){
 const classId=selected.class_id||'',slot=selected.slot||'glv1';
 return `<div class="account-assignment-row"><label class="field">Lớp phụ trách<select data-assignment-class><option value="">Chưa phân công</option>${classes.filter(c=>!c.archived||c.id===classId).map(c=>`<option value="${esc(c.id)}" ${classId===c.id?'selected':''}>${esc(c.name)}${c.archived?' · Đã lưu trữ':''}</option>`).join('')}</select></label><label class="field">Vị trí<select data-assignment-slot>${slotOptions({classId,slot,accounts,esc,targetId})}</select></label><button type="button" class="button button-secondary" data-assignment-remove aria-label="Bỏ lớp khỏi phân công">Bỏ lớp</button></div>`;
}
export function slotOptions({classId,slot,accounts,esc,targetId}){
 return assignmentSlots.map(([key,label])=>{
  const occupant=accounts.find(a=>a.id!==targetId&&(a.assignments||[]).some(s=>s.class_id===classId&&s.slot===key));
  return `<option value="${key}" ${slot===key?'selected':''} ${occupant?'disabled':''}>${label}${occupant?' · '+esc(occupant.displayName):''}</option>`;
 }).join('');
}
export function assignmentFields(ctx,selections=[]){
 return `<fieldset class="account-assignment-fields" data-assignment-target="${ctx.esc(ctx.targetId||'')}"><legend>Phân công lớp</legend><div data-assignment-rows>${(selections.length?selections:[{}]).map(selected=>assignmentRow({...ctx,selected})).join('')}</div><button type="button" class="button button-secondary" data-assignment-add>Thêm lớp phụ trách</button><p class="field-help">Có thể chọn lớp ngay hoặc để phân công sau. Vị trí đã có người phụ trách sẽ không bị ghi đè. Admin vẫn có quyền truy cập toàn bộ lớp.</p></fieldset>`;
}
export function collectAssignments(form){
 const selections=[...form.querySelectorAll('.account-assignment-row')].map(row=>({classId:row.querySelector('[data-assignment-class]').value,slot:row.querySelector('[data-assignment-slot]').value})).filter(row=>row.classId);
 if(new Set(selections.map(row=>row.classId)).size!==selections.length)throw new Error('Mỗi lớp chỉ chọn một vị trí cho tài khoản này.');
 if(selections.some(row=>!row.slot))throw new Error('Chọn một vị trí còn trống cho lớp.');
 return selections;
}
