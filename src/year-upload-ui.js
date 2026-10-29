export function createYearUploadUI({api,esc}){
 let stop=()=>{};
 function clear(){stop();stop=()=>{};}
 function mount(host){
  clear();let alive=true,files=[],entries=new Map(),errors=new Map(),plan=null,uploadedYear=null;
  const controller=new AbortController(),form=host.closest('form'),dialog=host.closest('dialog');
  stop=()=>{alive=false;files=[];entries.clear();errors.clear();plan=null;controller.abort();};
  host.innerHTML=`<p>Chuẩn bị các sổ .xlsm đã xếp thiếu nhi vào lớp năm mới và cập nhật lịch học trong Excel, sau đó chọn toàn bộ sổ cần nhập.</p><p data-year-upload-year class="field-help"></p><label class="button button-secondary year-file-picker">Chọn hoặc thêm sổ lớp .xlsm<input class="sr-only" type="file" accept=".xlsm" multiple data-year-files aria-describedby="year-file-limits"></label><p class="field-help" id="year-file-limits">Mỗi sổ tối đa 1,9 MB, tối đa 60 sổ. Có thể chọn thêm hoặc bỏ từng file.</p><details data-year-file-details open><summary data-year-file-summary>Các sổ đã chọn</summary><div data-year-file-list></div></details><p data-year-upload-status role="status" aria-live="polite"></p><div data-year-import-preview></div>`;
  const button=()=>document.getElementById('feature-submit');
  function invalidate(){plan=null;host.querySelector('[data-year-import-preview]').replaceChildren();button().textContent='Kiểm tra các sổ Excel';}
  function paint(){if(!alive)return;const year=Number(form.elements.startYear.value);host.querySelector('[data-year-upload-year]').textContent=`Năm học sẽ tạo: ${year}–${year+1}`;host.querySelector('[data-year-file-summary]').textContent=`${files.length} sổ đã chọn · ${entries.size} sổ đã đọc`;host.querySelector('[data-year-file-list]').innerHTML=files.length?`<ul class="year-upload-files">${files.map((file,n)=>{const item=entries.get(file);return `<li><div><strong>${esc(file.name)}</strong><p>${esc(errors.get(file)||(item?`${item.className} · ${item.count} em · ${item.marks} lượt điểm danh`:'Chờ kiểm tra'))}</p></div><button type="button" class="button button-secondary" data-year-remove="${n}" aria-label="Bỏ ${esc(file.name)}">Bỏ file</button></li>`;}).join('')}</ul>`:'<p>Chưa chọn sổ lớp.</p>';}
  host.addEventListener('change',e=>{if(!e.target.matches('[data-year-files]'))return;for(const file of e.target.files){if(!files.some(f=>f.name===file.name&&f.size===file.size&&f.lastModified===file.lastModified))files.push(file);}e.target.value='';host.querySelector('[data-year-file-details]').open=true;invalidate();paint();},{signal:controller.signal});
  host.addEventListener('click',e=>{const remove=e.target.closest('[data-year-remove]');if(!remove)return;const [file]=files.splice(Number(remove.dataset.yearRemove),1);entries.delete(file);errors.delete(file);invalidate();paint();},{signal:controller.signal});
  form.addEventListener('input',e=>{if(e.target.name==='startYear'){entries.clear();errors.clear();uploadedYear=null;invalidate();paint();}},{signal:controller.signal});
  dialog.addEventListener('cancel',e=>{if(form.getAttribute('aria-busy')==='true')e.preventDefault();},{signal:controller.signal});
  function preview(model){host.querySelector('[data-year-file-details]').open=false;
   const omitted=model.omitted||[];
   host.querySelector('[data-year-import-preview]').innerHTML=`<section class="year-import-summary"><h3>Xem trước năm học ${esc(model.year)}</h3><p><strong>${model.classes.length} lớp · ${model.count} thiếu nhi</strong></p><ul>${model.classes.map(c=>`<li>${esc(c.className)}: <strong>${c.count} em</strong></li>`).join('')}</ul><p>Danh sách, hồ sơ, lịch, điểm và điểm danh được lấy từ các sổ đã chọn. Năm hiện tại và lịch sử được giữ nguyên.</p>${omitted.length?`<details><summary>${omitted.length} em năm hiện tại không có trong bộ sổ mới</summary><ul>${omitted.map(p=>`<li>${esc(p.code)} · ${esc(p.name)} · ${esc(p.className)}</li>`).join('')}</ul></details><label class="year-import-ack"><input type="checkbox" data-year-accept-omitted> Tôi đã kiểm tra: ${omitted.length} em này không được đưa vào năm mới.</label>`:''}<p>Khi chuyển sang năm mới, Admin cần phân công lại GLV. Tên GLV trong Excel không tự cấp quyền cho tài khoản.</p><p><strong>Chọn “Tạo năm học ${esc(model.year)}” để xác nhận. Năm mới sẽ ở trạng thái đã chuẩn bị.</strong></p></section>`;
   button().textContent='Tạo năm học '+model.year;
   host.querySelector('[data-year-import-preview]').scrollIntoView({block:'start',behavior:'instant'});
  }
  async function submit(values){
   const year=Number(values.startYear);
   if(plan){
    if(plan.omitted.length&&!host.querySelector('[data-year-accept-omitted]')?.checked)throw Error('Kiểm tra và xác nhận danh sách các em không có trong sổ năm mới.');
    const result=await api('admin/year-workbooks-import',{startYear:year,uploads:files.map(f=>entries.get(f).id),previewToken:plan.token,acceptOmitted:!!host.querySelector('[data-year-accept-omitted]')?.checked,reason:values.reason?.trim()||`Nhập sổ Excel năm học ${year}-${year+1}`});
    return result;
   }
   if(!files.length||files.length>60)throw Error('Chọn từ 1 đến 60 sổ lớp .xlsm để kiểm tra.');
   if(files.some(f=>!f.name.toLowerCase().endsWith('.xlsm')||!f.size||f.size>1900000))throw Error('Cần file .xlsm, mỗi sổ tối đa 1,9 MB. Bỏ file không hợp lệ rồi chọn lại.');
   if(uploadedYear!==year){entries.clear();errors.clear();uploadedYear=year;}
   const selected=[...files];
   for(let n=0;n<selected.length;n++){
    const file=selected[n];if(entries.has(file))continue;
    if(!alive)return null;host.querySelector('[data-year-upload-status]').textContent=`Đang kiểm tra sổ ${n+1}/${selected.length}: ${file.name}`;
    try{
     const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Không đọc được file đã chọn.'));reader.readAsDataURL(file);});
     if(!alive)return null;
     const result=await api('admin/year-workbook-preview',{startYear:year,filename:file.name,fileBase64:base64});
     if(!alive)return null;entries.set(file,result);errors.delete(file);
    }catch(error){if(!alive)return null;errors.set(file,error.message);}
    paint();
   }
   if(!alive)return null;
   host.querySelector('[data-year-upload-status]').textContent=`Đã đọc ${entries.size}/${files.length} sổ.`;
   if(errors.size)throw Error('Có sổ chưa hợp lệ. Xem lỗi dưới tên file, sửa trên Excel rồi bỏ file cũ và tải bản đã sửa lên.');
   const model=await api('admin/year-workbooks-preview',{startYear:year,uploads:files.map(f=>entries.get(f).id)});
   if(!alive)return null;plan=model;preview(model);return null;
  }
  paint();invalidate();return {submit,invalidate};
 }
 return {mount,clear};
}
