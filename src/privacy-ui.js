import {contactFields,parentContactMarkup} from './parent-contacts.js';

export function createPrivacyUI({api,esc,state,classes,applyServer,render,toast}) {
  const allowed=(cap,cid)=>(state().access?.[cap]||[]).includes(cid);
  let verifiedUntil=0,verifyResolve=null;
  document.body.insertAdjacentHTML('beforeend',`
  <dialog id="privacy-reauth-dialog" aria-labelledby="privacy-reauth-title"><form id="privacy-reauth-form"><h2 id="privacy-reauth-title">Xác thực để tải hồ sơ</h2><p>File có thể chứa thông tin riêng của các em và phụ huynh. Chỉ lưu ở nơi được bảo vệ.</p><label class="field">Mật khẩu hiện tại<input type="password" name="reauthPassword" required autocomplete="current-password" maxlength="128"></label><p id="privacy-reauth-error" role="alert"></p><div class="dialog-actions"><button type="button" data-close-dialog class="button button-secondary">Hủy</button><button type="submit" class="button button-primary">Xác thực</button></div></form></dialog>`);
  function slot(s){
    return `<section class="card p-4" id="private-contact-slot"><h3>Liên hệ gia đình</h3>${allowed('contactRead',s.classId)?`<button type="button" class="button button-secondary" data-contact-view="${esc(s.id)}">Xem liên hệ phụ huynh</button><p class="field-help">Mỗi lần mở liên hệ được ghi vào nhật ký truy cập.</p>`:'<p>Chỉ xem được liên hệ của lớp mình phụ trách.</p>'}<p id="private-contact-error" role="status" aria-live="polite"></p></section>`;
  }
  document.addEventListener('click',async event=>{
    const contact=event.target.closest('[data-contact-view]');
    if(contact){
      const code=contact.dataset.contactView,slot=document.getElementById('private-contact-slot');
      contact.disabled=true;const error=document.getElementById('private-contact-error');error.textContent='Đang kiểm tra quyền…';
      try{
        const result=await api('student-contact-view',{code});
        const dialog=document.getElementById('profile-dialog');
        if(!dialog.open||dialog.querySelector('[name=code]')?.value!==code||!slot.isConnected)return;
        const person=state().studentDirectory?.find(s=>s.id===code),cid=person?.classId;
        slot.innerHTML=`<h3>Liên hệ gia đình</h3>${allowed('contactWrite',cid)?contactFields(result.contact,{esc})+`<label class="field">Địa chỉ<input name="address" value="${esc(result.contact.address)}" maxlength="500" autocomplete="off"></label>`:parentContactMarkup(result.contact,{esc})+`<p>${esc(result.contact.address)}</p>`}<p class="field-help">Liên hệ chỉ hiển thị trong cửa sổ này.</p>`;
      }catch(e){if(error.isConnected)error.textContent=e.message;}finally{if(contact.isConnected)contact.disabled=false;}
    }
  });
  document.addEventListener('submit',async event=>{
    const form=event.target;
    if(form.id!=='privacy-reauth-form')return;
    event.preventDefault();const button=form.querySelector('[type=submit]');button.disabled=true;
    const error=document.getElementById('privacy-reauth-error');error.textContent='';
    try{
      await api('auth/reauth',{password:form.elements.reauthPassword.value});verifiedUntil=Date.now()+240000;
      verifyResolve?.(true);verifyResolve=null;form.closest('dialog').close();
    }catch(e){error.textContent=e.message;}finally{form.elements.reauthPassword&&(form.elements.reauthPassword.value='');button.disabled=false;}
  });
  document.getElementById('privacy-reauth-dialog').addEventListener('close',()=>{
    document.getElementById('privacy-reauth-form').reset();verifyResolve?.(false);verifyResolve=null;
  });
  document.getElementById('profile-dialog').addEventListener('close',()=>document.getElementById('profile-dialog-content').replaceChildren());
  return {slot,allowed,clear:()=>{verifiedUntil=0;verifyResolve?.(false);verifyResolve=null;document.getElementById('privacy-reauth-dialog').close();},
    confirmExport:()=>{if(verifiedUntil>Date.now())return Promise.resolve(true);document.getElementById('privacy-reauth-error').textContent='';document.getElementById('privacy-reauth-dialog').showModal();return new Promise(resolve=>{verifyResolve=resolve;});}};
}
