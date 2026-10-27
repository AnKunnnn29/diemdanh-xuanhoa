const primary=[['home','church','Trang chủ'],['start','grid','Công việc hôm nay']];
const classroom=[['attendance','qr','Điểm danh'],['students','users','Thiếu nhi'],['grades','chart','Điểm học tập'],['requests','calendar','Đơn từ'],['care','heart','Theo dõi thiếu nhi'],['files','file','Báo cáo & tải sổ']];
const team=[['celebrations','calendar','Sinh nhật & bổn mạng GLV'],['reports','chart','Báo cáo chuyên cần'],['overview','chart','Tổng quan'],['notifications','calendar','Thông báo & nhắc việc'],['teachers','teacher','Phân công GLV'],['staff','teacher','Hồ sơ GLV']];
const administration=[['accounts','users','Tài khoản & phân quyền'],['classes','book','Lớp giáo lý'],['excel','book','Quản lý sổ lớp'],['management','file','Sao lưu & năm học'],['administration','grid','Quản trị hệ thống']];
export const adminPages=[...administration.map(([page])=>page),'staff','celebrations'];
export const classPages=['start','attendance','students','grades','requests','care','files','excel'];
const links=items=>items.map(([page,icon,label])=>`<a href="#${page}" class="nav-item" data-page="${page}"><span data-icon="${icon}"></span>${label}</a>`).join('');
export function mountNavigation(){
  document.querySelector('.desktop-nav').innerHTML=`${links(primary)}<details id="desktop-class-menu" class="nav-group"><summary>Công việc lớp</summary>${links(classroom)}</details><details id="desktop-team-menu" class="nav-group"><summary>Theo dõi & GLV</summary>${links(team)}</details><details id="desktop-management-menu" class="nav-group" data-admin-navigation><summary>Quản trị</summary>${links(administration)}</details>`;
  document.querySelector('.mobile-menu nav').innerHTML=`<section class="nav-group" aria-label="Trang chính">${links(primary)}</section><section class="nav-group" aria-labelledby="mobile-class-label"><h2 id="mobile-class-label" class="nav-group-label">Công việc lớp</h2>${links(classroom)}</section><section class="nav-group" aria-labelledby="mobile-team-label"><h2 id="mobile-team-label" class="nav-group-label">Theo dõi & GLV</h2>${links(team)}</section><section class="nav-group" data-admin-navigation aria-labelledby="mobile-admin-label"><h2 id="mobile-admin-label" class="nav-group-label">Quản trị</h2>${links(administration)}</section>`;
  document.querySelector('.mobile-menu summary').innerHTML='<span data-icon="menu"></span><span id="mobile-menu-label">Điều hướng</span><span data-icon="chevron"></span>';
  for(const brand of document.querySelectorAll('.sidebar .brand,.mobile-brand'))brand.setAttribute('href','#home');
  const crumb=document.querySelector('.breadcrumbs>span:first-child');
  const home=document.createElement('a');home.href='#home';home.textContent='Trang chủ';crumb.replaceWith(home);
}
export function openNavigationGroup(view){
  document.getElementById('desktop-class-menu').open=['start',...classroom.map(([page])=>page)].includes(view);
  document.getElementById('desktop-team-menu').open=team.some(([page])=>page===view);
  document.getElementById('desktop-management-menu').open=administration.some(([page])=>page===view);
}
