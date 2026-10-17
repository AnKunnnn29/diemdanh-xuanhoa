import {welcomeBackdrop,welcomeIdentity} from './welcome-scene.js';
import {matchesSearch} from './ux-utils.js';
import {assignmentFields,assignmentRow,slotOptions,collectAssignments} from './account-assignment-fields.js';

export function createAuthUI({api,esc,page,onReady,onClear,pending,state,classes,render,toast,queueWrite,applyServer,onAccountsChanged,restoreOffline}) {
  let user=null,csrfToken='',mode='login',busy=false,accountQuery='';
  function form(password=false,optional=false) {
    return `<form id="auth-form" class="auth-form" aria-labelledby="auth-title"><div class="auth-form-heading"><h1 id="auth-title">${password?(user?.mustChangePassword?'Đặt mật khẩu mới':'Đổi mật khẩu'):'Đăng nhập'}</h1><p>${password?'Dùng mật khẩu riêng để bảo vệ tài khoản của bạn.':'Cổng giáo lý · Giáo xứ Xuân Hoà'}</p></div>
      ${password?`<p class="auth-account-name"><strong>${esc(user.displayName)}</strong> · ${esc(user.username)}</p>${user.mustChangePassword?'<p class="auth-notice">Bạn đang dùng mật khẩu tạm. Hãy đặt mật khẩu riêng trước khi mở sổ lớp.</p>':''}`:`<label class="field">Tên đăng nhập<input name="username" autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="80" required aria-describedby="auth-error"></label>`}
      ${!password||!user?.mustChangePassword?`<label class="field">${password?'Mật khẩu hiện tại':'Mật khẩu'}<input name="${password?'currentPassword':'password'}" type="password" autocomplete="current-password" maxlength="128" required aria-describedby="auth-error"></label>`:''}
      ${password?'<label class="field">Mật khẩu mới<input name="newPassword" type="password" autocomplete="new-password" minlength="15" maxlength="128" required aria-describedby="password-help auth-error"></label><p id="password-help" class="field-help">Từ 15 ký tự. Có thể dùng một câu dễ nhớ, gồm khoảng trắng.</p><label class="field">Nhập lại mật khẩu mới<input name="confirmPassword" type="password" autocomplete="new-password" minlength="15" maxlength="128" required></label>':''}
      <p id="auth-error" role="alert"></p><button type="submit" class="button auth-submit">${password?'Lưu mật khẩu mới':'Đăng nhập'}</button>
      ${optional?'<button type="button" class="button button-secondary" id="cancel-password">Quay lại</button>':''}
      <p class="field-help">${password?'Mật khẩu mới có hiệu lực ngay sau khi lưu.':'Dùng tài khoản do Admin cấp. Nếu quên mật khẩu, liên hệ ban trị sự để được cấp lại.'}</p></form>`;
  }
  function show(next='login') {
    mode=next;
    document.body.dataset.auth='out';
    page.innerHTML=`<section class="welcome-hero auth-scene-page" data-auth-screen="${next}" aria-labelledby="auth-title">${welcomeBackdrop()}${welcomeIdentity()}<div class="auth-scene-content"><section class="auth-card" data-welcome-enter="0" aria-labelledby="auth-title">${form(next==='password',next==='password'&&!user?.mustChangePassword)}</section></div></section>`;
    if(matchMedia('(min-width:900px)').matches)page.querySelector('[name="username"],[name="currentPassword"],[name="newPassword"]')?.focus({preventScroll:true});
  }
  function clear() {
    user=null;csrfToken='';accountQuery='';onClear();
    document.querySelectorAll('dialog[open]').forEach(d=>d.close());
    document.getElementById('account-credential')?.replaceChildren();
    show();
  }
  async function init() {
    try {
      const result=await api('auth/me');user=result.user;csrfToken=result.csrfToken;
      if(user.mustChangePassword)show('password');else await ready();
    }catch(error){
      const cached=error.network&&restoreOffline?await restoreOffline():null;
      if(cached){user=cached.user;csrfToken='';document.body.dataset.role=user.role;await onReady(user,{offline:cached});document.body.dataset.auth='in';chrome();return;}
      if(error.status===401)show();else {show();document.getElementById('auth-error').textContent='Chưa kết nối được dịch vụ. Tải lại trang để thử lại.';}
    }
  }
  async function refreshSession(){
    const result=await api('auth/me');
    if(!user||user.id!==result.user.id){clear();throw new Error('Tài khoản đã thay đổi. Đăng nhập lại để tiếp tục.');}
    user=result.user;csrfToken=result.csrfToken;
  }
  async function ready(welcome=false) {
    const sessionUser=user;
    document.body.dataset.role=sessionUser.role;
    await onReady(sessionUser,{welcome});
    // Bootstrap may expire the session and mount a fresh login form instead.
    if(user!==sessionUser||page.querySelector('#auth-form'))return;
    document.body.dataset.auth='in';chrome();
  }
  function chrome() {
    if(!user)return;
    const host=document.querySelector('.topbar-right');
    host.innerHTML=`<div class="account-identity"><strong>${esc(user.displayName)}</strong><small>${esc(user.username)} · ${user.role==='Admin'?'Admin · Quản trị':'Giáo lý viên'}</small></div><details class="account-menu"><summary>Tài khoản</summary><div><button type="button" id="change-password" class="button button-secondary">Đổi mật khẩu</button><button type="button" id="auth-logout" class="button button-secondary">Đăng xuất</button></div></details>`;
    document.querySelectorAll('a[href="#management"],a[href="#excel"],a[href="#accounts"],a[href="#administration"],[data-edit-teachers],[data-reconcile-grades]').forEach(el=>el.hidden=user.role!=='Admin');
    document.querySelectorAll('[data-admin-navigation]').forEach(el=>el.hidden=user.role!=='Admin');
    document.querySelectorAll('a[href="#staff"]').forEach(el=>el.hidden=user.role!=='Admin');
    document.querySelectorAll('.actor-input').forEach(el=>{el.value=user.displayName;el.readOnly=true;});
    if(user.role!=='Admin') {
      document.querySelectorAll('#export-class option[value="all"]').forEach(el=>el.remove());
      const all=document.getElementById('export-all');if(all)all.hidden=true;
      document.querySelectorAll('select[name="scope"] option[value="all"],#workspace-class option[value="all"]').forEach(el=>el.remove());
      document.querySelectorAll('select[name="scope"]').forEach(el=>{if(!el.value&&classes().length)el.value=classes()[0].name;});
    }
  }
  function accountsPage() {
    const classLabel=a=>a.role==='Admin'?'Toàn bộ':a.classIds.map(id=>classes().find(c=>c.id===id)?.name||id).join(', ')||'Chưa phân công';
    const searchText=a=>`${a.displayName} ${a.username} ${classLabel(a)}`;
    const count=state().accounts.filter(a=>matchesSearch(searchText(a),accountQuery)).length;
    return `<div class="page-heading"><h1>Tài khoản & phân quyền</h1><p>Cấp tài khoản cho GLV và ban trị sự. Admin xem toàn bộ; GLV truy cập các lớp được phân công.</p></div>
      <section class="card account-create"><h2>Tạo tài khoản</h2><form id="create-account-form"><label class="field">Họ tên<input name="displayName" required minlength="2" maxlength="100" autocomplete="name"></label><label class="field">Vai trò<select name="role"><option value="GLV">GLV · Quản lý lớp được phân công</option><option value="Admin">Admin · Quản trị, truy cập toàn bộ</option></select></label>${assignmentFields({classes:classes(),accounts:state().accounts,esc})}<button type="submit" class="button button-primary">Tạo tài khoản & phân công</button><p id="account-create-error" role="alert"></p></form><p class="field-help">Tên đăng nhập và mật khẩu tạm được tạo tự động. Người dùng phải đổi mật khẩu khi đăng nhập lần đầu.</p></section>
      <p class="account-assign-link"><a href="#teachers" class="button button-secondary">Phân công GLV vào lớp →</a></p>
      <section class="card account-directory"><div class="account-directory-search"><label class="field">Tìm tài khoản<input id="account-search" type="search" value="${esc(accountQuery)}" placeholder="Họ tên, tên đăng nhập hoặc lớp phụ trách…" autocomplete="off" aria-controls="account-rows" aria-describedby="account-search-help"></label><p id="account-search-help" class="field-help">Có thể gõ tên có dấu hoặc không dấu.</p><p id="account-search-results" role="status" aria-live="polite">${count} / ${state().accounts.length} tài khoản</p></div><div class="table-scroll"><table><caption>Danh sách tài khoản (${state().accounts.length})</caption><thead><tr><th>Họ tên / Đăng nhập</th><th>Vai trò</th><th>Lớp phụ trách</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody id="account-rows">${state().accounts.map(a=>`<tr data-account-search="${esc(searchText(a))}" ${matchesSearch(searchText(a),accountQuery)?'':'hidden'}><td><strong>${esc(a.displayName)}</strong><br><small>${esc(a.username)}</small></td><td>${esc(a.role)}</td><td>${esc(classLabel(a))}</td><td>${a.active?(a.mustChangePassword?'Chờ đổi mật khẩu':'Đang hoạt động'):'Đã khoá'}</td><td><div class="account-row-actions"><button type="button" class="button button-secondary" data-account-assign="${esc(a.id)}" aria-label="Phân công hoặc đổi lớp cho ${esc(a.displayName)}">${a.assignments?.length?'Đổi lớp':'Phân công'}</button>${a.id===user.id?'<small>Tài khoản của bạn</small>':`<button type="button" class="button button-secondary" data-account-edit="${esc(a.id)}">Quản lý</button>`}</div></td></tr>`).join('')}<tr id="account-search-empty" ${count?'hidden':''}><td colspan="5">Không tìm thấy tài khoản phù hợp. Thử tên đăng nhập hoặc từ khóa khác.</td></tr></tbody></table></div></section>`;
  }
  document.addEventListener('input',event=>{
    if(event.target.id!=='account-search')return;
    accountQuery=event.target.value;
    let count=0;
    document.querySelectorAll('[data-account-search]').forEach(row=>{row.hidden=!matchesSearch(row.dataset.accountSearch,accountQuery);if(!row.hidden)count++;});
    document.getElementById('account-search-results').textContent=`${count} / ${state().accounts.length} tài khoản`;
    document.getElementById('account-search-empty').hidden=count>0;
  });
  function dialogs() {
    return `<dialog id="account-manage-dialog" aria-labelledby="account-manage-title"><form id="update-account-form"><div class="dialog-heading"><h2 id="account-manage-title">Quản lý tài khoản</h2></div><input type="hidden" name="id"><input type="hidden" name="revision"><label class="field">Vai trò<select name="role"><option value="GLV">GLV</option><option value="Admin">Admin · Truy cập toàn bộ</option></select></label><label class="field">Trạng thái<select name="active"><option value="true">Hoạt động</option><option value="false">Khoá tài khoản</option></select></label><p class="field-help">Thay đổi quyền sẽ kết thúc các phiên đăng nhập của người này.</p><button type="button" id="open-account-assignments" class="button button-secondary">Phân công / Đổi lớp phụ trách</button><p id="account-update-error" role="alert"></p><div class="account-edit-footer"><div class="account-maintenance-actions"><button type="button" id="open-reset-password" class="button button-secondary">Cấp lại mật khẩu</button><button type="button" id="open-delete-account" class="button button-danger">Xoá tài khoản</button></div><div class="dialog-actions"><button type="button" data-close-dialog class="button button-secondary">Đóng</button><button type="submit" class="button button-primary">Lưu quyền</button></div></div></form></dialog>
      <dialog id="account-delete-dialog" aria-labelledby="account-delete-title" aria-describedby="account-delete-description"><form id="delete-account-form"><h2 id="account-delete-title">Xoá tài khoản?</h2><p id="account-delete-name"></p><p id="account-delete-description">Tài khoản sẽ bị xoá khỏi danh sách và đăng xuất trên mọi thiết bị. Phân công hiện tại và năm học đã chuẩn bị sẽ được gỡ; hồ sơ GLV, lịch sử và dữ liệu thiếu nhi vẫn được giữ.</p><p class="field-help">Nếu chỉ tạm ngưng sử dụng, hãy chọn Khoá tài khoản trong phần Trạng thái.</p><input type="hidden" name="id"><input type="hidden" name="expectedRevision"><label class="field">Nhập tên đăng nhập để xác nhận<input name="confirmation" required maxlength="100" autocomplete="off" autocapitalize="none" spellcheck="false" aria-describedby="account-delete-username account-delete-error"></label><p id="account-delete-username" class="field-help"></p><label class="field">Lý do xoá<textarea name="reason" rows="2" required minlength="3" maxlength="500" aria-describedby="account-delete-error"></textarea></label><p id="account-delete-error" role="alert" tabindex="-1"></p><div class="dialog-actions"><button type="button" data-close-dialog class="button button-secondary" autofocus>Huỷ</button><button type="submit" class="button button-danger">Xác nhận xoá</button></div></form></dialog>
      <dialog id="account-reset-dialog" aria-labelledby="account-reset-title"><form id="reset-account-form"><h2 id="account-reset-title">Cấp lại mật khẩu?</h2><p id="account-reset-name"></p><p>Người này sẽ bị đăng xuất trên các thiết bị và phải đổi mật khẩu tạm khi đăng nhập lại.</p><input type="hidden" name="id"><p id="account-reset-error" role="alert"></p><div class="dialog-actions"><button type="button" data-close-dialog class="button button-secondary" autofocus>Quay lại</button><button type="submit" class="button button-primary">Cấp mật khẩu tạm</button></div></form></dialog>
      <dialog id="account-credential-dialog" aria-labelledby="account-credential-title"><h2 id="account-credential-title">Tài khoản đã sẵn sàng</h2><p>Gửi riêng thông tin này cho đúng người. Mật khẩu tạm chỉ hiển thị trong lần này.</p><div id="account-credential"></div><div class="dialog-actions"><button type="button" data-close-dialog class="button button-primary">Đã lưu thông tin</button></div></dialog>`;
  }
  document.body.insertAdjacentHTML('beforeend',dialogs());
  document.body.insertAdjacentHTML('beforeend',`<dialog id="account-assignment-dialog" aria-labelledby="account-assignment-title"><form id="assign-account-form"><h2 id="account-assignment-title">Phân công lớp phụ trách</h2><p id="account-assignment-name"></p><input type="hidden" name="id"><input type="hidden" name="expectedRevision"><input type="hidden" name="assignmentRevision"><div id="account-assignment-fields"></div><p id="account-assignment-error" role="alert" tabindex="-1"></p><div class="dialog-actions"><button type="button" data-close-dialog class="button button-secondary">Đóng</button><button type="submit" class="button button-primary">Lưu phân công</button></div></form></dialog>`);
  document.getElementById('account-assignment-dialog').addEventListener('cancel',event=>{if(busy)event.preventDefault();});
  function openAssignments(account){
    if(!account||busy)return;
    const form=document.getElementById('assign-account-form');
    form.elements.id.value=account.id;form.elements.expectedRevision.value=account.revision;form.elements.assignmentRevision.value=account.assignmentRevision;
    document.getElementById('account-assignment-name').textContent=account.displayName+' · '+account.username;
    document.getElementById('account-assignment-fields').innerHTML=assignmentFields({classes:classes(),accounts:state().accounts,esc,targetId:account.id},account.assignments||[]);
    document.getElementById('account-assignment-error').textContent='';
    document.getElementById('account-manage-dialog').close();form.closest('dialog').showModal();
  }
  document.addEventListener('change',event=>{
    if(!event.target.matches('[data-assignment-class]'))return;
    const row=event.target.closest('.account-assignment-row'),select=row.querySelector('[data-assignment-slot]');
    select.innerHTML=slotOptions({classId:event.target.value,slot:select.value,accounts:state().accounts,esc,targetId:row.closest('fieldset').dataset.assignmentTarget});
    if(select.selectedOptions[0]?.disabled)select.value=[...select.options].find(o=>!o.disabled)?.value||'';
  });
  document.getElementById('account-credential-dialog').addEventListener('close',()=>document.getElementById('account-credential').replaceChildren());
  document.getElementById('account-delete-dialog').addEventListener('cancel',event=>{if(busy)event.preventDefault();});
  document.addEventListener('submit',async event=>{
    const formEl=event.target;
    const formId=formEl.getAttribute('id');
    if(!['auth-form','create-account-form','update-account-form','reset-account-form','delete-account-form','assign-account-form'].includes(formId))return;
    event.preventDefault();if(busy)return;
    const values=Object.fromEntries(new FormData(formEl));
    const errorEl=document.getElementById(formId==='auth-form'?'auth-error':formId==='create-account-form'?'account-create-error':formId==='update-account-form'?'account-update-error':formId==='delete-account-form'?'account-delete-error':formId==='assign-account-form'?'account-assignment-error':'account-reset-error');
    errorEl.textContent='';
    formEl.querySelectorAll('[aria-invalid]').forEach(el=>el.removeAttribute('aria-invalid'));
    if(formId==='auth-form'&&mode==='password'&&values.newPassword!==values.confirmPassword){errorEl.textContent='Hai lần nhập mật khẩu mới chưa khớp.';formEl.elements.confirmPassword.setAttribute('aria-invalid','true');formEl.elements.confirmPassword.setAttribute('aria-describedby','auth-error');formEl.elements.confirmPassword.focus();return;}
    busy=true;formEl.setAttribute('aria-busy','true');formEl.querySelectorAll('button').forEach(b=>b.disabled=true);
    const submitButton=formEl.querySelector('button[type="submit"]'),submitLabel=submitButton.textContent;
    submitButton.textContent=formId==='auth-form'?(mode==='password'?'Đang lưu mật khẩu…':'Đang đăng nhập…'):'Đang xử lý…';
    try {
      if(formId==='auth-form') {
        const welcome=mode==='login'||!!user?.mustChangePassword;
        const result=await api(mode==='password'?'auth/password':'auth/login',values);
        user=result.user;csrfToken=result.csrfToken;formEl.reset();
        if(user.mustChangePassword)show('password');else {
          submitButton.textContent='Đang mở cổng giáo lý…';
          await ready(welcome);
        }
      } else {
        const path=formId==='create-account-form'?'create':formId==='update-account-form'?'update':formId==='delete-account-form'?'delete':formId==='assign-account-form'?'assignments':'reset-password';
        if(path==='update')values.active=values.active==='true';
        if(['delete','assignments'].includes(path))values.expectedRevision=Number(values.expectedRevision);
        if(['create','assignments'].includes(path))values.assignments=collectAssignments(formEl);
        const result=await queueWrite(()=>api('accounts/'+path,values));state().accounts=result.accounts;
        if(result.state)applyServer?.(result.state);
        onAccountsChanged?.();
        if(path==='create')formEl.reset();else formEl.closest('dialog').close();
        render();
        if(result.temporaryPassword) {
          document.getElementById('account-credential').innerHTML=`<p><strong>${esc(result.displayName)}</strong></p><label class="field">Tên đăng nhập<input readonly value="${esc(result.username)}"></label><label class="field">Mật khẩu tạm<input readonly value="${esc(result.temporaryPassword)}" autocomplete="off"></label>`;
          document.getElementById('account-credential-dialog').showModal();
        }else toast(path==='delete'?'Đã xoá tài khoản. Hồ sơ và lịch sử được giữ lại.':path==='assignments'?'Đã cập nhật lớp phụ trách.':'Đã cập nhật quyền tài khoản.');
      }
    }catch(error){errorEl.textContent=error.message;if(['delete-account-form','assign-account-form'].includes(formId)){errorEl.focus();errorEl.scrollIntoView({block:'nearest'});}if(formId==='auth-form'&&error.status===401)formEl.querySelectorAll('input').forEach(el=>el.setAttribute('aria-invalid','true'));}finally{busy=false;formEl.removeAttribute('aria-busy');submitButton.textContent=submitLabel;formEl.querySelectorAll('button').forEach(b=>b.disabled=false);}
  });
  document.addEventListener('click',async event=>{
    const target=event.target.closest('button');if(!target)return;
    if(target.hasAttribute('data-assignment-add')){
      if(busy)return;const fieldset=target.closest('fieldset');
      fieldset.querySelector('[data-assignment-rows]').insertAdjacentHTML('beforeend',assignmentRow({classes:classes(),accounts:state().accounts,esc,targetId:fieldset.dataset.assignmentTarget}));
      fieldset.querySelector('.account-assignment-row:last-child select').focus();
    }else if(target.hasAttribute('data-assignment-remove')){
      if(busy)return;const fieldset=target.closest('fieldset');target.closest('.account-assignment-row').remove();fieldset.querySelector('[data-assignment-add]').focus();
    }else if(target.hasAttribute('data-account-assign')||target.id==='open-account-assignments'){
      const id=target.dataset.accountAssign||document.getElementById('update-account-form').elements.id.value;
      openAssignments(state().accounts.find(a=>a.id===id));
    }else if(target.id==='cancel-password') {
      if(!busy)await ready();
    }else if(target.id==='auth-logout') {
      if(pending()){toast('Đang lưu. Chờ hoàn tất rồi đăng xuất.');return;}
      target.disabled=true;
      try{await api('auth/logout',{});clear();}catch(error){if(error.status===401)clear();else toast(error.message);}finally{target.disabled=false;}
    }else if(target.id==='change-password') {
      if(pending()){toast('Đang lưu. Chờ hoàn tất rồi đổi mật khẩu.');return;}
      onClear();show('password');
    }else if(target.dataset.accountEdit) {
      const a=state().accounts.find(a=>a.id===target.dataset.accountEdit),formEl=document.getElementById('update-account-form');
      if(!a)return;
      formEl.elements.id.value=a.id;formEl.elements.revision.value=a.revision;formEl.elements.role.value=a.role;formEl.elements.active.value=String(a.active);
      document.getElementById('account-manage-title').textContent=a.displayName+' · '+a.username;
      document.getElementById('account-update-error').textContent='';formEl.closest('dialog').showModal();
    }else if(target.id==='open-delete-account') {
      if(busy)return;
      const manage=document.getElementById('update-account-form'),a=state().accounts.find(a=>a.id===manage.elements.id.value);
      if(!a||a.id===user.id)return;
      const formEl=document.getElementById('delete-account-form');formEl.reset();
      formEl.elements.id.value=a.id;formEl.elements.expectedRevision.value=manage.elements.revision.value;
      document.getElementById('account-delete-name').textContent=a.displayName+' · '+a.username;
      document.getElementById('account-delete-username').textContent='Tên đăng nhập: '+a.username;
      document.getElementById('account-delete-error').textContent='';
      document.getElementById('account-manage-dialog').close();formEl.closest('dialog').showModal();
    }else if(target.id==='open-reset-password') {
      const id=document.getElementById('update-account-form').elements.id.value,a=state().accounts.find(a=>a.id===id);
      document.getElementById('account-manage-dialog').close();
      document.getElementById('reset-account-form').elements.id.value=id;document.getElementById('account-reset-name').textContent=a.displayName+' · '+a.username;
      document.getElementById('account-reset-error').textContent='';document.getElementById('account-reset-dialog').showModal();
    }
  });
  return {init,clear,show,chrome,accountsPage,refreshSession,csrf:()=>csrfToken,user:()=>user};
}

