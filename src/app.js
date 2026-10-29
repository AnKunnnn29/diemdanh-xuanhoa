import {createAuthUI} from './auth-ui.js';
import {createPrivacyUI} from './privacy-ui.js';
import {createReportsUI} from './reports-ui.js';
import {createEnrollmentUI} from './enrollment-ui.js';
import {mountNavigation,openNavigationGroup,adminPages,classPages} from './navigation.js';
import {createTeacherAssignmentsUI,teacherSlots} from './teacher-assignments-ui.js';
import {createWelcomeSceneController} from './welcome-scene.js';
import {createMotionController,loadingPanel,animationStage,busyFeedback,celebrateSession} from './lottie-ui.js';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';
import jsQR from 'jsqr';
import { landing } from './landing.js';
import {requestsPage,requestTable,requestDialogs,requestStates,makeupDate} from './requests-ui.js';
import {attendanceHistory,summarizeAttendance} from './attendance-metrics.js';
import {groupSessionAttendance,sessionSummaryHtml,presentClipboardText,copySessionText,earlyMassAttendance} from './session-summary.js';
import {sessionAttendancePrintHtml} from './session-attendance-print.js';
import {renderPrintWindow} from './print-window.js';
import {scanAnnouncement,scanBubbleHtml,scanConfirmationHtml} from './scan-notification.js';
import {createDevelopmentUI} from './development-ui.js';
import {createManagementUI} from './management-ui.js';
import {lifecycleStatus} from './care-insights.js';
import {gradeValue,selectGradeRows,missingGradeInputs,khaoBaiDetails} from './grade-summary.js';
import {createExcelParityUI} from './excel-parity-ui.js';
import {startPage,attendanceSetup,flowSteps,gradeEditor,requestWizard} from './easy-ui.js';
import {normalizeSearch, matchesSearch, gradeFields, gradesMatch} from './ux-utils.js';
import {createGradeColumnUI} from './grade-column-ui.js';
import {contactFields,encodeContactFields,parentContactMarkup} from './parent-contacts.js';
import {createPortalTransition} from './portal-transition.js';
import {downloadResponse} from './cloud-download.js';
import {createOfflineAttendance,offlinePanel} from './offline-attendance.js';
import {createStaffCelebrationsUI} from './staff-celebrations.js';
import {attachStudentCombobox} from './student-combobox.js';

const cn = (...values) => twMerge(clsx(values));
const svg = (body) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
const icons = {
  grid: svg('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
  qr: svg('<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/><rect x="6" y="6" width="4" height="4"/><rect x="14" y="6" width="4" height="4"/><rect x="6" y="14" width="4" height="4"/><path d="M14 14h2v2h2v2h-4m4-4h1m-3 5v1"/>'),
  users: svg('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>'),
  teacher: svg('<path d="M8 21v-3a4 4 0 0 0-4-4H3m9-11h9v13h-5M16 7h2m-2 4h2"/><circle cx="6" cy="7" r="3"/><path d="M3 21v-3m6-4 4-3"/>'),
  file: svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8m-8 4h8"/>'),
  chart: svg('<path d="M4 3v17h17M8 16v-5m5 5V6m5 10v-8"/>'),
  heart: svg('<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>'),
  church: svg('<path d="M12 2v5m-2-3h4M4 21V11l8-5 8 5v10M2 21h20M9 21v-6a3 3 0 0 1 6 0v6M7 11h.01m10 0h.01"/>'),
  calendar: svg('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-13 4h2m4 0h2m-8 3h2"/>'),
  clock: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  book: svg('<path d="M4 3h7a3 3 0 0 1 3 3v15a3 3 0 0 0-3-3H4V3Zm10 3a3 3 0 0 1 3-3h4v15h-4a3 3 0 0 0-3 3"/>'),
  arrow: svg('<path d="M5 12h14m-5-5 5 5-5 5"/>'),
  download: svg('<path d="M12 3v12m-4-4 4 4 4-4M4 16v4h16v-4"/>'),
  check: svg('<path d="m5 12 4 4L19 6"/>'),
  checkcircle: svg('<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>'),
  close: svg('<path d="m6 6 12 12M6 18 18 6"/>'),
  menu: svg('<path d="M4 6h16M4 12h16M4 18h16"/>'),
  chevron: svg('<path d="m7 10 5 5 5-5"/>'),
  spark: svg('<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>'),
  camera: svg('<path d="M14 4H9L7 7H3v13h18V7h-5l-2-3Z"/><circle cx="12" cy="13" r="4"/>'),
  keyboard: svg('<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M6 13h.01M10 13h.01M14 13h.01M18 13h.01M8 16h8"/>'),
  phone: svg('<path d="M22 16.9v3a2 2 0 0 1-2.2 2A19.8 19.8 0 0 1 3.1 5.2 2 2 0 0 1 5.1 3h3a2 2 0 0 1 2 1.7l.5 3a2 2 0 0 1-.6 1.7L8.7 10.7a16 16 0 0 0 4.6 4.6l1.3-1.3a2 2 0 0 1 1.7-.6l3 .5a2 2 0 0 1 1.7 2Z"/>'),
  search: svg('<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>'),
  info: svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>'),
};
const i = (name) => icons[name] || icons.info;
function decorate(root = document) { root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = i(el.dataset.icon); }); }
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const activities = { mass: 'Tham dự Thánh lễ', early: 'Đi lễ sớm', lesson: 'Học giáo lý' };
const CLASS_LEVEL_SPECS = [
  { key: 'chien', prefixes: ['chiên'] },
  { key: 'au', prefixes: ['ấu'] },
  { key: 'thieu', prefixes: ['thiếu'] },
  { key: 'nghia', prefixes: ['nghĩa'] },
  { key: 'hiep', prefixes: ['hiệp'] },
  { key: 'dubi', prefixes: ['dự bị', 'db'] }
];
function classRank(name) { const lower = String(name || '').toLowerCase().trim(); const idx = CLASS_LEVEL_SPECS.findIndex(s => s.prefixes.some(p => lower.startsWith(p))); return idx >= 0 ? idx : CLASS_LEVEL_SPECS.length; }
function classLevelKey(name) { const r = classRank(name); return r < CLASS_LEVEL_SPECS.length ? CLASS_LEVEL_SPECS[r].key : ''; }
function compareClassNames(a, b) { const ra = classRank(a), rb = classRank(b); return ra !== rb ? ra - rb : a.localeCompare(b, 'vi'); }
function isSunday(dateStr) { try { const [y, m, d] = String(dateStr || '').split('-').map(Number); return new Date(y, m - 1, d).getDay() === 0; } catch { return false; } }
let classNames = [];
let classes = [];
let students = [];
let connected = false;
let offlineRestored=false;
let offlineSyncTask=null;
const offlineAttendance=createOfflineAttendance({onChange:()=>renderOfflinePanel()});
let authEpoch=0;
let connectionIssue=null,reconnectTimer=null,reconnectAttempt=0,reconnecting=false,refreshing=false;
let pendingWrites = 0;
let mutationQueue = Promise.resolve();
const queuedCodes = new Set();
const tz = 'Asia/Ho_Chi_Minh';
const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
const shortDate = d => d.split('-').reverse().join('/');
const longDate = d => new Intl.DateTimeFormat('vi-VN', { timeZone: tz, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(`${d}T12:00:00+07:00`));
const timeOf = d => new Intl.DateTimeFormat('vi-VN', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(d));
function earlyWindowOpen(session){
  const clock=new Intl.DateTimeFormat('en-GB',{timeZone:tz,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date());
  const minute=Number(clock.find(p=>p.type==='hour').value)*60+Number(clock.find(p=>p.type==='minute').value);
  return session.date===today()&&isSunday(session.date)&&minute>=360&&minute<=380;
}
const key = (session, id) => `${session.date}|${session.activity}|${id}`;
const scoped = scope => students.filter(s => scope === 'all' || s.className === scope);
let storageKey = 'gx-xuan-hoa-live-preferences-v1';
let storageError = false;
let state = {sessions: [], active: null, marks: {}, downloads: [], requests:[],requestEvents:[],isManager:false};
let preferences = {};
try { preferences = JSON.parse(localStorage.getItem(storageKey)) || {}; } catch {}
let workingClass=preferences.className||'';
let scanMethod=preferences.scanMethod==='camera'||preferences.scanMethod==='text'?preferences.scanMethod:(matchMedia('(max-width: 639px)').matches?'camera':'text');
let attendanceStage='setup',attendanceDraft=null,attendanceSetupError='';
if('largeText' in preferences){delete preferences.largeText;try{localStorage.setItem(storageKey,JSON.stringify(preferences));}catch{}}
document.documentElement.removeAttribute('data-large-text');
const development=createDevelopmentUI({state:()=>state,students:()=>students,classes:()=>classes,actor:()=>preferences.actor||'',onYearPrepared:()=>management.invalidateYears(),studentFilter:()=>studentFilter,carePeople:()=>calculateCareMetrics().people,careMarks:()=>careMarks(),api,queueWrite,applyServer,render,today,shortDate,downloadBlob,rememberActor,toast,esc,i,reauthenticate:()=>auth.clear()});
const staffCalendar=createStaffCelebrationsUI({api,state:()=>state,render,esc,today});
const management=createManagementUI({state:()=>state,classes:()=>classes,api,queueWrite,applyServer,render,toast,esc,reauthenticate:()=>auth.clear(),onStaffChanged:()=>staffCalendar.clear()});
const enrollment=createEnrollmentUI({state:()=>state,classes:()=>classes,api,queueWrite,applyServer,render,toast,esc,today,
  openStudents:name=>{rememberClass(name);route('students');},
  onChanged:()=>{management.clear();parity.clear();currentGradesData=null;gradesLoadToken++;gradesLoading=false;}});
const parity=createExcelParityUI({state:()=>state,students:()=>students,classes:()=>classes,workingClass:()=>workingClass,onClassChange:rememberClass,actor:()=>preferences.actor||'',year:()=>document.querySelector('.year-card strong').textContent,api,queueWrite,applyServer,render,today,downloadBlob,rememberActor,toast,esc,i,invalidateGrades:()=>{currentGradesData=null;gradesLoadToken++;gradesLoading=false;}});
async function api(path, values) {
  const epoch=authEpoch;
  if(connectionIssue&&values!==undefined&&!path.startsWith('auth/')){if(connectionIssue.status===401&&connected)openConnectionLogin();throw new Error('Đang kết nối lại. Nội dung vẫn được giữ; chờ kết nối rồi thử lưu.');}
  const workbookRead=/^(?:grades|excel-details|admin\/year-history|snapshot-export|year-export)(?:\?|$)/.test(path);
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),values===undefined&&!workbookRead?20000:240000);
  try{
    const response = await fetch('/api/' + path, {cache:'no-store',signal:controller.signal, ...(values === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':auth.csrf()},body:JSON.stringify(values)})});
    let data; try { data = await response.json(); } catch { throw new TypeError('Chưa đọc được phản hồi từ dịch vụ.'); }
    if(epoch!==authEpoch)throw new Error('Phiên đăng nhập đã thay đổi.');
    if (!response.ok) { const error = new Error(data.error || 'Chưa hoàn tất thao tác.'); error.status = response.status;error.code=data.code;if(response.status===401&&!path.startsWith('auth/')){if(pendingWrites)mutationQueue.finally(()=>{if(epoch===authEpoch)auth.clear();});else auth.clear();}throw error; }
    return data;
  }catch(error){
    if(error.name==='AbortError'||error instanceof TypeError){
      const failure=new Error(values===undefined?'Kết nối đang gián đoạn. Ứng dụng sẽ tự thử lại.':'Chưa nhận được xác nhận lưu. Giữ nội dung và kiểm tra kết quả sau khi kết nối lại trước khi lưu lại.');
      failure.network=true;failure.uncertain=values!==undefined;connectionLost(failure);throw failure;
    }
    throw error;
  }finally{clearTimeout(timer);}
}
function applyServer(data) {
  if(data.user?.id!==auth.user()?.id)return;
  if(!data.isManager&&(!workingClass||workingClass==='all'||!data.classes.some(c=>c.name===workingClass)))workingClass=data.classes[0]?.name||'';
  document.querySelector('.year-card strong').textContent=data.year||'2026-2027';
  const yearBadge=document.querySelector('.trial-badge');if(yearBadge)yearBadge.textContent='Năm học '+(data.year||'2026-2027');
  classes = data.classes.sort((a, b) => compareClassNames(a.name, b.name));
  if(currentGradesData&&!classes.some(c=>c.id===currentGradesData.classId)){currentGradesData=null;gradesClassId='';gradesLoadToken++;gradesLoading=false;gradeColumn.clear();}
  classNames = classes.map(c => c.name);
  if(workingClass&&workingClass!=='all'&&!classNames.includes(workingClass))workingClass='';
  students = data.students.map(person=>data.privacyVersion===2?{...person,_identityOnly:true,fullName:person.name,saintName:'',className:classes.find(c=>c.id===person.classId)?.name||'',...(data.attendanceRules?.[person.id]||{})}:person).sort((a,b)=>compareClassNames(a.className,b.className));
  studentFilter=workingClass||'all';careClassFilter=workingClass||'all';
  const todaySession = data.sessions.find(s => s.date === today() && s.activity === 'mass' && s.scope === 'all');
  const active = (state.active && data.sessions.some(s=>s.id===state.active)) ? state.active : (todaySession ? todaySession.id : (preferences.active && data.sessions.some(s=>s.id===preferences.active) ? preferences.active : data.sessions.at(-1)?.id));
  state = {privacyVersion:data.privacyVersion,access:data.access||{},studentDirectory:data.students,mode:data.mode||'excel',yearId:data.yearId,year:data.year,user:data.user,accounts:data.accounts||[],sessions:data.sessions, marks:data.marks, requests:data.requests||[],requestEvents:data.requestEvents||[],recurringMass:data.recurringMass||[],studentStatuses:data.studentStatuses||[],careNotes:data.careNotes||[],managementEvents:data.managementEvents||[],yearPlans:data.yearPlans||[],gradeMode:data.gradeMode||'native',isManager:!!data.isManager, active, pendingScans:data.pendingScans||[], downloads:state.downloads.length?state.downloads:(preferences.downloads || [])};
  connected = true;
  if(!offlineRestored)offlineAttendance.remember(data);
}
function sessionPeople(session) {
  if (session.activity === 'mass') {
    return scoped(session.scope).filter(s => !classes.find(c=>c.id===s.classId)?.archived&&(!s.enrolledFrom || s.enrolledFrom <= session.date)&&lifecycleStatus(state.studentStatuses,s.id,session.date)==='active');
  }
  const due=new Set(state.requests.filter(r=>r.kind==='makeup'&&makeupDate(r)===session.date&&['approved','completed','missed'].includes(r.status)&&(!r.actual_day||r.actual_day===session.date)).map(r=>r.code));
  return scoped(session.scope).filter(s => !classes.find(c=>c.id===s.classId)?.archived&&lifecycleStatus(state.studentStatuses,s.id,session.date)==='active'&&(((!s.enrolledFrom || s.enrolledFrom<=session.date) && classes.find(c=>c.id===s.classId)?.calendar[session.activity]?.includes(session.date)) || due.has(s.id)));
}
const waitingFor=(session,student)=>state.requests.find(r=>r.code===student.id&&r.kind==='makeup'&&r.status==='approved'&&r.day===session.date&&r.activity===session.activity);
function requestAnnotation(session,student) {
  const waiting=waitingFor(session,student);
  const attended=state.requests.find(r=>r.code===student.id&&r.kind==='makeup'&&r.status==='completed'&&r.actual_day===session.date&&r.day!==session.date&&session.activity==='mass');
  const due=state.requests.find(r=>r.code===student.id&&r.kind==='makeup'&&r.status==='approved'&&makeupDate(r)===session.date&&session.activity==='mass');
  return waiting?`<small class="makeup-note">Chờ lễ bù ${shortDate(makeupDate(waiting))}${waiting.exception_day?' · Riêng buổi này':''}</small>`:attended?`<small class="makeup-note">Đã đi lễ bù cho ${shortDate(attended.day)} · Không cộng thêm buổi này</small>`:due?`<small class="makeup-note">Có lễ bù cho ${shortDate(due.day)}${due.exception_day?' · Ngoại lệ một buổi':''}</small>`:'';
}

function queueWrite(action) {
  pendingWrites++;
  const result = mutationQueue.then(action);
  mutationQueue = result.catch(()=>{}).finally(()=>{pendingWrites--;});
  return result;
}
async function bootstrap() {
  if(connected)return reconnect();
  const epoch=authEpoch;
  try { applyServer(await api('bootstrap')); connectionRestored();decorate(); routeFromHash(); }
  catch(error) { if(epoch!==authEpoch)return;connectionView(error);connectionLost(error); }
}
function connectionBanner(){
  let banner=document.getElementById('connection-banner');
  if(!banner){banner=document.createElement('section');banner.id='connection-banner';banner.className='connection-banner';document.getElementById('main-content').prepend(banner);}
  banner.hidden=!connectionIssue;
  if(!connectionIssue)return;
  if(connectionIssue.status===401){
    banner.innerHTML='<div><strong>Kết nối đã hết hạn</strong><p>Nội dung đang nhập được giữ. Nhập mã kết nối trên máy quản lý để tiếp tục.</p></div><button type="button" class="button button-secondary" id="renew-connection">Nhập mã kết nối</button>';
  }else{
    banner.innerHTML=`<div><strong>Đang kết nối lại</strong><p role="status" aria-live="polite">${state.mode==='cloud'?'Bạn vẫn có thể điểm danh trong buổi hôm nay đã mở. Lượt quét được giữ trên thiết bị và chờ đồng bộ. Các thay đổi khác cần có mạng.':'Nội dung và buổi đang chọn vẫn được giữ. Chờ kết nối trước khi lưu.'}</p></div><button type="button" class="button button-secondary" id="retry-connection">Thử lại ngay</button>`;
  }
}
function openConnectionLogin(){auth.clear();}
function connectionLost(error){
  connectionIssue=error;connectionBanner();
  renderOfflinePanel();
  if(error.status===401){clearTimeout(reconnectTimer);if(connected&&document.querySelector('dialog[open]'))openConnectionLogin();return;}
  if(!reconnectTimer&&!reconnecting)reconnectTimer=setTimeout(()=>{reconnectTimer=null;reconnect();},Math.min(15000,2000*2**reconnectAttempt++));
}
function connectionRestored(){
  const wasLost=!!connectionIssue;connectionIssue=null;reconnectAttempt=0;clearTimeout(reconnectTimer);reconnectTimer=null;connectionBanner();
  renderOfflinePanel();
  if(wasLost&&connected)toast('Đã kết nối lại. Bạn có thể tiếp tục công việc.');
}
async function reconnect(){
  if(document.body.dataset.auth!=='in'||!auth.user()||auth.user().mustChangePassword)return;
  if(reconnecting||refreshing)return;
  reconnecting=true;clearTimeout(reconnectTimer);reconnectTimer=null;
  const hadData=connected;
  try{if(offlineRestored)await auth.refreshSession();const data=await api('bootstrap');offlineRestored=false;applyServer(data);connectionRestored();
    if(!hadData){decorate();routeFromHash();}
    else {
      await verifyGradeSave();await gradeColumn.verifyPending();
      if(!pendingWrites&&!document.querySelector('dialog[open]'))render();
    }
    syncOfflineScans();
  }catch(error){if(error.status===401){auth.clear();return;}connectionIssue=error;if(!hadData)connectionView(error);connectionBanner();}
  finally{reconnecting=false;if(connectionIssue)connectionLost(connectionIssue);}
}
async function refreshServer(){
  if(document.body.dataset.auth!=='in'||!auth.user()||auth.user().mustChangePassword)return;
  if(refreshing||reconnecting||document.hidden)return;
  if(connectionIssue||!connected)return reconnect();
  if(pendingWrites||document.querySelector('dialog[open]'))return;
  refreshing=true;
  try{
    const snapshot=()=>JSON.stringify([state,students,classes]),before=snapshot();
    applyServer(await api('bootstrap'));if(before!==snapshot())render();syncOfflineScans();
  }catch(error){connectionLost(error);}finally{refreshing=false;}
}
function connectionView(error) {
  if(error.status===401){auth.clear();return;}
  stopCamera();scanBubble.hidden=true;
  delete document.body.dataset.view;
  page.innerHTML=`<section class="connection-card card"><h1>Chưa mở được sổ lớp</h1><p role="alert">${esc(error.message)}</p><button class="button button-primary" id="reconnect">Thử lại</button></section>`;
}
let view = 'overview';
let studentFilter = 'all';
let studentTerm='';
let attendanceClass = 'all';
let attendanceStatus = 'all';
let attendanceTerm = '';
let exportClass = 'all';
let scanFeedback = null;
let scanBubbleDismissed = true;
const scanBubble=document.createElement('section');
scanBubble.id='scan-bubble';scanBubble.className='scan-bubble';scanBubble.hidden=true;
scanBubble.setAttribute('role','region');scanBubble.setAttribute('aria-labelledby','scan-bubble-title');
document.body.appendChild(scanBubble);
let scanCandidate=null;
const scanConfirmation=document.createElement('dialog');
scanConfirmation.id='scan-confirmation-dialog';scanConfirmation.className='scan-confirmation';
scanConfirmation.setAttribute('aria-labelledby','scan-confirmation-title');
scanConfirmation.setAttribute('aria-describedby','scan-confirmation-description');
document.body.appendChild(scanConfirmation);
scanConfirmation.addEventListener('cancel',event=>{if(scanCandidate?.phase==='saving')event.preventDefault();});
scanConfirmation.addEventListener('close',()=>{
  if(scanConfirmation.open)return;
  if(scanCandidate?.phase==='choice')return;
  scanCandidate=null;scanConfirmation.replaceChildren();
  if(connected&&view==='attendance')((cameraStream?document.getElementById('camera-toggle'):document.getElementById('student-code'))||document.getElementById('main-content'))?.focus({preventScroll:true});
});
let requestFilter='all',requestTerm='',reviewId=null,reviewDecision=null,correction=null,scanChoice=null,rescheduleId=null;
let cameraStream = null;
let scanTimer = null;
let scanToken = 0;
let toastTimer;
let lastDetected = { code: '', time: 0 };
const page = document.getElementById('page');
mountNavigation();
const teacherAssignments=createTeacherAssignmentsUI({classes:()=>classes,state:()=>state,esc,i,year:()=>document.querySelector('.year-card strong').textContent});
const teachersView=()=>teacherAssignments.page();
let renderedView=null;
page.innerHTML = loadingPanel();
function save() { try { localStorage.setItem(storageKey, JSON.stringify({...preferences,active:state.active,downloads:state.downloads,actor:preferences.actor,className:workingClass})); return true; } catch { return false; } }
function rememberClass(name) {
  if(!state.isManager&&classes.length&&(!name||name==='all'))name=classes[0].name;
  if(name!=='all'&&name!==''&&!classNames.includes(name))return;
  workingClass=name;studentFilter=name||'all';careClassFilter=name||'all';preferences.className=name;save();
}
function workContext() {
  document.querySelector('.workspace-classbar').hidden=!state.isManager&&classes.length<=1;
  const select=document.getElementById('workspace-class');
  select.innerHTML=`<option value="">Chọn lớp…</option><option value="all" ${workingClass==='all'?'selected':''}>Tất cả lớp</option>${classes.map(c=>`<option value="${esc(c.name)}" ${workingClass===c.name?'selected':''}>${esc(c.name)}${c.archived?' · Đã lưu trữ':''}</option>`).join('')}`;
}
async function chooseWorkingClass(name) {
  if(pendingWrites){toast('Đang lưu dữ liệu. Chờ hoàn tất rồi đổi lớp.');workContext();return;}
  rememberClass(name);
  if(view==='attendance'){stopCamera();attendanceStage='setup';attendanceDraft={date:attendanceDraft?.date||current().date,activity:attendanceDraft?.activity||current().activity,scope:name};}
  if(view==='grades'){return loadGrades(classes.find(c=>c.name===name)?.id||gradesClassId||classes[0].id,gradesSemester);}
  if(view==='excel'&&name!=='all'&&name){return parity.load(classes.find(c=>c.name===name).id);}
  render();
}
function beginSetup(useToday=false) {
  stopCamera();attendanceStage='setup';attendanceSetupError='';
  attendanceDraft={date:useToday?today():current().date,activity:useToday?'mass':current().activity,scope:workingClass||''};
  if(view==='attendance')render();else route('attendance');
}
function chooseScanMethod(method){
  if(method==='text')stopCamera();
  scanMethod=method;preferences.scanMethod=method;save();render();
  (document.getElementById(method==='text'?'student-code':'camera-toggle'))?.focus({preventScroll:true});
}
async function startAttendance(event) {
  event.preventDefault();const button=document.getElementById('begin-attendance');
  const v=Object.fromEntries(new FormData(event.target));attendanceDraft=v;
  if((v.activity==='lesson'||v.activity==='early')&&!isSunday(v.date)){attendanceSetupError='Giáo lý và lễ sớm chỉ vào Chủ Nhật. Vui lòng chọn lại ngày.';render();return;}
  button.disabled=true;button.textContent='Đang mở buổi…';
  try{rememberClass(v.scope);await switchDailySession(v.date,v.activity,v.scope);}
  finally{if(button.isConnected){button.disabled=false;button.textContent='Bắt đầu điểm danh';}}
}
function current() { return state.sessions.find(s => s.id === state.active) || state.sessions[0]; }
const mark = (session, student) => state.marks[key(session, student.id)];
const completedMakeups=session=>new Set(state.requests.filter(r=>r.kind==='makeup'&&r.status==='completed'&&r.actual_day===session.date&&r.day!==session.date&&session.activity==='mass').map(r=>r.code));
function stats(session) {
  const people = sessionPeople(session);
  const completed=completedMakeups(session);
  return { total: people.length, present: people.filter(s => mark(session, s)?.status === 'X').length, permitted: people.filter(s => mark(session, s)?.status === 'P').length, absent: people.filter(s => mark(session, s)?.status === 'O').length, waiting:people.filter(s=>!mark(session,s)&&waitingFor(session,s)).length, makeupDone:people.filter(s=>completed.has(s.id)).length, pending:people.filter(s=>!mark(session,s)&&!waitingFor(session,s)&&!completed.has(s.id)).length, processed:people.filter(s=>mark(session,s)||completed.has(s.id)).length };
}
function badge(text, closed = false) { return `<span class="badge ${closed ? 'neutral' : ''}"><span class="badge-dot"></span>${esc(text)}</span>`; }
function statusLabel(value) {
  const text = { X: 'Có mặt', P: 'Nghỉ phép', O: 'Vắng mặt' };
  return `<span class="status ${value ? value.toLowerCase() : 'empty'}">${value === 'X' ? i('check') : ''}${text[value] || 'Chưa điểm danh'}</span>`;
}
function studentCell(student) { return `<div class="student-name"><span class="student-avatar">${esc(student.name.split(' ').at(-1).slice(0,1))}</span><div><strong>${esc(student.fullName)}</strong><small>${esc(student._identityOnly?"Hồ sơ chi tiết theo quyền":student.saintName||"Chưa có tên thánh")} · ${esc(student.id)}</small></div></div>`; }
function heading(eyebrow, title, description, action = '') { return `<div class="page-heading"><div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${action}</div>`; }
function toast(message) { const box = document.getElementById('toast'); clearTimeout(toastTimer); box.textContent = message; box.hidden = false; toastTimer = setTimeout(() => { box.hidden = true; }, 4500); }
function renderScanBubble(){
  if(!connected||view!=='attendance'||!scanFeedback||scanBubbleDismissed){scanBubble.hidden=true;return;}
  const feedback=document.getElementById('scan-feedback');if(feedback)feedback.hidden=true;
  document.getElementById('scan-result-slot')?.appendChild(scanBubble);
  scanBubble.dataset.kind=scanFeedback.kind||'duplicate';
  scanBubble.innerHTML=scanBubbleHtml(scanFeedback,{esc,i,classLevelKey});
  scanBubble.hidden=false;
}
function dismissScanBubble(){
  const restore=scanBubble.contains(document.activeElement);
  scanBubbleDismissed=true;scanBubble.hidden=true;
  const feedback=document.getElementById('scan-feedback');if(feedback)feedback.hidden=false;
  if(restore)((cameraStream?document.getElementById('camera-toggle'):document.getElementById('student-code'))||document.getElementById('main-content')).focus({preventScroll:true});
}
const searchable = normalizeSearch;
function attendancePeople(session) {
  return sessionPeople(session).filter(s =>
    (attendanceClass === 'all' || s.className === attendanceClass) &&
    (attendanceStatus === 'all' || (attendanceStatus === 'pending' ? !mark(session,s) : mark(session,s)?.status === attendanceStatus)) &&
    matchesSearch(`${s.name} ${s.id} ${s.className}`,attendanceTerm)
  );
}
function labelTables(root = page) {
  root.querySelectorAll('table').forEach(table => {
    const labels = [...table.querySelectorAll('thead th')].map(th => th.textContent);
    table.querySelectorAll('tbody tr').forEach(row => [...row.cells].forEach((cell,n) => { cell.dataset.label = labels[n] || ''; }));
  });
}
function refreshAttendanceRows() {
  const session = current();
  document.getElementById('attendance-rows').innerHTML = recentRows(session,true);
  labelTables(document.getElementById('attendance-rows'));
  document.getElementById('attendance-count').textContent = `${attendancePeople(session).length} / ${sessionPeople(session).length} em`;
  document.getElementById('clear-attendance-filters').disabled = attendanceClass === 'all' && attendanceStatus === 'all' && !attendanceTerm;
}
function clearAttendanceFilters() {
  attendanceClass='all';attendanceStatus='all';attendanceTerm='';
  document.getElementById('attendance-class').value='all';
  document.getElementById('attendance-status').value='all';
  document.getElementById('attendance-search').value='';
  refreshAttendanceRows();document.getElementById('attendance-search').focus({preventScroll:true});
}
function recentRows(session, editable = false) {
  const people = editable ? attendancePeople(session) : sessionPeople(session).filter(s => mark(session, s)).sort((a,b) => new Date(mark(session,b).timestamp) - new Date(mark(session,a).timestamp)).slice(0,5);
  if (editable && !people.length) return `<div class="empty-state">${i('search')}<h3>Không có em nào phù hợp</h3><p>Thử tên, mã thẻ hoặc điều chỉnh lớp và trạng thái.</p><button class="button button-secondary" data-clear-attendance>Bỏ bộ lọc</button></div>`;
  if (!people.length) return `<div class="empty-state">${i('users')}<p>Chưa có lượt điểm danh trong buổi này.</p><button class="button button-primary" data-route="attendance">Bắt đầu quét QR</button></div>`;
  return `<div class="table-wrap"><table><thead><tr><th scope="col">Thiếu nhi</th><th scope="col">Lớp</th><th scope="col">Trạng thái</th><th scope="col">Giờ ghi nhận</th></tr></thead><tbody>${people.map(s => { const m = mark(session,s),pending=offlineAttendance.find(session,s.id),scheduled=!!classes.find(c=>c.id===s.classId)?.calendar[session.activity]?.includes(session.date),makeup=session.activity==='mass'&&state.requests.some(r=>r.code===s.id&&r.kind==='makeup'&&r.status==='approved'&&makeupDate(r)===session.date),locked=session.closed||session.lockedClassIds?.includes(s.classId),reason=!scheduled?(makeup?'Buổi lễ bù đã được duyệt. Dùng Có mặt hoặc quét thẻ để ghi đúng ngày gốc.':'Ngày này không có hoạt động đã chọn trong lịch lớp. Chọn ngày hoặc hoạt động phù hợp.'):locked&&!state.isManager?'Buổi của lớp đã chốt. Liên hệ Admin nếu cần điều chỉnh.':''; return `<tr><td>${studentCell(s)}</td><td><span class="class-pill" data-level="${classLevelKey(s.className)}">${esc(s.className)}</span></td><td><div class="row-status-actions">${editable ? `<select class="state-select" data-state-id="${s.id}" aria-label="Trạng thái của ${esc(s.name)}" ${reason?`disabled aria-describedby="state-reason-${esc(s.id)}"`:''}><option value="" ${!m?'selected':''}>${waitingFor(session,s)?'Chờ lễ bù':'Chưa điểm danh'}</option><option value="X" ${m?.status==='X'?'selected':''}>Có mặt</option><option value="P" ${m?.status==='P'?'selected':''}>Nghỉ phép</option><option value="O" ${m?.status==='O'?'selected':''}>Vắng mặt</option></select>${!m&&!session.closed&&(scheduled||makeup)&&(!locked||state.isManager) ? `<button type="button" class="quick-attend-btn" data-quick-attend="${s.id}" title="Đánh có mặt cho ${esc(s.name)}">${i('check')}Có mặt</button>` : ''}` : statusLabel(m?.status)}</div>${editable&&reason?`<small class="attendance-state-reason" id="state-reason-${esc(s.id)}">${esc(reason)}</small>`:''}${requestAnnotation(session,s)}${pending?`<small class="offline-row-note">${pending.status==='blocked'?'Lượt trên thiết bị cần kiểm tra':'Đã giữ trên thiết bị · Chờ đồng bộ'}</small>`:''}${editable?`<button class="button button-text request-row-button" data-request-student="${s.id}">Xin phép / Đổi lễ</button>`:''}</td><td class="tabular">${m?.timestamp ? timeOf(m.timestamp) : m ? 'Đã có trong Excel' : '—'}</td></tr>`; }).join('')}</tbody></table></div>`;
}
function sessionCard(session) {
  const st = stats(session);
  const percentage = st.total ? Math.round(st.present / st.total * 100) : 0;
  return `<div class="card-body"><div class="session-title"><div><h3>${esc(activities[session.activity])}</h3><p>${esc(shortDate(session.date))} <span aria-hidden="true">·</span> ${esc(session.scope === 'all' ? 'Tất cả lớp ' : session.scope)}</p></div>${badge(session.closed ? 'Đã kết thúc' : 'Đang mở',session.closed)}</div><div class="progress-label"><span>Các em đã có mặt</span><strong>${st.present} / ${st.total} em</strong></div><div class="progress-track" role="progressbar" aria-label="Tỷ lệ có mặt" aria-valuenow="${percentage}" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill" style="width:${percentage}%"></div></div><div class="session-footer"><span>${i('checkcircle')}Đã kết nối Excel</span><button class="button button-soft" data-open-session="${session.id}">${session.closed ? 'Xem điểm danh' : 'Tiếp tục quét'}${i('arrow')}</button></div></div>`;
}
function overview() {
  const session = current();
  const st = stats(session);
  const openCount = state.sessions.filter(s => !s.closed).length;
  const percentage = st.total ? Math.round(st.present / st.total * 100) : 0;
  const remaining = st.total - st.present - st.permitted - st.absent;
  const classes = classNames.filter(c => session.scope === 'all' || c === session.scope);
  return `${heading('','Sổ giáo lý',longDate(today()),`<button class="button button-primary" data-route="attendance">${i('qr')}Mở điểm danh${i('arrow')}</button>`)}
    <section class="workspace-facts" aria-label="Danh sách "><span><strong class="stat-value">${students.length}</strong> thiếu nhi</span><span><strong class="stat-value">${classNames.length}</strong> lớp giáo lý</span><span><strong class="stat-value">${openCount}</strong> buổi đang mở</span><small>Đọc từ file lớp</small></section>
    <section class="attendance-ledger" aria-labelledby="ledger-title">
      <div class="ledger-main">
        <div class="ledger-title"><h2 id="ledger-title">${session.date===today()?'Điểm danh hôm nay':'Điểm danh ngày '+esc(shortDate(session.date))}</h2>${badge(session.closed ? 'Đã kết thúc' : 'Đang mở (Hằng ngày)', session.closed)}</div>
        <p class="ledger-session">${esc(activities[session.activity])}<span> ${shortDate(session.date)}</span></p>
        <div class="ledger-count"><strong>${st.present}</strong><span>/ ${st.total}<small>em có mặt trong buổi</small></span></div>
        <div class="progress-track" role="progressbar" aria-label="Tỷ lệ có mặt" aria-valuenow="${percentage}" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill" style="width:${percentage}%"></div></div>
        <p class="ledger-qualifier">${remaining-st.waiting} em chưa ghi nhận · ${st.permitted} nghỉ phép · ${st.absent} vắng mặt · ${st.waiting} chờ lễ bù</p>
        <button class="button button-primary" data-open-session="${session.id}">${i('qr')}${session.closed ? 'Xem kết quả' : 'Tiếp tục quét QR'}${i('arrow')}</button>
      </div>
      <div class="ledger-classes"><h3>Theo từng lớp</h3><div class="class-ledger">${classes.map(c=>{const people=sessionPeople(session).filter(s=>s.className===c);const present=people.filter(s=>mark(session,s)?.status==='X').length;return `<div class="class-ledger-row" data-level="${classLevelKey(c)}"><div><strong>${esc(c)}</strong><small>${people.length} thiếu nhi </small></div><span class="class-tally"><strong>${present}</strong> / ${people.length}</span></div>`;}).join('')}</div><button class="button button-text" data-route="students">Xem danh sách lớp${i('arrow')}</button></div>
    </section>
    <div class="dashboard-grid"><section class="card main-column"><div class="card-header"><h2>Vừa ghi nhận</h2><button class="button button-text" data-route="attendance">Xem tất cả${i('arrow')}</button></div>${recentRows(session)}</section><aside class="side-column"><section class="export-note"><span class="export-note-icon">${i('file')}</span><h2>File điểm danh của lớp</h2><p>Kết quả của buổi đang xem, sẵn sàng tải về theo từng lớp.</p><button class="button button-secondary" data-route="files">${i('download')}Tải file Excel</button><small>File lớp · Định dạng .xlsm</small></section></aside></div>
    <section class="future-ledger"><div><h2>Quản lý giáo lý</h2><p>Chọn phần cần xem hoặc cập nhật.</p></div><div class="future-links"><a href="#teachers">${i('teacher')}Giáo lý viên${i('arrow')}</a><a href="#grades">${i('chart')}Bảng điểm${i('arrow')}</a><a href="#care">${i('heart')}Theo dõi thiếu nhi${i('arrow')}</a></div></section>`;
}
function feedbackHtml() {
  const f = scanFeedback, student=f?.student;
  return `<div class="scan-result ${f?.kind || ''}" ${f?.kind==='pending'?'aria-busy="true"':''}><span class="result-icon">${i(f?.kind==='error'?'info':f?.kind==='warning'?'info':f?.kind==='success'?'checkcircle':'qr')}</span><div><strong>${esc(f?.title || 'Sẵn sàng nhận mã thẻ')}</strong><p>${esc(f?.description || 'Quét thẻ QR đã cấp hoặc nhập mã trên thẻ của học sinh.')}</p>${student?`<dl class="scan-student-details"><div><dt>Tên thánh</dt><dd>${esc(student._identityOnly?'Xem khi có kết nối':student.saintName||'Chưa có trong danh sách')}</dd></div><div><dt>Họ và tên</dt><dd>${esc(student.fullName)}</dd></div><div><dt>Lớp</dt><dd>${esc(student.className)}</dd></div><div><dt>Mã số</dt><dd class="tabular">${esc(student.id)}</dd></div></dl>`:''}</div></div>`;
}

function offlineSlot(){return state.mode==='cloud'?'<div id="offline-attendance-slot"></div>':'';}
function renderOfflinePanel(){
  const slot=document.getElementById('offline-attendance-slot');if(!slot)return;
  const expanded=[...slot.querySelectorAll('details[open]')].map(e=>e.className);
  slot.innerHTML=offlinePanel({entries:offlineAttendance.list(),...offlineAttendance.status(),online:navigator.onLine&&!connectionIssue&&!offlineRestored,esc,shortDate});
  for(const details of slot.querySelectorAll('details'))if(expanded.includes(details.className))details.open=true;
}
function syncOfflineScans(){
  if(offlineSyncTask||state.mode!=='cloud'||!connected||connectionIssue||offlineRestored||!navigator.onLine)return offlineSyncTask;
  if(!offlineAttendance.list().some(e=>e.status==='pending'))return;
  const epoch=authEpoch;
  offlineSyncTask=queueWrite(()=>offlineAttendance.sync(entry=>api('offline-scan',{
    id:entry.id,ownerId:entry.owner,yearId:entry.yearId,sessionId:entry.sessionId,code:entry.code,manual:entry.manual,
    capturedAt:entry.capturedAt,...(entry.obligationDate?{obligationDate:entry.obligationDate}:{})
  }),{isCurrent:()=>epoch===authEpoch&&!connectionIssue&&!offlineRestored,
    onResult:(result,entry)=>{
      applyServer(result.state);
      updateFeedback(result.duplicate||result.replayed?'duplicate':'success',result.duplicate||result.replayed?'Lượt này đã được ghi nhận':'Đã đồng bộ điểm danh',
        result.duplicate||result.replayed?'Máy chủ đã tiếp nhận lượt này trước đó; không ghi lại.':`Đã ghi có mặt cho ngày ${shortDate(result.creditedDate||entry.date)}.`,result.student);
    },onChoice:(result,entry)=>{if(scanCandidate?.code===entry.code||!document.querySelector('dialog[open]'))openScanChoice(result,entry.code,entry.manual,entry.id);}
  })).finally(()=>{
    offlineSyncTask=null;
    if(epoch===authEpoch&&view==='attendance'&&!document.querySelector('dialog[open]'))render();
  });
  return offlineSyncTask;
}
async function keepOfflineScan(session,student,manual,obligationDate){
  const epoch=authEpoch;
  try{
    const {duplicate}=await offlineAttendance.enqueue({yearId:state.yearId,session,student,manual,obligationDate});
    if(epoch!==authEpoch)return;
    updateFeedback('warning',duplicate?'Lượt này đang chờ đồng bộ':'Đã giữ lượt quét trên thiết bị',
      'Chưa tính có mặt. Hệ thống sẽ gửi lại khi kết nối được và đăng nhập còn hiệu lực.',student);
    const input=document.getElementById('student-code');if(input)input.value='';
    render();syncOfflineScans();
  }catch(error){
    if(epoch!==authEpoch)return;
    if(navigator.onLine&&!connectionIssue&&!offlineRestored){
      return queueWrite(async()=>{
        try{
          const result=await api('scan',{sessionId:session.id,code:student.id,manual,...(obligationDate?{obligationDate}:{})});
          if(result.choiceRequired){openScanChoice(result,student.id,manual);return;}
          applyServer(result.state);updateFeedback(result.duplicate?'duplicate':'success','Máy chủ đã ghi nhận lượt điểm danh',
            'Thiết bị chưa lưu được lượt chờ; giữ kết nối mạng để tiếp tục điểm danh.',result.student);render();
        }catch(failure){updateFeedback('error','Chưa giữ được lượt quét',failure.message,student);}
      });
    }
    updateFeedback('error','Chưa giữ được lượt quét',error.message,student);
  }
}

function pendingScansBanner(session) {
  const pending = (state.pendingScans || []).filter(p => 
    p.status === 'pending' &&
    p.date === session.date && p.activity === session.activity &&
    (session.scope === 'all' || p.className === session.scope || p.classId === classes.find(c => c.name === session.scope)?.id)
  );
  if (!pending.length) return '';
  return `<section class="card pending-scans-card" aria-labelledby="pending-scans-title">
    <div class="card-header">
      <div>
        <h2 id="pending-scans-title">Điểm danh chờ duyệt</h2>
        <p class="field-help">Có ${pending.length} em được điểm danh giùm trong buổi này</p>
      </div>
      <div class="feature-actions">
        <button type="button" class="button button-primary" data-approve-all-pending>Duyệt tất cả</button>
        <button type="button" class="button button-secondary" data-reject-all-pending>Bỏ qua tất cả</button>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Thiếu nhi</th>
            <th scope="col">Lớp</th>
            <th scope="col">Người quét giùm</th>
            <th scope="col">Thời gian</th>
            <th scope="col">Thao tác</th>
          </tr>
        </thead>
        <tbody>
          ${pending.map(p => `<tr>
            <td><strong>${esc(p.studentName || p.code)}</strong> <small>(${esc(p.code)})</small></td>
            <td>${esc(p.className || '')}</td>
            <td>${esc(p.scannedByName || '')}</td>
            <td>${esc(p.scannedAt ? new Date(p.scannedAt).toLocaleTimeString('vi-VN', {hour:'2-digit', minute:'2-digit'}) : '')}</td>
            <td>
              <div class="flex gap-2">
                <button type="button" class="button button-sm button-primary" data-approve-pending="${esc(p.id)}">Duyệt</button>
                <button type="button" class="button button-sm button-secondary" data-reject-pending="${esc(p.id)}">Bỏ qua</button>
              </div>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </section>`;
}

function sessionAttendanceGroups(session){
  const completed=completedMakeups(session);
  return groupSessionAttendance(sessionPeople(session),{
    markFor:student=>mark(session,student),isWaiting:student=>waitingFor(session,student),isMakeupDone:student=>completed.has(student.id)
  });
}
function sessionSummary(session){
  return sessionSummaryHtml(sessionAttendanceGroups(session),{esc,timeOf,closed:session.closed,
    earlyGroups:session.activity==='mass'?earlyMassAttendance(sessionPeople(session),state.marks,session.date):null,
    context:`${session.scope==='all'?'Tất cả lớp':session.scope} · ${activities[session.activity]} · ${shortDate(session.date)}`});
}
async function printSessionSummary(button){
  const session=current();if(!session||view!=='attendance'||!auth.user())return;
  const status=button.closest('.session-summary').querySelector('[data-summary-print-status]');
  const epoch=authEpoch,identifier=session.id,isCurrent=()=>epoch===authEpoch&&view==='attendance'&&current()?.id===identifier;
  const win=window.open('/print.html','_blank');
  if(!win){status.textContent='Trình duyệt đang chặn cửa sổ in. Cho phép mở cửa sổ bật lên rồi thử lại.';return;}
  win.opener=null;button.disabled=true;button.setAttribute('aria-busy','true');status.textContent='Đang chuẩn bị bản in…';
  try{
    const title=session.activity==='mass'?'Danh sách thiếu nhi tham dự Thánh lễ':`Danh sách ${activities[session.activity].toLocaleLowerCase('vi')}`;
    const html=sessionAttendancePrintHtml({groups:sessionAttendanceGroups(session),
      earlyGroups:session.activity==='mass'?earlyMassAttendance(sessionPeople(session),state.marks,session.date):null,
      scope:session.scope==='all'?'Tất cả lớp':session.scope,date:shortDate(session.date),activityLabel:activities[session.activity],year:state.year,title,closed:session.closed},{esc});
    await renderPrintWindow(win,html,{isCurrent});
    if(isCurrent()&&status.isConnected)status.textContent='Đã mở danh sách. Chọn In / Lưu PDF trong cửa sổ mới.';
  }catch(error){if(!win.closed)win.close();if(isCurrent()&&status.isConnected)status.textContent=error.message;}
  finally{if(button.isConnected){button.disabled=false;button.removeAttribute('aria-busy');if(isCurrent()&&document.activeElement===document.body)button.focus({preventScroll:true});}}
}
async function copyPresent(button){
  const session=current();if(!session||view!=='attendance'||!auth.user())return;
  const groups=sessionAttendanceGroups(session),kind=button.dataset.copyPresent;
  const text=presentClipboardText(groups,kind);if(!text)return;
  const epoch=authEpoch,identifier=session.id,panel=button.closest('[data-summary-group="present"]');
  const buttons=[...panel.querySelectorAll('[data-copy-present]')],status=panel.querySelector('[data-summary-copy-status]');
  const fallback=panel.querySelector('[data-summary-copy-fallback]'),input=panel.querySelector('[data-summary-copy-text]');
  const isCurrent=()=>epoch===authEpoch&&view==='attendance'&&current()?.id===identifier&&button.isConnected;
  fallback.hidden=true;input.value='';status.textContent='Đang sao chép…';
  buttons.forEach(control=>{control.disabled=true;control.setAttribute('aria-busy','true');});
  try{
    const copied=await copySessionText(text,{isCurrent});if(!isCurrent())return;
    if(copied)status.textContent=`Đã sao chép ${text.split('\n').length} ${kind==='codes'?'mã số':'tên Thánh, họ và tên'} của các em có mặt.`;
    else{
      status.textContent='Trình duyệt chưa cho phép sao chép tự động. Dùng nội dung bên dưới để sao chép thủ công.';
      fallback.hidden=false;input.value=text;input.focus({preventScroll:true});input.select();
    }
  }finally{
    buttons.forEach(control=>{if(control.isConnected){control.disabled=false;control.removeAttribute('aria-busy');}});
    if(isCurrent()&&document.activeElement===document.body)button.focus({preventScroll:true});
  }
}
function attendance() {
  const session = current();
  if(!session)return heading('','Điểm danh thiếu nhi','Mở buổi khi còn mạng để chuẩn bị điểm danh ngoại tuyến.')+offlineSlot()+attendanceSetup({fixedClass:state.isManager?'':workingClass,esc,classes,draft:attendanceDraft||{date:today(),activity:'mass',scope:workingClass},error:attendanceSetupError,activities,maxDate:today()});
  const st = stats(session);
  const sunday = isSunday(session.date);
  if(attendanceStage==='setup')return heading('','Điểm danh thiếu nhi','Chọn đúng buổi trước khi quét thẻ.')+offlineSlot()+attendanceSetup({fixedClass:state.isManager?'':workingClass,setupAnimation:animationStage('cat','setup-cat'),esc,classes,draft:attendanceDraft||{date:today(),activity:'mass',scope:workingClass},error:attendanceSetupError,activities,maxDate:today()});
  if(session.closed)return `${heading('','Đã kết thúc điểm danh',`${activities[session.activity]} · ${shortDate(session.date)} · ${session.scope==='all'?'Tất cả lớp':session.scope}`)}${flowSteps('finished')}${offlineSlot()}<section class="card session-complete"><div class="card-body"><span class="session-complete-icon" aria-hidden="true">${i('checkcircle')}</span><h2>Kết quả đã được lưu</h2><p>${st.present} em có mặt · ${st.permitted} em nghỉ phép · ${st.absent} em vắng không phép.</p><div class="feature-actions"><button class="button button-primary" data-route="files">${i('download')}Tải sổ lớp</button><button class="button button-secondary" id="change-attendance-session">Chọn buổi khác</button></div></div></section>${sessionSummary(session)}<details class="easy-advanced mt-6"><summary>Xem danh sách đã điểm danh</summary><p>${state.isManager?'Người quản lý có thể sửa từng em và ghi rõ lý do.':'Kết quả chi tiết của các em trong buổi đã kết thúc.'}</p><div id="attendance-rows">${recentRows(session,true)}</div></details>`;
  return `${heading('','Điểm danh thiếu nhi','Quét thẻ hoặc nhập tên; kết quả được lưu sau mỗi lượt.')}
  ${flowSteps(session.closed?'finished':'scan')}${offlineSlot()}
  <div class="easy-session-context"><div><strong>${esc(session.scope==='all'?'Tất cả lớp':session.scope)}</strong><small>${esc(activities[session.activity])} · ${shortDate(session.date)}</small></div><button type="button" class="button button-secondary" id="change-attendance-session">Đổi buổi</button></div>
  ${session.activity==='early'?`<div class="early-rule-card"><div class="early-rule-badge">⏰ QUY ĐỊNH ĐI LỄ SỚM</div><p>Khung giờ: <strong>06:00 — 06:20 sáng Chúa Nhật</strong></p><small>Chỉ ghi nhận các em quét thẻ từ 06:00 đến 06:20 sáng Chúa Nhật. Ngoài khung giờ này sẽ không được tính đi lễ sớm.</small></div>`:''}
  ${session.closed ? `<div class="closed-notice">${i('checkcircle')}<div><strong>Buổi điểm danh đã chốt</strong><p>Quản lý trên máy Excel có thể điều chỉnh riêng từng em, kèm lý do và lịch sử. Bạn vẫn có thể xem và tải kết quả.</p></div></div>` : ''}
  ${pendingScansBanner(session)}
  <div id="scan-feedback" class="session-feedback">${feedbackHtml()}</div><div id="scan-result-slot"></div><div class="scanner-methods" role="group" aria-label="Cách điểm danh"><button type="button" class="button button-secondary" data-scan-method="camera" aria-pressed="${scanMethod==='camera'}">${i('camera')}Quét camera</button><button type="button" class="button button-secondary" data-scan-method="text" aria-pressed="${scanMethod==='text'}">${i('keyboard')}Nhập mã / Tìm tên</button></div>
  <div class="scanner-grid"><div class="scanner-column"><section class="card" data-scan-panel="camera" ${scanMethod==='camera'?'':'hidden'}><div class="card-header"><h2><span>${i('camera')}</span>Quét QR</h2><button class="button button-primary" id="camera-toggle" ${session.closed?'disabled':''}>${i('camera')}${cameraStream?'Tắt camera':'Bật camera'}</button></div><div class="scanner-surface ${cameraStream?'live':''}" id="scanner-surface"><video id="camera-video" playsinline muted autoplay ${cameraStream?'':'hidden'}></video><div class="scan-frame" aria-hidden="true"></div><h3>Đặt mã QR vào khung hình</h3><p>Cho phép truy cập camera khi bạn muốn bắt đầu quét thẻ.</p></div><div class="camera-controls"><label class="button button-text" for="qr-image">Chọn ảnh QR</label><input id="qr-image" type="file" accept="image/*" class="qr-file-input" aria-label="Chọn ảnh mã QR trên thẻ" ${session.closed?'disabled':''}><button class="button button-text" data-focus-code>${i('keyboard')}Dùng mã thẻ</button></div><p id="camera-error" class="inline-message px-5 pb-4" role="status" hidden></p></section>
  <section class="card" data-scan-panel="text" ${scanMethod==='text'?'':'hidden'}><div class="card-body"><form id="code-form"><div class="manual-input-box"><div class="manual-input-header"><strong>${i('keyboard')}Nhập tay khi quên thẻ / Nhập sau lễ</strong><small>Nhập tên (vd: Lam Anh, Gia Bảo) hoặc mã thẻ (vd: XH22008), rồi nhấn Enter</small></div><div class="input-actions"><label class="field flex-1" for="student-code">Tên hoặc mã thiếu nhi<input id="student-code" name="code" autocomplete="off" spellcheck="false" placeholder="Ví dụ: Lam Anh, Gia Bảo hoặc XH22008..." aria-describedby="scan-feedback code-help" required ${session.closed?'disabled':''}></label><button class="button button-primary" type="submit" ${session.closed?'disabled':''}>${i('check')}Ghi nhận</button></div><p class="field-help code-help" id="code-help">💡 Hỗ trợ gõ không dấu. Nếu về nhà nhập sau, hệ thống tự động tìm đúng em và ghi vào Excel.</p></div></form></div></section></div>
  <aside class="scan-side"><section class="card"><div class="card-header"><h2>Kết quả buổi điểm danh</h2>${badge(session.closed?'Đã kết thúc':'Đang mở',session.closed)}</div><div class="card-body"><div class="scan-summary"><div><strong>${st.present}</strong><span>Có mặt</span></div><div><strong>${st.permitted}</strong><span>Nghỉ phép</span></div><div><strong>${st.pending}</strong><span>Chưa ghi nhận</span></div><div><strong>${st.absent}</strong><span>Vắng mặt</span></div></div><p class="field-help">${st.waiting} em chờ lễ bù · ${st.makeupDone} em đã quét lễ bù cho buổi khác · <a href="#requests">Xử lý xin phép / đổi lễ</a></p><div class="progress-label"><span>Đã ghi trạng thái</span><strong>${st.processed} / ${st.total} em</strong></div><div class="progress-track" role="progressbar" aria-label="Tỷ lệ đã ghi trạng thái" aria-valuenow="${st.total?Math.round(st.processed/st.total*100):0}" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill" style="width:${st.total?st.processed/st.total*100:0}%"></div></div><button class="button button-secondary w-full mt-4" data-route="files">${i('download')}Tải sổ lớp</button>${!session.closed?`<button class="button button-text w-full mt-2" id="close-session">Kết thúc điểm danh${i('checkcircle')}</button>`:`<p class="field-help mt-4">Buổi đã chốt. Bạn vẫn có thể xem và tải kết quả.</p>`}</div></section><section class="card"><div class="card-header"><h2>Các buổi đã mở</h2></div><div class="card-body small-session-list">${state.sessions.slice().reverse().map(s=>`<button class="session-choice ${s.id===session.id?'selected':''}" data-open-session="${s.id}"><span>${esc(activities[s.activity])}<small>${shortDate(s.date)} · ${esc(s.scope==='all'?'Tất cả lớp':s.scope)}</small></span>${i(s.closed?'checkcircle':'arrow')}</button>`).join('')}</div></section></aside></div>
  ${sessionSummary(session)}
  <section class="card attendance-register"><div class="card-header"><h2>Danh sách trong buổi</h2><span id="attendance-count" class="result-count" role="status" aria-live="polite">${attendancePeople(session).length} / ${st.total} em</span></div>
    <div class="register-filters"><label class="field search-field">Tìm thiếu nhi<input id="attendance-search" type="search" placeholder="Tên hoặc mã thẻ" value="${esc(attendanceTerm)}" aria-controls="attendance-rows"></label><label class="field" ${!state.isManager&&classes.length===1?'hidden':''}>Lớp<select id="attendance-class" aria-controls="attendance-rows"><option value="all">Tất cả lớp trong buổi</option>${classNames.filter(c=>session.scope==='all'||c===session.scope).map(c=>`<option ${attendanceClass===c?'selected':''}>${esc(c)}</option>`).join('')}</select></label><label class="field">Trạng thái<select id="attendance-status" aria-controls="attendance-rows">${[['all','Tất cả trạng thái'],['pending','Chưa điểm danh'],['X','Có mặt'],['P','Nghỉ phép'],['O','Vắng mặt']].map(([v,t])=>`<option value="${v}" ${attendanceStatus===v?'selected':''}>${t}</option>`).join('')}</select></label></div>
    <div class="register-legend"><span>Em chờ lễ bù chưa bị ghi vắng.</span><button class="button button-text" id="clear-attendance-filters" ${attendanceClass==='all'&&attendanceStatus==='all'&&!attendanceTerm?'disabled':''}>Bỏ bộ lọc</button></div><div id="attendance-rows">${recentRows(session,true)}</div></section>`;
}
function filterStudentRows(){
  let count=0;
  document.querySelectorAll('#student-rows tr').forEach(row=>{row.hidden=!matchesSearch(row.dataset.search,studentTerm);if(!row.hidden)count++;});
  document.getElementById('student-count').textContent=`${count} em`;
  document.getElementById('search-empty').hidden=count>0;
}
function studentView() {
  const people = scoped(studentFilter);
  return `${heading('THIẾU NHI & LỚP',state.isManager?'Danh sách các lớp':'Thiếu nhi lớp '+workingClass,'Tìm em, xem hồ sơ và liên hệ phụ huynh.',`<div class="feature-actions"><button class="button button-secondary" data-feature="print">${i('qr')}In thẻ QR theo lớp đang chọn</button>${state.isManager?`<button type="button" class="button button-primary" data-intake-student="${esc(classes.find(c=>c.name===studentFilter)?.id||'')}">Thêm thiếu nhi</button><button type="button" class="button button-secondary" data-intake-class>Tạo lớp mới</button><a class="button button-secondary" href="#classes">Quản lý lớp</a>`:''}</div>`)}
  ${state.isManager?`<div class="class-grid">${classNames.map(c=>`<button class="class-button ${studentFilter===c?'active':''}" aria-pressed="${studentFilter===c}" data-filter-class="${esc(c)}" data-level="${classLevelKey(c)}"><strong>${esc(c)}</strong><small>${scoped(c).length} thiếu nhi </small></button>`).join('')}</div>`:''}
  <div class="student-filters ${state.isManager?'':'student-filters-fixed'}">
    <label class="field" ${state.isManager?'':'hidden'}>Phạm vi lớp
      <select id="student-filter">
        <option value="all">Tất cả lớp </option>
        ${classNames.map(c=>`<option ${studentFilter===c?'selected':''}>${esc(c)}</option>`).join('')}
      </select>
    </label>
    <label class="field grow">Tìm thiếu nhi
      <input id="student-search" value="${esc(studentTerm)}" placeholder="Tên có hoặc không dấu, mã thẻ, số điện thoại" type="search" aria-controls="student-rows" aria-describedby="student-search-help">
    </label>
    <p id="student-search-help" class="field-help">Tìm trong ${esc(studentFilter==='all'?'tất cả lớp':studentFilter)}.</p>
  </div>
  <section class="card student-roster">
    <div class="card-header">
      <h2>${i('users')}Thiếu nhi trong danh sách</h2>
      <span id="student-count" class="text-xs text-slate-500">${people.length} em</span>
    </div>
    <div class="table-wrap">
      <table class="student-roster-table">
        <caption class="sr-only">Danh sách thiếu nhi và thao tác theo từng em</caption>
        <thead><tr><th scope="col">Thiếu nhi</th><th scope="col">Lớp giáo lý</th><th scope="col">Thao tác</th></tr></thead>
        <tbody id="student-rows">
          ${people.map(s=>`
            <tr data-search="${esc((s.name+' '+s.id).toLocaleLowerCase('vi-VN'))}">
              <td>${studentCell(s)}</td>
              <td><span class="class-pill" data-level="${classLevelKey(s.className)}">${esc(s.className)}</span><small class="block">${esc({active:'Đang học',paused:'Tạm nghỉ',left:'Nghỉ học'}[development.status(s.id)])}</small></td>
              <td>
                <div class="student-row-actions">
                  <button class="button button-soft button-xs" data-open-profile="${s.id}">Hồ sơ</button>
                  <button class="button button-soft button-xs" data-use-student="${s.id}">${i('qr')}Mã thẻ</button>
                  <button class="button button-text button-xs" data-request-student="${s.id}">Đơn phép</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    <div id="search-empty" class="empty-state" hidden><p>Không tìm thấy em trong lớp đang chọn. Thử tên không dấu hoặc mã thẻ.</p><div class="feature-actions"><button type="button" class="button button-secondary" id="clear-student-search">Xóa từ khóa</button><button type="button" class="button button-secondary" id="search-all-classes">Tìm tất cả lớp</button></div></div>
  </section>`;
}

let profileLoadId=0;
async function openProfile(code) {
  let s = students.find(x => x.id === code);
  if (!s) return;
  const load=++profileLoadId;
  if(state.mode==='cloud'){
    try{const detail=await api('student-detail?code='+encodeURIComponent(code));if(load!==profileLoadId)return;s={...s,...detail.student,className:s.className};}
    catch(error){toast(error.message);return;}
  }
  const dialog = document.getElementById('profile-dialog');
  document.getElementById('profile-dialog-title').textContent = 'Hồ sơ thiếu nhi';
  document.getElementById('profile-dialog-error').textContent = '';
  document.getElementById('profile-dialog-content').innerHTML = `
    <div class="profile-dialog-box">
      <div class="profile-summary-card">
        <span class="profile-avatar-large">${esc(s.name.split(' ').at(-1).slice(0,1))}</span>
        <div class="profile-meta">
          <strong>${esc(s.saintName ? s.saintName + ' ' : '')}${esc(s.fullName)}</strong>
          <small>Mã số: <span class="tabular font-bold">${esc(s.id)}</span> · Lớp: <span class="class-pill" data-level="${classLevelKey(s.className)}">${esc(s.className)}</span></small>
          ${s.phone ? parentContactMarkup(s,{esc,icon:i('phone'),names:false}) : ''}
        </div>
      </div>
      <input type="hidden" name="code" value="${esc(s.id)}">
      ${Number.isInteger(s.revision)?`<input type="hidden" name="expectedRevision" value="${s.revision}">`:''}
      ${development.profileActions(s)}
      <div class="profile-fields-grid">
        <label class="field">Tên thánh<input name="saintName" maxlength="100" value="${esc(s.saintName)}" aria-describedby="profile-dialog-error"></label>
        <label class="field">Họ và tên<input name="fullName" required minlength="2" maxlength="150" value="${esc(s.fullName)}" aria-describedby="profile-dialog-error"></label>
        <label class="field">Giới tính
          <select name="gender">
            <option value="" ${!s.gender ? 'selected' : ''}>— Chọn giới tính —</option>
            <option value="Nam" ${s.gender === 'Nam' ? 'selected' : ''}>Nam</option>
            <option value="Nữ" ${s.gender === 'Nữ' ? 'selected' : ''}>Nữ</option>
          </select>
        </label>
        <label class="field">Ngày sinh
          <input type="text" name="birthDate" value="${esc(s.birthDate || '')}" placeholder="dd/mm/yyyy">
        </label>
        <label class="field">Ngày rửa tội
          <input type="text" name="baptismDate" value="${esc(s.baptismDate || '')}" placeholder="dd/mm/yyyy">
        </label>
        ${state.mode==='cloud'?privacyUI.slot(s):contactFields(s,{esc})}
        <label class="field">Giáo họ (Họ lẻ)
          <input type="text" name="subParish" value="${esc(s.subParish || '')}" placeholder="Tên giáo họ">
        </label>
      </div>
      ${state.mode==='cloud'?'':`<label class="field">Địa chỉ thường trú<input type="text" name="address" value="${esc(s.address||'')}"></label>`}
    </div>
  `;
  dialog.showModal();
}

async function submitProfile(event) {
  event.preventDefault();
  const form = event.target;
  const values = Object.fromEntries(new FormData(form));
  const btn = document.getElementById('profile-save-btn');
  btn.disabled = true;
  document.getElementById('profile-dialog-error').textContent = 'Đang lưu hồ sơ…';
  await queueWrite(async () => {
    try {
      const result = await api('student-profile', encodeContactFields(values));
      applyServer(result.state);
      document.getElementById('profile-dialog').close();
      toast(`Đã lưu hồ sơ của ${result.student.name}.`);
      render();
    } catch (err) {
      document.getElementById('profile-dialog-error').textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });
}

function exportPlan(session,choice) {
  const people=scoped(session.scope).filter(s=>choice==='all'||s.className===choice);
  const count=new Set(people.map(s=>s.className)).size;
  const eligible=sessionPeople(session).filter(s=>choice==='all'||s.className===choice);
  const present=eligible.filter(s=>mark(session,s)?.status==='X').length;
  const permitted=eligible.filter(s=>mark(session,s)?.status==='P').length;
  const absent=eligible.filter(s=>mark(session,s)?.status==='O').length;
  return `<div class="export-plan"><div class="export-plan-heading"><span>${i('file')}</span><div><strong>${choice==='all'?`${count} file Excel trong một ZIP`:esc(choice)+' · Excel .xlsm'}</strong><small>${people.length} thiếu nhi trong sổ · ${eligible.length} em có lịch buổi ${shortDate(session.date)}</small></div></div><dl class="export-counts"><div><dt>Có mặt</dt><dd>${present}</dd></div><div><dt>Nghỉ phép</dt><dd>${permitted}</dd></div><div><dt>Vắng mặt</dt><dd>${absent}</dd></div><div><dt>Chưa ghi nhận</dt><dd>${eligible.length-present-permitted-absent}</dd></div></dl><p>${session.closed?'Buổi đã chốt, kết quả được giữ nguyên.':'Buổi đang mở. File phản ánh kết quả ở thời điểm tải.'}</p></div>`;
}
function refreshExportPlan() {
  document.getElementById('export-plan').innerHTML=exportPlan(current(),exportClass);
  document.querySelector('#export-submit span').textContent=exportClass==='all'?'Tải ZIP':'Tải Excel';
  document.getElementById('export-all').hidden=exportClass==='all';
}
function filesView() {
  const session = current();
  const st = stats(session);
  if(exportClass !== 'all' && session.scope !== 'all' && exportClass !== session.scope) exportClass='all';
  if(!state.isManager)exportClass=classes.length===1?workingClass:session.scope;
  return `${heading('BÁO CÁO & FILE','Báo cáo & tải sổ',state.isManager?'Chọn lớp và tải sổ đã có điểm danh, điểm học tập và tổng kết.':'Tải sổ của lớp '+esc(workingClass)+'.')}
  <section class="card easy-book"><div class="card-body"><h2>Tải hồ sơ của một lớp</h2><label class="field" ${state.isManager?'':'hidden'}>Lớp cần tải<select id="book-class"><option value="">Chọn lớp…</option>${classes.map(c=>`<option value="${esc(c.name)}" ${c.name===workingClass?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><button type="button" id="download-class-book" class="button button-primary" ${!workingClass||workingClass==='all'?'disabled':''}>${i('download')}${workingClass&&workingClass!=='all'?'Tải hồ sơ lớp '+esc(workingClass):'Chọn lớp để tải'}</button><p id="book-export-message" role="status" aria-live="polite">${!workingClass||workingClass==='all'?'Chọn một lớp để tải hồ sơ.':'Sổ hồ sơ lớp '+esc(workingClass)+' · cả năm học '+esc(document.querySelector('.year-card strong').textContent)+' · file .xlsm gồm điểm danh, kết quả học tập và hồ sơ của lớp.'}</p>${state.isManager?'<a class="button button-secondary" href="#excel">In / Lưu PDF</a>':''}</div></section>
  <details class="easy-advanced mt-6"><summary>Tải nhiều lớp hoặc theo buổi</summary>
  <div class="export-grid"><section class="card export-form-card"><div class="card-header"><h2>${i('file')}Xuất danh sách điểm danh</h2>${badge('Sổ lớp đã kết nối')}</div><div class="card-body"><div class="export-preview"><span>${i('file')}</span><div><strong>${esc(activities[session.activity])}</strong><small>${shortDate(session.date)} · ${st.total} em trong phạm vi buổi</small></div></div><form id="export-form"><label class="field">Buổi điểm danh<select id="export-session">${state.sessions.map(s=>`<option value="${s.id}" ${s.id===session.id?'selected':''}>${shortDate(s.date)} · ${esc(activities[s.activity])} · ${esc(s.scope==='all'?'Tất cả lớp':s.scope)}</option>`).join('')}</select></label><label class="field" ${!state.isManager&&classes.length===1?'hidden':''}>Lớp cần tải<select id="export-class"><option value="all" ${exportClass==='all'?'selected':''}>Tất cả lớp trong buổi</option>${classNames.filter(c=>session.scope==='all'||session.scope===c).map(c=>`<option ${exportClass===c?'selected':''}>${esc(c)}</option>`).join('')}</select></label><div id="export-plan">${exportPlan(session,exportClass)}</div><div class="flex flex-wrap gap-3"><button type="submit" id="export-submit" class="button button-primary">${i('download')}<span>${exportClass==='all'?'Tải ZIP':'Tải Excel'}</span></button><button type="button" id="export-all" class="button button-secondary" ${exportClass==='all'?'hidden':''}>${i('file')}Tải tất cả lớp (ZIP)</button></div><p id="export-message" class="field-help mt-4" role="status" aria-live="polite"></p></form></div></section><aside class="card export-info-card"><div class="card-header"><h2>File tải về gồm những gì?</h2></div><div class="card-body"><ul class="info-list"><li>${i('checkcircle')}Mã số, họ tên và lớp của các em.</li><li>${i('checkcircle')}Ngày, hoạt động, trạng thái X / O / P.</li><li>${i('checkcircle')}Nguyên mẫu sổ lớp, các tháng và công thức tổng kết.</li><li>${i('info')}File .xlsm thật của từng lớp, giữ nguyên VBA.</li></ul><div class="mt-6 border-t border-slate-100 pt-4"><p class="field-help">File tải xuống gồm toàn bộ năm học.</p></div></div></aside></div></details>
  <section class="card mt-6"><div class="card-header"><h2>${i('clock')}Các lần tải trên thiết bị này</h2></div>${state.downloads.length?`<div class="table-wrap"><table><thead><tr><th scope="col">File</th><th scope="col">Phạm vi</th><th scope="col">Thời gian</th></tr></thead><tbody>${state.downloads.slice().reverse().slice(0,8).map(d=>`<tr><td class="font-medium text-slate-700">${esc(d.filename)}</td><td>${esc(d.scope)}</td><td class="tabular">${shortDate(d.date)} · ${timeOf(d.timestamp)}</td></tr>`).join('')}</tbody></table></div>`:`<div class="empty-state">${i('download')}<p>Chưa tải file nào. Chọn buổi và lớp ở phía trên để tải bản đầu tiên.</p></div>`}</section>`;
}

function openTeachersDialog(classId) {
  const c = classes.find(x => x.id === classId);
  if (!c || !state.isManager) return;
  const t = c.teachers || {};
  document.getElementById('teachers-class-id').value = c.id;
  document.getElementById('teachers-dialog-title').textContent = `Phân công: ${c.name}`;
  document.getElementById('teachers-dialog-intro').textContent = `Chọn tài khoản phụ trách lớp ${c.name}. Người được chọn sẽ có quyền truy cập, quản lý và điểm danh lớp này.`;
  for(const slot of ['glv1','glv2','glv3','souer']) {
    const select=document.getElementById('teachers-'+slot);
    select.innerHTML='<option value="">Chưa phân công</option>'+state.accounts.filter(a=>a.active).map(a=>`<option value="${esc(a.id)}">${esc(a.displayName)} · ${esc(a.username)}</option>`).join('');
    const linkedAccount=state.accounts.find(a=>a.assignments.some(x=>x.class_id===classId&&x.slot===slot));
    select.value=linkedAccount?.id||'';
    if(t[slot]&&linkedAccount?.displayName!==t[slot]){
      const existing=document.createElement('option');existing.value='__excel__';existing.textContent=t[slot]+' · Chưa liên kết tài khoản';select.append(existing);select.value=existing.value;
    }
    let help=document.getElementById('teachers-existing-'+slot);
    if(!help){help=document.createElement('small');help.id='teachers-existing-'+slot;help.className='teacher-existing';select.after(help);select.setAttribute('aria-describedby',help.id+' teachers-dialog-error');}
    help.textContent='Phân công hiện tại: '+(t[slot]||'Chưa phân công');
  }
  document.getElementById('teachers-dialog-error').textContent = '';
  document.getElementById('teachers-dialog').showModal();
}

async function submitTeachers(event) {
  event.preventDefault();
  const form = event.target;
  const values = Object.fromEntries(new FormData(form));
  if(teacherSlots.some(([slot])=>values[slot]==='__excel__')){
    document.getElementById('teachers-dialog-error').textContent='Có tên trong sổ Excel chưa liên kết tài khoản. Tạo tài khoản cho người đó rồi chọn tại đây, hoặc chọn rõ “Chưa phân công” nếu muốn bỏ tên.';
    return;
  }
  const btn = document.getElementById('teachers-save-btn');
  btn.disabled = true;
  document.getElementById('teachers-dialog-error').textContent = 'Đang lưu phân công…';
  await queueWrite(async () => {
    try {
      const result = await api('teachers', {classId:values.classId,accountAssignments:Object.fromEntries(['glv1','glv2','glv3','souer'].map(slot=>[slot,values[slot]]))});
      applyServer(result.state);
      document.getElementById('teachers-dialog').close();
      toast('Đã cập nhật phân công giáo lý viên.');
      render();
    } catch (err) {
      document.getElementById('teachers-dialog-error').textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });
}

let gradesClassId = '';
let gradesSemester = 1;
let currentGradesData = null;
let gradesLoading = false;
let gradesLoadToken=0;
let gradesError='';
let gradeSavedMessage='';
let gradeFilters={query:'',assessment:'all',sort:'roster'};
let mobileGradeCode='';
let selectedGradeKind=gradeFields.some(([kind])=>kind===preferences.gradeKind)?preferences.gradeKind:'kt15';
let uncertainGradeSave=null;
function rememberGradeKind(kind){selectedGradeKind=kind;preferences.gradeKind=kind;save();}
const gradeColumn=createGradeColumnUI({data:()=>currentGradesData,api,queueWrite,esc,render,kind:()=>selectedGradeKind,rememberKind:rememberGradeKind,update:result=>{currentGradesData=result.grades;gradeSavedMessage=result.message||'Đã lưu điểm.';}});

async function loadGrades(classId, semester) {
  if(pendingWrites){toast('Đang lưu điểm. Chờ hoàn tất trước khi đổi bảng điểm.');return;}
  const token=++gradesLoadToken;
  gradesClassId = classId || classes.find(c=>c.name===workingClass)?.id || classes[0]?.id;
  const selectedClass=classes.find(c=>c.id===gradesClassId);if(selectedClass)rememberClass(selectedClass.name);
  gradesSemester = semester;
  currentGradesData=null;gradesError='';gradeSavedMessage='';
  gradesLoading = true;
  render();
  try {
    const data = await api(`grades?classId=${encodeURIComponent(gradesClassId)}&semester=${gradesSemester}`);
    if(token!==gradesLoadToken)return;
    currentGradesData = data;
  } catch (err) {
    if(token===gradesLoadToken)gradesError=err.message;
  } finally {
    if(token===gradesLoadToken){gradesLoading = false;render();}
  }
}

function gradesView() {
  if (!gradesClassId && classes.length) gradesClassId = classes[0].id;
  return `${heading('BẢNG ĐIỂM','Bảng điểm & Kết quả học tập',state.gradeMode==='portable'?'Chọn em, nhập điểm và xem kết quả sau khi lưu.':'Theo dõi và nhập điểm trực tiếp vào file Excel.',`<div class="feature-actions"><button class="button button-secondary" id="refresh-grade-table" ${gradesLoading?'disabled':''}>Làm mới bảng điểm</button><button class="button button-primary" id="download-grade-file" ${gradesLoading||!gradesClassId?'disabled':''}>${i('download')}Tải sổ lớp đang xem</button></div>`)}
  <div class="grades-control-bar">
    <div class="flex items-center gap-3" ${state.isManager?'':'hidden'}>
      <label class="field mb-0" ${state.isManager?'':'hidden'}><strong>Lớp học:</strong>
        <select id="grades-class-select">
          ${classes.map(c => `<option value="${esc(c.id)}" ${c.id === gradesClassId ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}
        </select>
      </label>
    </div>
    <div class="grades-sem-tabs">
      <button type="button" class="grades-sem-btn ${gradesSemester === 1 ? 'active' : ''}" data-change-sem="1">Học kỳ 1</button>
      <button type="button" class="grades-sem-btn ${gradesSemester === 2 ? 'active' : ''}" data-change-sem="2">Học kỳ 2</button>
      <button type="button" class="grades-sem-btn ${gradesSemester === 3 ? 'active' : ''}" data-change-sem="3">Tổng kết cả năm</button>
    </div>
  </div>
  <p id="grade-export-message" role="status" aria-live="polite"></p><p id="grade-saved-message" role="status" aria-live="polite">${esc(gradeSavedMessage)}</p>
  ${state.gradeMode==='portable'?'<details class="easy-help"><summary>Cách tính điểm</summary><p>TB HK gồm điểm khảo bài (KB 1–20) và kiểm tra/thi theo quy định trong sổ lớp. Mở mục Khảo bài để xem đầy đủ điểm thành phần. Nghỉ phép, điểm 0 và chưa nhập được xử lý riêng. Khi một cột đã có điểm, các em chưa có điểm ở cột đó có thể được tính là 0 theo mẫu.</p></details>':''}
  ${currentGradesData?.excelReady===false?'<p role="status" class="field-help">Điểm đã được lưu, Excel còn chờ cập nhật. Đóng file lớp nếu đang mở rồi bấm tải Excel để hoàn tất.</p>':''}
  ${currentGradesData?.exportConflict?`<div class="card p-4"><p role="alert">File Excel đã được sửa bên ngoài khi còn điểm chờ xuất. Hệ thống chưa ghi đè. Người quản lý cần đối chiếu bản chờ với file hiện tại.</p>${state.isManager?'<div class="feature-actions"><button class="button button-secondary" id="download-pending-grade-file">Tải bản điểm chờ để đối chiếu</button><button class="button button-secondary" id="review-grade-conflict">Xác nhận giữ file hiện tại</button></div>':''}</div>`:''}
  ${currentGradesData?.calculationIssues?.length?`<p role="alert" class="field-help">Công thức mẫu có ${currentGradesData.calculationIssues.length} ô chưa tính được. ${currentGradesData.calculationIssues.slice(0,3).map(x=>esc(x.sheet+'!'+x.cell+' '+x.error)).join('; ')}. Kiểm tra điểm/P và hệ số; hệ thống giữ lỗi hiển thị để đối chiếu.</p>`:''}
  ${gradesSemester===3&&currentGradesData?`<p class="field-help">Điều kiện đạt: điểm Giáo Lý ≥ ${esc(gradeValue(currentGradesData.thresholds?.catechism))} và điểm Thánh Lễ tổng hợp ≥ ${esc(gradeValue(currentGradesData.thresholds?.attendance))}, theo sổ lớp. — là chưa có dữ liệu; lỗi công thức được giữ để kiểm tra.</p><div class="feature-actions"><label class="field">Tìm thiếu nhi<input id="grade-search" type="search" value="${esc(gradeFilters.query)}" placeholder="Tên hoặc mã số"></label><label class="field">Đánh giá<select id="grade-assessment">${[['all','Tất cả'],['passed','Đạt'],['failed','Không đạt'],['unknown','Chưa đánh giá']].map(([v,t])=>`<option value="${v}" ${gradeFilters.assessment===v?'selected':''}>${t}</option>`).join('')}</select></label><label class="field">Sắp xếp<select id="grade-sort"><option value="roster" ${gradeFilters.sort==='roster'?'selected':''}>Theo danh sách</option><option value="rank" ${gradeFilters.sort==='rank'?'selected':''}>Theo hạng cả năm</option></select></label></div>`:''}
  <div id="grade-table-container">${gradesLoading ? loadingPanel('Đang mở bảng điểm','Đang đọc và tính kết quả học tập của lớp…') : gradesError?`<p role="alert">${esc(gradesError)}</p><button class="button button-secondary" id="reload-grades">Tải lại bảng điểm</button>`:renderGradesTable(currentGradesData)}</div>`;
}

function renderGradesTable(data) {
  if (!data || !data.students?.length) return `<div class="empty-state">${i('chart')}<p>Chưa có dữ liệu điểm cho lớp này.</p><button class="button button-primary" id="reload-grades">Tải lại</button></div>`;
  const isTerm = data.semester === 1 || data.semester === 2;
  const gradeRows=isTerm?data.students.filter(s=>matchesSearch(`${s.name} ${s.code}`,gradeFilters.query)):selectGradeRows(data.students,gradeFilters);
  if(!gradeRows.some(s=>s.code===mobileGradeCode))mobileGradeCode='';
  return `
    ${isTerm?`<div class="grade-work-actions"><label class="field">Tìm thiếu nhi<input id="grade-search" type="search" value="${esc(gradeFilters.query)}" placeholder="Tên có hoặc không dấu, mã thẻ" aria-controls="grade-table-container"></label>${data.revision?`<button type="button" id="toggle-grade-column" class="button button-secondary" aria-expanded="${gradeColumn.isVisible()}" aria-controls="grade-column-content">${gradeColumn.isVisible()?'Xem bảng điểm':'Nhập cùng loại điểm'}</button>`:""}</div>`:''}
    <div id="grade-column-content">${gradeColumn.page(gradeFilters.query)}</div>
    <div ${gradeColumn.isVisible()&&isTerm&&data.revision?'hidden':''}>
    <p role="status" aria-live="polite">${gradeRows.length} / ${data.students.length} thiếu nhi</p>
    <section class="grade-student-cards" aria-label="Điểm từng thiếu nhi"><label class="field">Chọn thiếu nhi<select id="grade-mobile-student"><option value="">Chọn em cần xem điểm…</option>${gradeRows.map(s=>`<option value="${esc(s.code)}" ${mobileGradeCode===s.code?'selected':''}>${esc(s.name)} · ${esc(s.code)}</option>`).join('')}</select></label><p id="grade-mobile-empty" ${mobileGradeCode?'hidden':''}>Chọn một em để xem kết quả và nhập điểm.</p>${gradeRows.map(s=>`<article class="grade-student-card" data-grade-card="${esc(s.code)}" ${mobileGradeCode===s.code?'':'hidden'}><strong>${esc(s.name)}</strong><small>${esc(s.code)} · ${esc(data.className)}</small>${isTerm&&missingGradeInputs(s)?'<p class="grade-source-note">Có TB HK nhưng chưa có điểm thành phần hiển thị. Cần đối chiếu sổ nguồn.</p>':''}<p>${isTerm?`Trung bình: ${esc(gradeValue(s.tbHk))} · ${esc(s.xepLoai||'Chưa xếp loại')}`:`${esc(s.assessment||'Chưa đánh giá')} · Tổng điểm: ${esc(gradeValue(s.totalScore))}`}</p>${isTerm?`<button type="button" class="button button-primary" data-edit-grade-mobile="${esc(s.code)}">Nhập điểm</button>`:''}<details><summary>Xem chi tiết điểm</summary>${isTerm?khaoBaiDetails(s,{esc,disclosure:false}):''}<dl>${(isTerm?[['Kiểm tra 15 phút',s.kt15],['Kiểm tra 1 tiết',s.kt1Tiet],['Thi kinh',s.thiKinh],['Thi học kỳ',s.thiHk],['Hạng học kỳ',s.xepHang]]:[['HK1',s.diemHk1],['HK2',s.diemHk2],['Giáo Lý',s.diemGiaoLy],['Thánh Lễ tổng hợp',s.combinedMassScore],['Hạng cả năm',s.yearRank],['Lễ bổ sung',s.supplementalMass]]).map(([label,value])=>`<div><dt>${label}</dt><dd>${esc(gradeValue(value))}</dd></div>`).join('')}</dl></details></article>`).join('')}</section>
    <div class="grades-table-wrap">
      <table class="grades-table">
        <thead>
          <tr>
            <th class="sticky-col">Thiếu nhi</th>
            ${isTerm ? `
              <th>Khảo bài</th>
              <th>KT 15'</th>
              <th>KT 1 Tiết</th>
              <th>Thi Kinh</th>
              <th>Thi HK</th>
              <th>TB HK</th>
              <th>Xếp Loại</th>
              <th>Hạng</th>
              <th>Điểm danh lễ</th>
              <th>Điểm danh GL</th>
              <th>Thao tác</th>
            ` : `
              <th>Điểm HK 1</th>
              <th>Điểm HK 2</th>
              <th>Điểm Giáo Lý</th>
              <th>Xếp Loại</th>
              <th>Điểm chuyên cần lễ</th>
              <th>Điểm chuyên cần giáo lý</th>
              <th>Điểm Thánh Lễ tổng hợp</th>
              <th>Đánh giá</th><th>Tổng điểm</th><th>Hạng cả năm</th><th>Lễ bổ sung</th>
            `}
          </tr>
        </thead>
        <tbody>
          ${gradeRows.map((s, idx) => `
            <tr>
              <td data-label="Thiếu nhi" class="sticky-col">
                <div class="flex items-center gap-2">
                  <span class="text-slate-400 tabular">${idx + 1}.</span>
                  <div>
                    <strong>${esc(s.name)}</strong>
                    <small class="block text-slate-500 tabular">${esc(s.code)}</small>
                  </div>
                </div>
              </td>
              ${isTerm ? `
                <td data-label="Khảo bài">${khaoBaiDetails(s,{esc})}${missingGradeInputs(s)?'<p class="grade-source-note">Có TB HK nhưng chưa có điểm thành phần hiển thị. Cần đối chiếu sổ nguồn.</p>':''}</td>
                <td data-label="KT 15'" class="font-bold tabular">${esc(gradeValue(s.kt15))}</td>
                <td data-label="KT 1 Tiết" class="font-bold tabular">${esc(gradeValue(s.kt1Tiet))}</td>
                <td data-label="Thi Kinh" class="font-bold tabular">${esc(gradeValue(s.thiKinh))}</td>
                <td data-label="Thi HK" class="font-bold tabular">${esc(gradeValue(s.thiHk))}</td>
                <td data-label="TB HK" class="font-bold text-amber-600 tabular">${esc(gradeValue(s.tbHk))}</td>
                <td data-label="Xếp Loại"><span class="grade-pill ${getGradeClass(s.xepLoai)}">${esc(s.xepLoai || '—')}</span></td>
                <td data-label="Hạng" class="font-bold tabular">${esc(s.xepHang ?? '—')}</td>
                <td data-label="Điểm danh lễ" class="tabular">${esc(gradeValue(s.massRatio))}</td>
                <td data-label="Điểm danh GL" class="tabular">${esc(gradeValue(s.lessonRatio))}</td>
                <td data-label="Thao tác">
                  <button class="button button-soft button-xs" data-edit-grade="${esc(s.code)}">
                    Nhập điểm
                  </button>
                </td>
              ` : `
                <td data-label="Điểm HK 1" class="font-bold tabular">${esc(gradeValue(s.diemHk1))}</td>
                <td data-label="Điểm HK 2" class="font-bold tabular">${esc(gradeValue(s.diemHk2))}</td>
                <td data-label="Điểm Giáo Lý" class="font-bold text-amber-600 tabular">${esc(gradeValue(s.diemGiaoLy))}</td>
                <td data-label="Xếp Loại"><span class="grade-pill ${getGradeClass(s.xepLoai)}">${esc(s.xepLoai || '—')}</span></td>
                <td data-label="Điểm chuyên cần lễ" class="tabular">${esc(gradeValue(s.massScore))}</td>
                <td data-label="Điểm chuyên cần giáo lý" class="tabular">${esc(gradeValue(s.lessonScore))}</td>
                <td data-label="Điểm Thánh Lễ tổng hợp" class="tabular">${esc(gradeValue(s.combinedMassScore))}</td>
                <td data-label="Đánh giá">${esc(gradeValue(s.assessment))}</td>
                <td data-label="Tổng điểm" class="tabular">${esc(gradeValue(s.totalScore))}</td>
                <td data-label="Hạng cả năm" class="tabular">${esc(gradeValue(s.yearRank))}</td>
                <td data-label="Lễ bổ sung" class="tabular">${esc(gradeValue(s.supplementalMass))}</td>
              `}
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div></div>
    ${!gradeRows.length?'<div class="empty-state"><p>Không tìm thấy em phù hợp.</p><button type="button" class="button button-secondary" id="clear-grade-search">Xóa từ khóa</button></div>':''}
  `;
}

function getGradeClass(val) {
  const norm = String(val || '').toLowerCase();
  if (norm.includes('giỏi')) return 'gioi';
  if (norm.includes('khá')) return 'kha';
  if (norm.includes('trung bình') || norm.includes('tb')) return 'tb';
  if (norm.includes('yếu') || norm.includes('kém')) return 'yeu';
  return '';
}

function refreshGradeEditor() {
  const fields=document.getElementById('grade-fields'),kind=document.getElementById('grade-kind').value;
  rememberGradeKind(kind);
  const full=fields.dataset.entry==='full';
  fields.querySelectorAll('[data-grade-field]').forEach(label=>label.hidden=!full&&label.dataset.gradeField!==kind);
  document.getElementById('grade-kind-label').hidden=full;
  document.getElementById('grade-permitted').hidden=full;
  document.getElementById('grade-show-all').setAttribute('aria-expanded',String(full));
  document.getElementById('grade-show-all').textContent=full?'Nhập một loại điểm':'Nhập nhiều loại điểm';
  const value=document.querySelector(`#grade-fields [name="${kind}"]`).value;
  document.getElementById('grade-permitted').setAttribute('aria-pressed',String(value.toUpperCase()==='P'));
  document.getElementById('grade-permitted').textContent=value.toUpperCase()==='P'?'Bỏ nghỉ phép':'Đánh dấu nghỉ phép';
}

function openGradesDialog(code, continuing=false) {
  if(pendingWrites&&!continuing){toast('Đang lưu điểm. Chờ hoàn tất rồi nhập em tiếp theo.');return;}
  if(uncertainGradeSave||gradeColumn.hasPending()){toast('Đang kiểm tra kết quả lượt lưu vừa rồi. Chờ xác nhận trước khi mở lượt nhập mới.');return;}
  if (!currentGradesData) return;
  const s = currentGradesData.students.find(x => x.code === code);
  if (!s) return;
  document.getElementById('grades-edit-class-id').value = gradesClassId;
  document.getElementById('grades-edit-semester').value = gradesSemester;
  document.getElementById('grades-edit-code').value = code;
  document.getElementById('grades-dialog-title').textContent = `Nhập điểm HK ${gradesSemester}`;
  document.getElementById('grades-dialog-error').textContent = '';
  document.getElementById('grades-student-header').innerHTML = `
    <div class="profile-summary-card mb-4">
      <div>
        <strong>${esc(s.saintName ? s.saintName + ' ' : '')}${esc(s.fullName || s.name)}</strong>
        <small class="block text-slate-500">Mã số: ${esc(s.code)} · Lớp: ${esc(currentGradesData.className)}</small>
      </div>
    </div>
  `;
  document.getElementById('grades-inputs-container').innerHTML = gradeEditor(s,{esc,kind:selectedGradeKind});
  const nextIndex=currentGradesData.students.findIndex(x=>x.code===code)+1;
  const next=currentGradesData.students[nextIndex];
  const nextButton=document.getElementById('grades-save-next');nextButton.disabled=!next;
  document.getElementById('grades-next-help').textContent=next?'Tiếp theo: '+next.name:'Đây là em cuối trong danh sách lớp.';
  refreshGradeEditor();
  document.getElementById('grades-dialog').showModal();
  document.querySelector(`#grade-fields [name="${selectedGradeKind}"]`)?.focus({preventScroll:true});
}

async function submitGrades(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const classId = formData.get('classId');
  const semester = parseInt(formData.get('semester'), 10);
  const code = formData.get('code');
  const khaoBai = [];
  for (let i = 0; i < 20; i++) {
    const val = formData.get(`kb_${i}`);
    khaoBai.push(val?.trim() ? val.trim() : null);
  }
  const parseScore = key => {
    const v = formData.get(key);
    return v?.trim() ? v.trim() : null;
  };
  const payload = {
    classId,
    semester,
    ...(currentGradesData.revision?{expectedRevision:currentGradesData.revision}:{}),
    grades: [{
      code,
      khaoBai,
      kt15: parseScore('kt15'),
      kt1Tiet: parseScore('kt1Tiet'),
      thiKinh: parseScore('thiKinh'),
      thiHk: parseScore('thiHk')
    }]
  };
  const btn = document.getElementById('grades-save-btn'),nextButton=document.getElementById('grades-save-next');
  const continueEntry=event.submitter?.id==='grades-save-next';
  const nextCode=currentGradesData.students[currentGradesData.students.findIndex(s=>s.code===code)+1]?.code;
  btn.disabled = true;nextButton.disabled=true;form.setAttribute('aria-busy','true');
  form.querySelectorAll('input,select').forEach(input=>input.disabled=true);
  document.getElementById('grades-dialog-error').textContent = 'Đang lưu điểm và tính kết quả cho cả lớp…';
  await queueWrite(async () => {
    try {
      const res = await api('grades', payload);
      currentGradesData = res.grades;
      gradeSavedMessage=res.excelReady===false?(res.message||'Điểm đã lưu; sổ còn chờ cập nhật.'):'Đã lưu điểm. Bạn có thể nhập cho em tiếp theo.';
      toast(res.message||'Đã lưu điểm.');
      if(continueEntry&&nextCode&&res.excelReady!==false){
        mobileGradeCode=nextCode;gradeFilters.query='';openGradesDialog(nextCode,true);
        document.getElementById('grades-dialog-error').textContent='Đã lưu điểm của em trước. Có thể nhập cho em tiếp theo.';
      }else if(res.excelReady===false&&continueEntry){
        document.getElementById('grades-dialog-error').textContent=gradeSavedMessage+' Hoàn tất cập nhật sổ trước khi nhập em tiếp theo.';
      }else{document.getElementById('grades-dialog').close();render();}
    } catch (err) {
      if(err.uncertain)uncertainGradeSave=payload;
      document.getElementById('grades-dialog-error').textContent = err.message;
    } finally {
      btn.disabled = false;
      const activeCode=document.getElementById('grades-edit-code').value;
      nextButton.disabled=!currentGradesData.students[currentGradesData.students.findIndex(s=>s.code===activeCode)+1];
      form.removeAttribute('aria-busy');
      form.querySelectorAll('input,select').forEach(input=>input.disabled=false);
    }
  });
}

async function verifyGradeSave(){
  if(!uncertainGradeSave)return;
  const pending=uncertainGradeSave;
  const latest=await api(`grades?classId=${encodeURIComponent(pending.classId)}&semester=${pending.semester}`);
  if(gradesMatch(latest,pending.grades)){
    if(gradesClassId===pending.classId&&gradesSemester===pending.semester)currentGradesData=latest;
    gradeSavedMessage='Đã kiểm tra: điểm của lượt vừa rồi đã được ghi nhận. Không cần lưu lại.';
    if(document.getElementById('grades-dialog').open)document.getElementById('grades-dialog-error').textContent=gradeSavedMessage;
  }else if(latest.revision===pending.expectedRevision){
    if(document.getElementById('grades-dialog').open)document.getElementById('grades-dialog-error').textContent='Lượt lưu vừa rồi chưa được ghi nhận. Nội dung vẫn được giữ; bạn có thể bấm Lưu.';
  }else if(document.getElementById('grades-dialog').open){
    document.getElementById('grades-dialog-error').textContent='Bảng điểm đã thay đổi. Nội dung của bạn được giữ; cần đối chiếu bảng điểm mới trước khi lưu lại.';
  }
  uncertainGradeSave=null;
}

async function downloadGradeFile(pending=false,bookClassId=null){
  const downloadEpoch=authEpoch;
  const targetClassId=bookClassId||gradesClassId;
  if(state.mode==='cloud'){if(!privacyUI.allowed('privateExport',targetClassId)){toast('Bạn chưa được cấp quyền tải hồ sơ đầy đủ của lớp này.');return;}if(!await privacyUI.confirmExport())return;}
  const button=document.getElementById(bookClassId?'download-class-book':pending?'download-pending-grade-file':'download-grade-file'),message=document.getElementById(bookClassId?'book-export-message':'grade-export-message');
  button.disabled=true;button.setAttribute('aria-busy','true');busyFeedback(message,'Đang chuẩn bị Excel với kết quả đã tính…');
  await queueWrite(async()=>{
    try{
      const response=await fetch('/api/'+(pending?'grade-pending-export':'grade-export')+'?classId='+encodeURIComponent(targetClassId),{cache:'no-store'});
      if(!response.ok){const result=await response.json();throw new Error(result.error||'Chưa xuất được Excel.');}
      const name=(pending?'DiemChoDoiChieu_':'')+(classes.find(c=>c.id===targetClassId)?.filename||'BangDiem.xlsm');
      const bytes=await response.arrayBuffer();if(downloadEpoch!==authEpoch)return;downloadBlob(bytes,name,response.headers.get('Content-Type'));
      message.textContent=pending?'Đã tải bản chờ để đối chiếu.':'Đã tải sổ lớp có kết quả điểm danh và học tập.';
    }catch(error){message.textContent=error.message;}finally{button.disabled=false;button.removeAttribute('aria-busy');}
  });
}

function reviewGradeConflict(){
  document.getElementById('grade-reconcile-error').textContent='';
  document.getElementById('grade-reconcile-actor').value=preferences.actor||'';
  document.getElementById('grade-reconcile-form').reset();
  document.getElementById('grade-reconcile-actor').value=preferences.actor||'';
  document.getElementById('grade-reconcile-dialog').showModal();
}

async function reconcileGrades(event){
  event.preventDefault();const form=event.target,button=form.querySelector('button[type=submit]');button.disabled=true;
  const values={...Object.fromEntries(new FormData(form)),classId:gradesClassId,semester:gradesSemester,expectedRevision:currentGradesData.revision,decision:'keep-file'};
  await queueWrite(async()=>{try{const result=await api('grade-reconcile',values);currentGradesData=result.grades;rememberActor(values.actor);document.getElementById('grade-reconcile-dialog').close();render();toast(result.message);}catch(error){document.getElementById('grade-reconcile-error').textContent=error.message;}finally{button.disabled=false;}});
}

let careClassFilter = 'all';
let careSearchTerm = '';
let careMonthFilter = 'all';

function careMarks(){
  const classIds=new Set(students.filter(s=>careClassFilter==='all'||s.className===careClassFilter).map(s=>s.id));
  return Object.fromEntries(Object.entries(state.marks).filter(([key])=>{
    const [date,,code]=key.split('|');if(!classIds.has(code))return false;
    if(careMonthFilter==='all')return true;
    if(['hk1','hk2'].includes(careMonthFilter)){
      const student=students.find(s=>s.id===code);
      return classes.find(c=>c.id===student?.classId)?.semesterMonths?.[careMonthFilter]?.includes(date.slice(0,7));
    }
    return date.startsWith(careMonthFilter+'-');
  }));
}

function calculateCareMetrics() {
  const people = students.filter(s =>
    (careClassFilter === 'all' || s.className === careClassFilter) &&
    matchesSearch(`${s.name} ${s.id} ${s.className}`,careSearchTerm)
  );
  const periodMarks=careMarks();
  const records = summarizeAttendance(people,periodMarks,'all');
  return { people, records };
}

function careView() {
  const { people, records } = calculateCareMetrics();
  const goodCount = records.filter(r => r.health === 'good').length;
  const warnCount = records.filter(r => r.health === 'warn').length;
  const dangerCount = records.filter(r => r.health === 'danger').length;
  const totalAbsent = records.reduce((sum, r) => sum + r.absentCount, 0);
  const months=[...new Set(classes.flatMap(c=>Object.values(c.calendar).flat()).map(d=>d.slice(0,7)))].sort();

  return `${heading('THEO DÕI THIẾU NHI','Chăm sóc & Chuyên cần','Đồng hành, theo dõi tiến độ chuyên cần, phát hiện kịp thời các em vắng nhiều để giáo lý viên nhắc nhở và thăm hỏi.')}
  <div class="care-kpi-grid">
    <div class="care-kpi-card">
      <div class="care-kpi-val text-emerald-600">${goodCount}</div>
      <div class="care-kpi-label">Chuyên cần tốt (≥ 80%)</div>
    </div>
    <div class="care-kpi-card">
      <div class="care-kpi-val text-amber-500">${warnCount}</div>
      <div class="care-kpi-label">Cần nhắc nhở (50–79%)</div>
    </div>
    <div class="care-kpi-card">
      <div class="care-kpi-val text-rose-600">${dangerCount}</div>
      <div class="care-kpi-label">Nguy cơ vắng nhiều (&lt; 50%)</div>
    </div>
    <div class="care-kpi-card">
      <div class="care-kpi-val text-slate-700">${totalAbsent}</div>
      <div class="care-kpi-label">Tổng lượt vắng không phép (O)</div>
    </div>
  </div>
  <div class="care-filters">
    <label class="field">Kỳ theo dõi<select id="care-month-filter"><option value="all" ${careMonthFilter==='all'?'selected':''}>Cả năm học</option><option value="hk1" ${careMonthFilter==='hk1'?'selected':''}>Học kỳ 1 (theo Excel)</option><option value="hk2" ${careMonthFilter==='hk2'?'selected':''}>Học kỳ 2 (theo Excel)</option>${months.map(m=>`<option value="${m}" ${m===careMonthFilter?'selected':''}>Tháng ${m.slice(5)}/${m.slice(0,4)}</option>`).join('')}</select></label>
    <label class="field" ${state.isManager?'':'hidden'}>Lớp học
      <select id="care-class-filter">
        <option value="all">Tất cả lớp (${students.length} em)</option>
        ${classNames.map(c => `<option value="${esc(c)}" ${c === careClassFilter ? 'selected' : ''}>${esc(c)}</option>`).join('')}
      </select>
    </label>
    <label class="field grow">Tìm kiếm
      <input type="search" id="care-search-input" value="${esc(careSearchTerm)}" placeholder="Tìm theo tên, mã thẻ hoặc lớp...">
    </label>
  </div>
  <p class="field-help">Thống kê theo ngày ghi trong Excel; lễ bù tính về ngày lễ gốc. ${records.filter(r=>r.health==='none').length} em chưa có dữ liệu trong kỳ này. Ô chưa điểm danh chưa tính là vắng.</p>
  <section class="card care-roster">
    <div class="card-header">
      <h2>${i('heart')}Danh sách theo dõi chuyên cần</h2>
      <span class="text-xs text-slate-500">${records.length} em</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Thiếu nhi</th>
            <th scope="col">Lớp</th>
            <th scope="col">Tỷ lệ</th>
            <th scope="col">Đi lễ (X)</th>
            <th scope="col">Phép (P)</th>
            <th scope="col">Vắng (O)</th>
            <th scope="col">Lễ sớm</th>
            <th scope="col">Học GL</th>
            <th scope="col">Thao tác</th>
          </tr>
        </thead>
        <tbody>
          ${records.map(r => `
            <tr>
              <td>${studentCell(r.student)}</td>
              <td><span class="class-pill" data-level="${classLevelKey(r.student.className)}">${esc(r.student.className)}</span></td>
              <td>
                <span class="health-badge ${r.health}">
                  ${r.ratio===null?'— · Chưa có dữ liệu':`${r.ratio}% · ${r.health === 'good' ? 'Tốt' : r.health === 'warn' ? 'Nhắc nhở' : 'Báo động'}`}
                </span>
              </td>
              <td class="tabular font-bold text-emerald-600">${r.massCount}</td>
              <td class="tabular font-bold text-amber-600">${r.permittedCount}</td>
              <td class="tabular font-bold text-rose-600">${r.absentCount}</td>
              <td class="tabular">${r.earlyCount}</td>
              <td class="tabular">${r.lessonCount}</td>
              <td>
                <div class="care-row-actions">
                  <button class="button button-soft button-xs" data-open-care-detail="${esc(r.student.id)}">
                    Chi tiết
                  </button>
                  ${r.student.phone ? parentContactMarkup(r.student,{esc,icon:i('phone'),names:false}) : ''}
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  </section>${development.alerts()}${development.insights()}${development.notesPanel()}`;
}

function openCareDetail(code) {
  const s = students.find(x => x.id === code);
  if (!s) return;
  const history = attendanceHistory(careMarks(),s.id,'all');

  document.getElementById('care-dialog-title').textContent = 'Lịch sử chuyên cần';
  document.getElementById('care-dialog-content').innerHTML = `
    <div class="profile-summary-card mb-4">
      <span class="profile-avatar-large">${esc(s.name.split(' ').at(-1).slice(0, 1))}</span>
      <div class="profile-meta">
        <strong>${esc(s.saintName ? s.saintName + ' ' : '')}${esc(s.fullName)}</strong>
        <small>Lớp: ${esc(s.className)} · Mã: ${esc(s.id)}</small>
        ${s.phone ? parentContactMarkup(s,{esc,icon:i('phone')}) : ''}
      </div>
    </div>
    <h3 class="font-bold text-slate-800 mb-2">Các buổi đã ghi nhận (${history.length} buổi):</h3>
    ${history.length ? `
      <div class="timeline-list">
        ${history.map(h => `
          <div class="timeline-item">
            <div>
              <strong>${esc(activities[h.activity] || h.activity)}</strong>
              <small class="block text-slate-500">${shortDate(h.date)}</small>
              ${state.requests.find(r=>r.code===code&&r.activity===h.activity&&r.day===h.date&&r.status==='completed'&&r.actual_day&&r.actual_day!==h.date)?`<small class="block text-slate-500">Đi thực tế ${shortDate(state.requests.find(r=>r.code===code&&r.activity===h.activity&&r.day===h.date&&r.status==='completed').actual_day)} · Lễ bù</small>`:''}
            </div>
            <div>
              ${statusLabel(h.status)}
            </div>
          </div>
        `).join('')}
      </div>
    ` : '<p class="text-slate-500 py-4 text-center">Chưa có lượt điểm danh nào được ghi nhận cho em này.</p>'}
  `;
  document.getElementById('care-dialog-content').insertAdjacentHTML('beforeend',`<button type="button" class="button button-secondary" data-feature="grade-progress" data-code="${esc(code)}">So sánh điểm HK1 / HK2</button>`+development.insights(code)+development.notesPanel(code));
  document.getElementById('care-dialog').showModal();
}

function render() {
  if(!connected)return;
  const activeId = document.activeElement?.id;
  const selection=document.activeElement?.selectionStart;
  const draftInput=document.getElementById('student-code');
  const codeDraft=draftInput?.value;
  const scrollPosition=window.scrollY;
  const activeStudent = document.activeElement?.dataset?.stateId||document.activeElement?.dataset?.quickAttend;
  if(view!=='attendance') stopCamera();
  const labels = { reports:'Báo cáo chuyên cần',celebrations:'Sinh nhật & bổn mạng GLV',classes:'Lớp giáo lý',staff:'Hồ sơ GLV',administration:'Quản trị hệ thống',notifications:'Thông báo & nhắc việc',start:'Công việc hôm nay',home:'Trang chủ', overview:'Tổng quan', attendance:'Điểm danh QR', students:'Thiếu nhi & lớp', files:'Báo cáo & tải sổ', requests:'Xin phép & đổi lễ', teachers:'Phân công GLV', grades:'Bảng điểm', care:'Theo dõi thiếu nhi',management:'Sao lưu & năm học',excel:'Sổ lớp & báo cáo',accounts:'Tài khoản & phân quyền' };
  document.getElementById('breadcrumb').textContent = labels[view] || 'Tổng quan';
  document.title = `${labels[view]} · Giáo Xứ Xuân Hoà`;
  document.querySelectorAll('[data-page]').forEach(a=>{a.className=cn('nav-item',a.dataset.page===view&&'active');if(a.dataset.page===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  document.querySelectorAll('[data-mobile-page]').forEach(a=>{a.className=cn('mobile-tab',a.dataset.mobilePage===view&&'active');if(a.dataset.mobilePage===view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  document.body.dataset.view = view;
  document.body.toggleAttribute('data-class-context',classPages.includes(view)&&classes.length>0);
  document.getElementById('mobile-menu-label').textContent=labels[view]||'Điều hướng';
  workContext();
  page.innerHTML = !classes.length&&classPages.includes(view)?'<section class="card auth-empty"><h1>Chưa được phân công lớp</h1><p>Liên hệ Admin để được phân công. Sau đó tải lại trang để mở sổ lớp.</p><a class="button button-secondary" href="#home">Về trang chủ</a></section>':view==='reports'?reportsUI.page():view==='classes'?enrollment.page():view==='staff'?management.staffDirectory():view==='administration'?management.page():view==='notifications'?management.notificationsPage():view==='accounts'?auth.accountsPage():view==='start'?startPage({singleClass:!state.isManager&&classes.length===1,esc,i,workingClass,today,longDate,students,requests:state.requests,sessions:state.sessions,careNotes:state.careNotes,pendingScans:state.pendingScans,offlineCount:offlineAttendance.list().length}):view==='home'?landing({i,esc,students,classNames,session:current(),stats,activities,shortDate,feedback:scanFeedback,classLevelKey,year:document.querySelector('.year-card strong').textContent}):view==='overview'?overview():view==='attendance'?attendance():view==='celebrations'?staffCalendar.page():view==='students'?studentView():view==='files'?filesView():view==='requests'?requestsPage(requestContext())+development.recurringPanel():view==='teachers'?teachersView():view==='grades'?gradesView():view==='care'?careView():view==='management'?development.managementPage():view==='excel'?parity.page():overview();
  management.restoreDrafts();
  attachStudentCombobox(document.getElementById('student-code'),{people:()=>sessionPeople(current())});
  if(renderedView!==view){
    if(!document.documentElement.hasAttribute('data-portal-transition')){
      page.querySelector('.page-heading')?.classList.add('motion-enter');
      if(view==='start')page.querySelectorAll('.easy-task').forEach(task=>task.classList.add('motion-enter'));
    }
    renderedView=view;
  }
  decorate(page);
  auth.chrome();
  renderOfflinePanel();
  renderScanBubble();
  labelTables();
  if(view==='students')filterStudentRows();
  if(codeDraft!==undefined&&view==='attendance'&&document.getElementById('student-code'))document.getElementById('student-code').value=codeDraft;
  if(activeId){const input=document.getElementById(activeId);input?.focus({preventScroll:true});if(selection!==null&&selection!==undefined&&['text','search','tel'].includes(input?.type))input.setSelectionRange(selection,selection);}
  window.scrollTo({top:scrollPosition,behavior:'instant'});
  if(activeStudent)(page.querySelector(`[data-state-id="${activeStudent}"]`)||document.getElementById('attendance-status'))?.focus({preventScroll:true});
  if(cameraStream && view==='attendance'){const video=document.getElementById('camera-video');video.srcObject=cameraStream;video.play().catch(()=>{});}
}
function route(name) { if(view===name){render();return;}portalTransition.enter(name); }
function routeFromHash() {
  if(!portalTransition.committing)portalTransition.cancel();
  if(!connected)return;
  const [name='start',query='']=(location.hash.slice(1)||'start').split('?');
  const routeParams=new URLSearchParams(query);
  view=['start','home','overview','reports','attendance','students','celebrations','files','requests','teachers','grades','care','management','excel','accounts','administration','notifications','staff','classes'].includes(name)?name:'start';
  if(view!=='attendance'){scanCandidate=null;if(scanConfirmation.open)scanConfirmation.close();}
  if(offlineRestored)view='attendance';
  if(!state.isManager&&adminPages.includes(view))view='start';
  if(view==='requests'){
    const filter=routeParams.get('filter');
    if(['all','pending','waiting','due','completed','missed','rejected','cancelled'].includes(filter)){requestFilter=filter;requestTerm='';}
    const requestedClass=routeParams.get('class');
    if(requestedClass&&(requestedClass==='all'||classNames.includes(requestedClass))&&!pendingWrites)rememberClass(requestedClass);
  }
  document.querySelector('.mobile-menu').open=false;
  openNavigationGroup(view);
  if(view==='excel'&&state.isManager&&!parity.ready()){parity.load(classes.find(c=>c.name===workingClass)?.id);}
  else if(view==='grades' && !gradesLoading && classes.length && (!currentGradesData||workingClass!=='all'&&workingClass&&currentGradesData.classId!==classes.find(c=>c.name===workingClass)?.id)) {
    loadGrades(classes.find(c=>c.name===workingClass)?.id||gradesClassId||classes[0].id, gradesSemester);
  } else {
    render();
  }
  window.scrollTo({top:0,behavior:'instant'});
}
function openSession(id) {
  if(pendingWrites){toast('Đang lưu dữ liệu. Chờ hoàn tất trước khi đổi buổi.');return;}
  const selected=state.sessions.find(s=>s.id===id);if(!selected)return;
  stopCamera();state.active=id;
  attendanceDraft={date:selected.date,activity:selected.activity,scope:selected.scope};
  attendanceStage=selected.date>today()?'setup':selected.closed?'finished':'scan';
  attendanceSetupError=selected.date>today()?'Buổi này chưa diễn ra. Chọn hôm nay hoặc một ngày đã qua.':'';
  rememberClass(selected.scope);scanFeedback=null;attendanceClass='all';attendanceStatus='all';attendanceTerm='';save();
  if(view==='attendance')render();else route('attendance');
}
async function switchDailySession(dateVal, activityVal, scopeVal) {
  if (pendingWrites) { toast('Đang ghi Excel. Chờ hoàn tất trước khi đổi ngày.'); return; }
  if ((activityVal === 'early' || activityVal === 'lesson') && !isSunday(dateVal)) {
    toast(`Buổi ${activities[activityVal] || activityVal} chỉ diễn ra vào Chúa Nhật. Đã chuyển sang Thánh lễ.`);
    activityVal = 'mass';
  }
  const existing = state.sessions.find(s => s.date === dateVal && s.activity === activityVal && s.scope === scopeVal);
  if (existing) {
    openSession(existing.id);
  } else {
    try {
      const res = await api('sessions', { date: dateVal, activity: activityVal, scope: scopeVal });
      applyServer(await api('bootstrap'));
      openSession(res.id);
    } catch (e) {
      toast(e.message);
    }
  }
}
function calendarHelp() {
  const form=document.getElementById('session-form'), values=new FormData(form);
  const days=[...new Set(classes.filter(c=>values.get('scope')==='all'||c.name===values.get('scope')).flatMap(c=>c.calendar[values.get('activity')]))].sort();
  const input=document.getElementById('session-date');
  if(!days.includes(input.value)) input.value=days.filter(d=>d<=today()).at(-1)||days[0]||'';
  input.min=days[0]||'';input.max=days.at(-1)||'';
  const nearby=days.filter(d=>d>=input.value).slice(0,5).map(shortDate).join(', ');
  document.getElementById('session-calendar-help').textContent='Lịch lấy từ Excel. Ngày phù hợp gần nhất: '+nearby+'. Các lớp khác nhau có thể có lịch Thánh lễ khác nhau.';
}
function newSession() {
  if(pendingWrites){toast('Đang ghi Excel. Chờ hoàn tất trước khi mở buổi mới.');return;}
  document.getElementById('session-date').value=today();
  document.getElementById('session-scope').innerHTML=`${state.isManager?'<option value="all">Tất cả lớp</option>':''}${classNames.map(c=>`<option ${c===workingClass?'selected':''}>${esc(c)}</option>`).join('')}`;
  document.getElementById('session-error').textContent='';calendarHelp();document.getElementById('session-dialog').showModal();
}
function updateFeedback(kind,title,description,student=null) {
  scanFeedback={kind,title,description,student};
  if(scanCandidate&&['saving','result'].includes(scanCandidate.phase)&&
    (student?.id===scanCandidate.code||scanCandidate.phase==='saving'&&!student)){
    scanCandidate.feedback={kind,title,description};
    scanCandidate.student=student||scanCandidate.student;
    scanCandidate.phase=kind==='pending'?'saving':'result';
    renderScanConfirmation();
  }
  scanBubbleDismissed=false;renderScanBubble();
  if(kind==='success')queueMicrotask(()=>{
    if(scanFeedback?.kind==='success')scanBubble.querySelector('.scan-bubble-icon')?.classList.add('motion-confirm');
  });
  const target=document.getElementById('scan-feedback');if(target)target.innerHTML=feedbackHtml();
  document.getElementById('scan-announcement').textContent=scanAnnouncement(scanFeedback);
  const input=document.getElementById('student-code');if(input){if(kind==='error')input.setAttribute('aria-invalid','true');else input.removeAttribute('aria-invalid');}
}
function findStudents(query, scope = 'all') {
  const raw = String(query || '').trim();
  if (!raw) return [];
  const cleanId = raw.toUpperCase().replace(/^\*|\*$/g, '');
  const byId = students.filter(s => s.id === cleanId && (scope === 'all' || s.className === scope));
  if (byId.length) return byId;

  const norm = searchable(raw);
  const byExact = students.filter(s =>
    (scope === 'all' || s.className === scope) &&
    (searchable(s.fullName) === norm || searchable(s.name) === norm)
  );
  if (byExact.length) return byExact;

  const byPartial = students.filter(s =>
    (scope === 'all' || s.className === scope) &&
    matchesSearch(`${s.fullName} ${s.name} ${s.id}`,raw)
  );
  return byPartial;
}

function handleManualAttendance(query) {
  const q = String(query || '').trim();
  if (!q) return;
  const session = current();
  const matches = findStudents(q, session.scope);
  if (!matches.length) {
    updateFeedback('error', 'Không tìm thấy thiếu nhi', `Không tìm thấy em nào có tên hoặc mã "${q}". Hãy kiểm tra lại danh sách hoặc chọn phạm vi lớp phù hợp.`);
    return;
  }
  if (matches.length === 1) {
    recordCode(matches[0].id, null, true);
  } else {
    openStudentChoice(q, matches);
  }
}

function openStudentChoice(query, matches) {
  const dialog = document.getElementById('student-choice-dialog');
  document.getElementById('student-choice-title').textContent = `Tìm thấy ${matches.length} em phù hợp`;
  document.getElementById('student-choice-desc').textContent = `Chọn đúng em cần điểm danh cho từ khóa "${query}":`;
  document.getElementById('student-choice-list').innerHTML = matches.map(s => `
    <li class="student-choice-item">
      <div>
        <strong>${esc(s.saintName ? s.saintName + ' ' : '')}${esc(s.fullName)}</strong>
        <span class="class-pill" data-level="${classLevelKey(s.className)}">${esc(s.className)}</span>
        <small class="tabular">${esc(s.id)}</small>
      </div>
      <button type="button" class="button button-primary button-xs" data-choose-student="${esc(s.id)}">
        ${i('check')}Ghi nhận em này
      </button>
    </li>
  `).join('');
  dialog.showModal();
}

function renderScanConfirmation(){
  if(!scanCandidate)return;
  const focused=scanConfirmation.contains(document.activeElement);
  scanConfirmation.dataset.phase=scanCandidate.phase;
  scanConfirmation.dataset.kind=scanCandidate.feedback?.kind||'pending';
  scanConfirmation.setAttribute('aria-busy',String(['lookup','saving'].includes(scanCandidate.phase)));
  scanConfirmation.innerHTML=scanConfirmationHtml(scanCandidate,{esc,i,classLevelKey,shortDate,activities});
  if(!scanConfirmation.open)scanConfirmation.showModal();
  if(focused||scanCandidate.phase==='confirm')scanConfirmation.querySelector('[data-confirm-scan],[data-cancel-scan]')?.focus({preventScroll:true});
}
function cancelScanConfirmation(){
  if(scanCandidate?.phase==='saving')return;
  scanCandidate=null;
  if(scanConfirmation.open)scanConfirmation.close();
}
async function recordCode(raw,obligationDate=null,manual=true){
  if(obligationDate)return commitCode(raw,obligationDate,manual);
  if(scanCandidate)return;
  const session=current(),code=String(raw||'').trim().toUpperCase().replace(/^\*|\*$/g,'');
  if(!session||!code)return;
  if(session.closed){updateFeedback('error','Buổi đã kết thúc','Mở một buổi chưa chốt để điểm danh.');return;}
  const candidate={code,manual,session:{...session},epoch:authEpoch,phase:'lookup',student:null,proxy:false};
  scanCandidate=candidate;renderScanConfirmation();
  try{
    const known=students.find(s=>s.id===code);
    const result=known&&(state.mode!=='cloud'||connectionIssue||offlineRestored||!navigator.onLine)?{student:known,proxy:session.scope!=='all'&&session.scope!==known.className}:
      await api('scan-preview',{sessionId:session.id,code});
    if(scanCandidate!==candidate||candidate.epoch!==authEpoch)return;
    candidate.student=result.student;candidate.proxy=result.proxy;candidate.phase='confirm';
    document.getElementById('scan-announcement').textContent=scanAnnouncement({title:'Đã nhận diện thiếu nhi',student:result.student,description:'Kiểm tra tên và bấm xác nhận để điểm danh.'});
  }catch(error){
    if(scanCandidate!==candidate||candidate.epoch!==authEpoch)return;
    candidate.phase='result';candidate.feedback={kind:'error',title:'Chưa nhận diện được thiếu nhi',description:error.message};
  }
  if(scanCandidate===candidate)renderScanConfirmation();
}
async function confirmScannedStudent(){
  const candidate=scanCandidate;
  if(!candidate||candidate.phase!=='confirm')return;
  if(candidate.epoch!==authEpoch||current()?.id!==candidate.session.id){cancelScanConfirmation();return;}
  candidate.phase='saving';candidate.feedback={kind:'pending',title:candidate.proxy?'Đang gửi điểm danh giùm':'Đang ghi nhận điểm danh',description:'Chờ hệ thống xác nhận kết quả.'};
  renderScanConfirmation();
  try{await commitCode(candidate.code,null,candidate.manual);}
  catch(error){if(scanCandidate===candidate)updateFeedback('error','Chưa ghi nhận điểm danh',error.message,candidate.student);}
}
function commitCode(raw,obligationDate=null,manual=true) {
  const scannedSession=current(),sessionId=scannedSession.id, code=String(raw||'').trim().toUpperCase().replace(/^\*|\*$/g,'');
  const recognized=students.find(s=>s.id===code)||null;
  if(state.mode==='cloud'&&recognized&&scannedSession.date===today()&&!scannedSession.closed&&
    (scannedSession.scope==='all'||scannedSession.scope===recognized.className)&&
    !(manual&&scannedSession.activity==='early'&&!earlyWindowOpen(scannedSession))){
    return keepOfflineScan(scannedSession,recognized,manual,obligationDate);
  }
  if(state.mode==='cloud'&&(connectionIssue||offlineRestored||!navigator.onLine)){
    updateFeedback('error','Chưa giữ được lượt quét','Chỉ giữ lượt quét cho thiếu nhi trong danh sách và buổi hôm nay đã mở khi có mạng.',recognized);return;
  }
  if(manual&&scannedSession.activity==='early'&&!earlyWindowOpen(scannedSession)&&students.some(s=>s.id===code)){
    if(!state.isManager){updateFeedback('error','Cần xác nhận nhập bổ sung','Nhờ người quản lý trên máy Excel xác nhận giờ đi lễ thực tế và lý do.');return;}
    if(scanCandidate?.code===code){scanCandidate.phase='choice';if(scanConfirmation.open)scanConfirmation.close();}
    openCorrection(code,'X',true);return;
  }
  const job=sessionId+'|'+code;
  if(queuedCodes.has(job))return;
  queuedCodes.add(job);
  return queueWrite(async()=>{
    updateFeedback('pending',recognized?'Đã nhận diện thiếu nhi':'Đang kiểm tra mã','Đang cập nhật file lớp. Chờ thông báo đã lưu.',recognized);
    try {
      const result=await api('scan',{sessionId,code,manual,...(obligationDate?{obligationDate}:{})});if(result.choiceRequired){openScanChoice(result,code,manual);return;}applyServer(result.state);
      if(result.pending){
        updateFeedback('warning',result.duplicate?'Yêu cầu đã được ghi nhận':'Đã ghi nhận điểm danh giùm',result.message,result.student);
        render();
        const input=document.getElementById('student-code');if(input){input.value='';if(manual&&!input.closest('[hidden]')){input.scrollIntoView({block:'center',behavior:'instant'});input.focus({preventScroll:true});}}
        return;
      }
      const attendanceDescription=result.isMakeup?`Đi lễ ngày ${shortDate(result.actualDate)} · Đã ghi có mặt cho ngày ${shortDate(result.creditedDate)} trong Excel theo đơn đổi lễ đã duyệt.`:`Đã ghi có mặt cho ngày ${shortDate(result.creditedDate||scannedSession.date)}. File lớp đã lưu.`;
      updateFeedback(result.duplicate?'duplicate':'success',result.duplicate?'Lượt đi lễ đã được ghi nhận':'Đã lưu vào Excel',result.message||(result.duplicate?'Không ghi thêm lượt trùng.':attendanceDescription),result.student);
      render();
      const input=document.getElementById('student-code');if(input){input.value='';if(manual&&!input.closest('[hidden]')){input.scrollIntoView({block:'center',behavior:'instant'});input.focus({preventScroll:true});}}
    } catch(error) { updateFeedback('error','Chưa ghi nhận điểm danh',error.message,recognized); }
    finally {queuedCodes.delete(job);}
  });
}
async function changeMark(code,status,actor,reason,attendedTime) {
  const sessionId=current().id, button=document.querySelector('#correction-form button[type=submit]');button.disabled=true;
  return queueWrite(async()=>{
    updateFeedback('pending','Đang cập nhật trạng thái','Đang lưu thay đổi vào sổ lớp.');
    try { const result=await api('mark',{sessionId,code,status,actor,reason,...(attendedTime?{attendedTime}:{})});applyServer(result.state);updateFeedback('success','Đã lưu trạng thái vào Excel',status?`Trạng thái ${status} đã lưu.${result.attendedAt?' Giờ đi thực tế: '+timeOf(result.attendedAt)+'.':''}`:'Đã xoá trạng thái điểm danh.',result.student);document.getElementById('correction-dialog').close();render(); }
    catch(error){document.getElementById('correction-error').textContent=error.message;}
    finally{button.disabled=false;}
  });
}
async function closeSession() {
  if(state.mode==='cloud'&&offlineAttendance.status().ready){try{await offlineAttendance.reload();}catch(error){document.getElementById('close-error').textContent=error.message;return;}}
  if(offlineAttendance.pendingFor(current()).length){document.getElementById('close-error').textContent='Còn lượt quét trên thiết bị. Đồng bộ hoặc kiểm tra từng lượt trước khi chốt buổi.';return;}
  const sessionId=current().id, button=document.getElementById('confirm-close');button.disabled=true;
  button.setAttribute('aria-busy','true');
  busyFeedback(document.getElementById('close-error'),'Đang cập nhật các file lớp…');
  return queueWrite(async()=>{
    try {const result=await api('close',{sessionId,...(state.mode==='cloud'?{previewToken:closePreviewToken}:{})});applyServer(result.state);stopCamera();document.getElementById('close-dialog').close();scanFeedback=null;render();celebrateSession(page);}
    catch(error){document.getElementById('close-error').textContent=error.message+(state.mode==='cloud'?' Bấm Kiểm tra lại trước khi xác nhận.':' Các lớp đã lưu giữ kết quả; bấm Xác nhận kết thúc để tiếp tục phần còn lại.');applyServer(await api('bootstrap'));}
    finally {button.disabled=state.mode==='cloud';button.removeAttribute('aria-busy');}
  });
}

async function approvePending(id) {
  if (pendingWrites) return;
  return queueWrite(async () => {
    try {
      const res = await api('pending-scans-approve', { id });
      applyServer(res.state);
      toast(res.message || 'Đã duyệt điểm danh giùm.');
      render();
    } catch (e) {
      toast(e.message);
    }
  });
}

async function rejectPending(id) {
  if (pendingWrites) return;
  return queueWrite(async () => {
    try {
      const res = await api('pending-scans-reject', { id });
      applyServer(res.state);
      toast(res.message || 'Đã bỏ qua yêu cầu điểm danh giùm.');
      render();
    } catch (e) {
      toast(e.message);
    }
  });
}

async function approveAllPending(session) {
  if (pendingWrites) return;
  const targetClass = classes.find(c => c.name === session.scope);
  return queueWrite(async () => {
    try {
      const res = await api('pending-scans-approve', { all: true, classId: targetClass?.id, sessionId: session.id });
      applyServer(res.state);
      toast(res.message || 'Đã duyệt tất cả điểm danh giùm.');
      render();
    } catch (e) {
      toast(e.message);
    }
  });
}

async function rejectAllPending(session) {
  if (pendingWrites) return;
  const targetClass = classes.find(c => c.name === session.scope);
  return queueWrite(async () => {
    try {
      const res = await api('pending-scans-reject', { all: true, classId: targetClass?.id, sessionId: session.id });
      applyServer(res.state);
      toast(res.message || 'Đã bỏ qua tất cả yêu cầu điểm danh giùm.');
      render();
    } catch (e) {
      toast(e.message);
    }
  });
}

function requestContext() {const visibleStudents=workingClass&&workingClass!=='all'?students.filter(s=>s.className===workingClass):students;const codes=new Set(visibleStudents.map(s=>s.id));return {state:{...state,requests:state.requests.filter(r=>codes.has(r.code))},students:visibleStudents,esc,i,shortDate,activities,studentCell,filter:requestFilter,term:requestTerm,searchable,today};}
function refreshRequests(){const target=document.getElementById('requests-rows');if(target){target.innerHTML=requestTable(requestContext());labelTables(target);}}
function rememberActor(actor){preferences.actor=auth.user()?.displayName||actor;save();}
function fillActors(dialog){dialog.querySelectorAll('.actor-input').forEach(e=>e.value=preferences.actor||'');}
function validateRequestStep(step){
  const code=document.getElementById('request-code'),raw=searchable(code.value.trim());
  const matches=students.filter(s=>(!workingClass||workingClass==='all'||s.className===workingClass)&&(searchable(s.id)===raw||searchable(s.name)===raw||searchable(s.fullName)===raw));
  if(matches.length!==1)return matches.length>1?'Có nhiều em cùng tên. Chọn đúng mã trong danh sách gợi ý.':'Chọn một em trong danh sách gợi ý; có thể gõ tên hoặc mã trên thẻ.';
  code.value=matches[0].id;requestFormHelp();
  if(step!==2)return '';
  const kind=document.getElementById('request-kind').value,d=document.getElementById('request-date').value;
  const activity=kind==='makeup'?'mass':document.getElementById('request-activity').value,c=classes.find(c=>c.id===matches[0].classId);
  const days=activity==='both'?c.calendar.mass.filter(d=>c.calendar.lesson.includes(d)):c.calendar[activity];
  if(!days?.includes(d))return 'Ngày này không có trong lịch của lớp. Chọn một ngày phù hợp trong phần gợi ý.';
  if(kind==='makeup'){
    const target=document.getElementById('request-target').value;
    const monday=v=>{const date=new Date(v+'T12:00:00Z');date.setUTCDate(date.getUTCDate()-(date.getUTCDay()+6)%7);return date.toISOString().slice(0,10);};
    if(isSunday(d)||isSunday(target)||d===target||monday(d)!==monday(target))return 'Hai ngày phải khác nhau, cùng tuần, từ thứ Hai đến thứ Bảy.';
  }
  return '';
}
function openRequest(code=''){
  if(pendingWrites){toast('Đang ghi Excel. Chờ hoàn tất trước khi lập đơn.');return;}
  const dialog=document.getElementById('request-dialog'),form=document.getElementById('request-form');form.reset();fillActors(dialog);
  attachStudentCombobox(document.getElementById('request-code'),{people:()=>students});
  document.getElementById('request-code').value=code;document.getElementById('request-date').value=current().date;
  document.getElementById('request-activity').value=current().activity;
  document.getElementById('request-error').textContent='';requestFormHelp();dialog.showModal();requestWizard(form,()=>{const v=Object.fromEntries(new FormData(form));const person=students.find(s=>s.id===String(v.code).trim().toUpperCase());return [person?.name||v.code,person?.className||'',v.kind==='makeup'?'Đổi ngày đi lễ':'Xin nghỉ phép',v.date,v.targetDate?'Đi thay vào '+v.targetDate:''].filter(Boolean).join(' · ');},validateRequestStep);
}
function requestFormHelp(){
  const form=document.getElementById('request-form'),v={code:document.getElementById('request-code').value,date:document.getElementById('request-date').value},student=students.find(s=>s.id===v.code.trim().toUpperCase());
  document.getElementById('request-person').textContent=student?student.name+' · '+student.className:'Chọn đúng học sinh trong danh sách Excel.';
  const isMakeup=document.getElementById('request-kind').value==='makeup';document.getElementById('replacement-field').hidden=!isMakeup;
  const input=document.getElementById('request-target');input.required=isMakeup;input.disabled=!isMakeup;
  const activity=document.getElementById('request-activity');if(isMakeup)activity.value='mass';activity.disabled=isMakeup;
  // Disabled activity fields are restored explicitly when the form is submitted.
  if(v.date&&isMakeup){const d=new Date(v.date+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-(d.getUTCDay()+6)%7);input.min=d.toISOString().slice(0,10);d.setUTCDate(d.getUTCDate()+5);input.max=d.toISOString().slice(0,10);}
  const sunday=v.date&&new Date(v.date+'T12:00:00Z').getUTCDay()===0;
  document.querySelector('#request-kind option[value="makeup"]').disabled=!!sunday;
  const chosen=isMakeup?'mass':activity.value, classroom=classes.find(c=>c.id===student?.classId);
  const days=chosen==='both'?classroom?.calendar.mass.filter(d=>classroom.calendar.lesson.includes(d)):classroom?.calendar[chosen];
  document.getElementById('request-calendar-help').textContent=sunday&&isMakeup?'Chủ nhật không được đổi ngày.':days?`Ngày gốc theo lịch lớp. Các ngày gần nhất: ${days.filter(d=>d>=v.date).slice(0,4).map(shortDate).join(', ')}.${isMakeup?' Ngày bù phải khác ngày gốc, cùng tuần và không phải Chủ nhật.':''}`:'Chọn học sinh để xem lịch của lớp.';
}
async function submitRequest(event){
  const form=event.target,v=Object.fromEntries(new FormData(form)),approve=event.submitter?.value==='approve';
  v.kind=document.getElementById('request-kind').value;
  v.activities=v.kind==='makeup'?['mass']:v.activity==='both'?['mass','lesson']:[v.activity];
  rememberActor(v.actor);form.querySelectorAll('button[type=submit]').forEach(b=>b.disabled=true);
  await queueWrite(async()=>{
    let created=false;
    try{
      const result=await api('requests',v);created=true;applyServer(result.state);document.getElementById('request-dialog').close();route('requests');
      if(approve){const reviewed=await api('review',{id:result.requestIds[0],decision:'approve',actor:v.actor,reason:v.reason});applyServer(reviewed.state);}
      render();document.getElementById('requests-message').textContent=approve?'Đã duyệt đơn và cập nhật Excel.':'Đã gửi đơn chờ duyệt.';
    }catch(error){
      if(created){try{applyServer(await api('bootstrap'));}catch{}render();const box=document.getElementById('requests-message');if(box)box.textContent='Đơn đã lưu; còn mục chưa duyệt. '+error.message;}
      else document.getElementById('request-error').textContent=error.message;
    }finally{form.querySelectorAll('button[type=submit]').forEach(b=>b.disabled=false);}
  });
}
function openReview(id,decision){
  const r=state.requests.find(r=>r.id===id),student=students.find(s=>s.id===r.code);reviewId=id;reviewDecision=decision;
  const dialog=document.getElementById('review-dialog'),form=document.getElementById('review-form');form.reset();fillActors(dialog);
  const titles={approve:'Duyệt đơn',reject:'Không duyệt đơn',cancel:'Huỷ đơn đã lập'};
  document.getElementById('review-title').textContent=titles[decision];document.getElementById('review-submit').textContent=titles[decision];
  document.getElementById('review-details').textContent=`${student.name} · ${shortDate(r.day)}${r.target_day?' → '+shortDate(r.target_day):''}. ${decision==='cancel'?'Huỷ đơn phép sẽ trả về chưa điểm danh hoặc O nếu buổi đã chốt.':'Các mục còn chờ duyệt cùng đơn sẽ được xử lý.'}`;
  if(decision==='approve')form.elements.reason.value=r.reason;
  document.getElementById('review-error').textContent='';dialog.setAttribute('role',decision==='approve'?'dialog':'alertdialog');dialog.showModal();
}
async function submitReview(event){
  const form=event.target,v=Object.fromEntries(new FormData(form));rememberActor(v.actor);const button=document.getElementById('review-submit');button.disabled=true;
  await queueWrite(async()=>{try{const result=await api('review',{...v,id:reviewId,decision:reviewDecision});applyServer(result.state);document.getElementById('review-dialog').close();render();}
  catch(error){try{applyServer(await api('bootstrap'));}catch{}document.getElementById('review-error').textContent=error.message;}
  finally{button.disabled=false;}});
}
function openReschedule(id){
  if(pendingWrites){toast('Đang ghi Excel. Chờ hoàn tất trước khi dời buổi.');return;}
  const r=state.requests.find(r=>r.id===id),student=students.find(s=>s.id===r?.code);
  if(!r||!student)return;
  rescheduleId=id;
  const dialog=document.getElementById('reschedule-dialog'),form=document.getElementById('reschedule-form');form.reset();fillActors(dialog);
  document.getElementById('reschedule-person').textContent=student.name+' · '+student.className;
  document.getElementById('reschedule-details').textContent=`Lễ gốc: ${shortDate(r.day)} · Ngày đã xin: ${shortDate(r.target_day)}${r.exception_day?' · Ngoại lệ hiện tại: '+shortDate(r.exception_day):''}.${r.status==='missed'?' Buổi đã chốt vắng; thao tác này mở lại riêng buổi đó.':''}`;
  const input=document.getElementById('reschedule-date'),start=new Date(r.day+'T12:00:00Z');start.setUTCDate(start.getUTCDate()-(start.getUTCDay()+6)%7);input.min=start.toISOString().slice(0,10);start.setUTCDate(start.getUTCDate()+5);input.max=start.toISOString().slice(0,10);input.value=makeupDate(r);input.removeAttribute('aria-invalid');
  document.getElementById('reschedule-error').textContent='';dialog.showModal();
}
async function submitReschedule(event){
  const form=event.target,v=Object.fromEntries(new FormData(form));v.attended=document.getElementById('reschedule-attended').checked;
  const date=document.getElementById('reschedule-date'),r=state.requests.find(r=>r.id===rescheduleId),errorBox=document.getElementById('reschedule-error');
  const validation=v.targetDate===r?.day?'Ngày ngoại lệ phải khác ngày lễ gốc.':v.attended&&v.targetDate>today()?'Không ghi nhận đã đi lễ cho ngày chưa diễn ra.':'';
  if(validation){errorBox.textContent=validation;date.setAttribute('aria-invalid','true');date.focus();return;}
  rememberActor(v.actor);const button=document.getElementById('reschedule-submit');button.disabled=true;form.setAttribute('aria-busy','true');errorBox.textContent='';date.removeAttribute('aria-invalid');
  await queueWrite(async()=>{try{
    const result=await api('reschedule-makeup',{...v,id:rescheduleId});applyServer(result.state);document.getElementById('reschedule-dialog').close();render();
    const message=document.getElementById('requests-message');if(message)message.textContent=result.creditedDate?`Đã ghi X cho lễ gốc ${shortDate(result.creditedDate)}; đi thực tế ${shortDate(result.actualDate)}. Các buổi sau giữ lịch đã xin.`:'Đã lưu ngày ngoại lệ riêng buổi này. Các buổi sau giữ lịch đã xin.';
    const focusTarget=document.querySelector(`[data-reschedule-id="${rescheduleId}"]`)||document.querySelector(`[data-request-history="${rescheduleId}"]`);focusTarget?.focus({preventScroll:true});
  }catch(error){try{applyServer(await api('bootstrap'));}catch{}errorBox.textContent=error.message;errorBox.focus();}
  finally{button.disabled=false;form.removeAttribute('aria-busy');}});
}
async function showRequestHistory(id){
  const r=state.requests.find(r=>r.id===id),ids=new Set(state.requests.filter(x=>x.group_id===r.group_id).map(x=>x.id));
  const labels={created:'Lập đơn',approve:'Duyệt',reject:'Không duyệt',cancel:'Huỷ',completed:'Đã quét',cancelled:'Huỷ do đã có mặt',missed:'Chốt vắng',corrected:'Điều chỉnh',rescheduled:'Dời riêng buổi này',reschedule_failed:'Chưa áp dụng ngoại lệ'};
  const dialog=document.getElementById('request-history-dialog');document.getElementById('request-history-content').textContent='Đang tải lịch sử…';dialog.showModal();
  let events;try{events=await api('request-history?id='+encodeURIComponent(id));}catch(error){document.getElementById('request-history-content').textContent=error.message;return;}
  document.getElementById('request-history-content').innerHTML=`<ol class="request-history">${events.map(e=>`<li><strong>${esc(labels[e.action]||e.action)} · ${esc(e.actor)}</strong><p>${esc(e.reason)}</p><small>${new Intl.DateTimeFormat('vi-VN',{timeZone:tz,dateStyle:'short',timeStyle:'short'}).format(new Date(e.stamp))}</small></li>`).join('')}</ol>`;
}
function openCorrection(code,status,forceReview=false){
  const session=current(),student=students.find(s=>s.id===code);
  if(status==='P'&&mark(session,student)?.status!=='X'&&!session.closed&&!session.lockedClassIds?.includes(student.classId)){openRequest(code);return;}
  if(!forceReview&&status==='X'&&!mark(session,student)&&!session.closed&&!session.lockedClassIds?.includes(student.classId)){recordCode(code,null,true);return;}
  correction={code,status};const form=document.getElementById('correction-form');form.reset();fillActors(document.getElementById('correction-dialog'));
  const early=status==='X'&&session.activity==='early',timeInput=document.getElementById('correction-attended-time');document.getElementById('correction-early-field').hidden=!early;timeInput.disabled=!early;timeInput.required=early;
  document.getElementById('correction-details').textContent=`${student.name} · ${shortDate(session.date)} · ${activities[session.activity]} → ${status||'Chưa điểm danh'}. Thao tác được lưu lịch sử; đơn liên quan sẽ được huỷ để tránh lệch trạng thái.`;
  document.getElementById('correction-error').textContent='';document.getElementById('correction-dialog').showModal();
}
function openScanChoice(result,code,manual,entryId=null){
  if(scanCandidate?.code===code){scanCandidate.phase='choice';if(scanConfirmation.open)scanConfirmation.close();}
  scanChoice={code,manual,entryId};document.getElementById('scan-choice-person').textContent=(result.student.name||[result.student.saintName,result.student.fullName].filter(Boolean).join(' '))+' · '+result.student.className;
  document.getElementById('scan-choice-options').innerHTML='<legend>Chọn một buổi được tính điểm danh</legend>'+result.options.map(o=>`<label class="scan-choice-option"><input type="radio" name="obligationDate" value="${o.date}" required><span>${o.kind==='makeup'?'Lễ bù cho':'Buổi lễ theo lịch'} ${shortDate(o.date)}</span></label>`).join('');
  document.getElementById('scan-choice-dialog').showModal();
}
let closePreviewToken='';
async function previewClose(){
  closePreviewToken='';
  if(state.mode==='cloud'&&offlineAttendance.status().ready){try{await offlineAttendance.reload();}catch(error){toast(error.message);return;}}
  if(offlineAttendance.pendingFor(current()).length){toast('Còn lượt quét trên thiết bị. Đồng bộ hoặc kiểm tra từng lượt trước khi chốt buổi.');return;}
  const dialog=document.getElementById('close-dialog'),button=document.getElementById('confirm-close');button.disabled=true;
  document.getElementById('close-error').textContent='Đang kiểm tra đơn và trạng thái…';document.getElementById('close-preview').innerHTML='';if(!dialog.open)dialog.showModal();
  try{
    await mutationQueue;const result=await api('close-preview',{sessionId:current().id});closePreviewToken=result.previewToken||'';
    document.getElementById('close-preview').innerHTML=flowSteps('review')+`<p><strong>${result.willMarkAbsent} em chưa điểm danh sẽ được ghi vắng. ${result.waitingMakeup} em chờ lễ bù được giữ lại.</strong></p><dl>${[['Có mặt',result.present],['Nghỉ phép',result.permitted],['Chờ lễ bù',result.waitingMakeup],['Sẽ ghi vắng',result.willMarkAbsent],['Lễ bù đến hạn chưa quét',result.makeupsWillMiss]].map(([label,value])=>`<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl>`;
    const roster=(title,rows)=>`<details open><summary>${title} (${rows.length})</summary><ul>${rows.map(p=>`<li>${esc([p.saintName,p.fullName||p.name||p.code].filter(Boolean).join(' '))} · ${esc(p.className||'')} · ${esc(p.id||p.code)}</li>`).join('')||'<li>Không có.</li>'}</ul></details>`;
    document.getElementById('close-preview').insertAdjacentHTML('beforeend',roster('Các em sẽ được ghi vắng',result.willMarkAbsentStudents||[])+roster('Giữ chờ lễ bù',result.waitingMakeupStudents||[])+roster('Đơn chưa duyệt',result.pendingRequests||[])+roster('Quét hộ chờ xử lý',result.pendingScans||[])+(state.mode==='cloud'?'<button type="button" class="button button-secondary" id="refresh-close-preview">Kiểm tra lại</button>':''));
    const pending=result.pendingRequests.length+(result.pendingScans?.length||0);document.getElementById('close-error').textContent=pending?`${pending} mục chưa duyệt. Xử lý trước khi chốt.`:'';
    document.getElementById('review-before-close').hidden=!pending;button.disabled=!!pending;
  }catch(error){document.getElementById('close-error').textContent=error.message;}
}
async function finishMakeups(){
  const button=document.getElementById('confirm-finish-makeup');button.disabled=true;
  await queueWrite(async()=>{try{const result=await api('close-makeup',{date:today(),scope:workingClass||'all'});applyServer(result.state);document.getElementById('finish-makeup-dialog').close();render();document.getElementById('requests-message').textContent=`Đã ghi vắng ${result.count} lễ bù chưa điểm danh.`;}
  catch(error){try{applyServer(await api('bootstrap'));}catch{}document.getElementById('finish-makeup-error').textContent=error.message;}
  finally{button.disabled=false;}});
}

function stopCamera() { scanToken++; clearTimeout(scanTimer); if(cameraStream)cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null;lastDetected={code:'',time:0}; }
async function readQrImage(file) {
  if(!file)return;
  try {
    const bitmap=await createImageBitmap(file);
    const scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));
    const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
    const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
    const pixels=ctx.getImageData(0,0,canvas.width,canvas.height),code=jsQR(pixels.data,canvas.width,canvas.height,{inversionAttempts:'attemptBoth'});
    if(!code)throw new Error('Chưa đọc được QR. Chọn ảnh một thẻ rõ nét, có đủ viền mã.');
    recordCode(code.data, null, false);
  }catch(error){updateFeedback('error','Chưa đọc được ảnh QR',error.message);}
}
async function cameraToggle() {
  if(cameraStream){stopCamera();render();return;}
  const error=document.getElementById('camera-error');error.hidden=true;
  if(!navigator.mediaDevices?.getUserMedia){error.textContent='Trang này chưa mở được camera. Bạn có thể chọn ảnh thẻ hoặc nhập tên/mã của em ở bên dưới.';error.hidden=false;return;}
  const token=++scanToken;const button=document.getElementById('camera-toggle');button.disabled=true;button.textContent='Đang mở camera…';
  try {
    const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}},audio:false});
    if(token!==scanToken||view!=='attendance'||current().closed){stream.getTracks().forEach(t=>t.stop());return;}
    cameraStream=stream;render();
    document.getElementById('scanner-surface')?.scrollIntoView({block:'center',behavior:'instant'});
    const canvas=document.createElement('canvas');const ctx=canvas.getContext('2d',{willReadFrequently:true});
    const tick=()=>{if(!cameraStream||view!=='attendance'||token!==scanToken)return;const video=document.getElementById('camera-video');if(video?.readyState>=2&&!document.querySelector('dialog[open]')){const scale=Math.min(1,640/video.videoWidth);canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);ctx.drawImage(video,0,0,canvas.width,canvas.height);const data=ctx.getImageData(0,0,canvas.width,canvas.height);const result=jsQR(data.data,canvas.width,canvas.height,{inversionAttempts:'dontInvert'});const now=Date.now();if(result){const fresh=result.data!==lastDetected.code;lastDetected={code:result.data,time:now};if(fresh)recordCode(result.data,null,false);}else if(now-lastDetected.time>1200){lastDetected={code:'',time:0};}}scanTimer=setTimeout(tick,250);};tick();
  } catch(e) { if(token!==scanToken||view!=='attendance')return;const target=document.getElementById('camera-error');target.textContent=e.name==='NotAllowedError'?'Camera chưa được cho phép. Hãy cấp quyền camera hoặc dùng ô nhập mã.':'Chưa mở được camera. Kiểm tra thiết bị hoặc dùng ô nhập mã.';target.hidden=false;document.getElementById('camera-toggle').disabled=false;document.getElementById('camera-toggle').innerHTML=`${i('camera')}Bật camera`; }
}

function downloadBlob(bytes,filename,type){const url=URL.createObjectURL(new Blob([bytes],{type}));const link=document.createElement('a');link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
async function exportFiles(all=false) {
  const downloadEpoch=authEpoch;
  const session=current(),choice=all?'all':document.getElementById('export-class').value;
  const classId=choice==='all'?'all':classes.find(c=>c.name===choice).id;
  if(state.mode==='cloud'){if(classId==='all'?!state.isManager:!privacyUI.allowed('privateExport',classId)){toast('Bạn chưa được cấp quyền tải hồ sơ trong phạm vi này.');return;}if(!await privacyUI.confirmExport())return;}
  const form=document.getElementById('export-form'),message=document.getElementById('export-message');
  form.setAttribute('aria-busy','true');form.querySelectorAll('button').forEach(b=>b.disabled=true);message.textContent='Đang lấy file Excel đã lưu…';
  try {
    await mutationQueue;
    const endpoint=state.mode==='cloud'&&classId==='all'?'export-manifest':'export';
    const response=await fetch(`/api/${endpoint}?sessionId=${encodeURIComponent(session.id)}&classId=${encodeURIComponent(classId)}`,{cache:'no-store'});
    const filename=await downloadResponse(response,'DiemDanh.xlsm',downloadBlob,text=>message.textContent=text,()=>downloadEpoch===authEpoch);
    if(downloadEpoch!==authEpoch)return;
    state.downloads.push({filename,scope:choice,date:session.date,timestamp:new Date().toISOString()});save();render();
    const result=document.getElementById('export-message');if(result)result.textContent='Đã tải file lớp. Các macro VBA được giữ nguyên.';
  }catch(error){message.textContent=error.message||'Chưa tải được file. Hãy kết nối lại dịch vụ Excel.';}
  finally{form.removeAttribute('aria-busy');form.querySelectorAll('button').forEach(b=>b.disabled=false);}
}

document.addEventListener('click',event=>{
  const target=event.target.closest('button,a');if(!target)return;
  if(target.matches('.skip-link')){event.preventDefault();document.getElementById('main-content').focus();return;}
  if(target.matches('a[href^="#"]')&&!target.hasAttribute('data-home-scroll')&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey&&event.button===0&&!target.hasAttribute('download')&&(!target.target||target.target==='_self')){
    const destination=target.getAttribute('href').slice(1);
    if(offlineRestored&&destination!=='attendance'){event.preventDefault();toast('Đang mất mạng. Tiếp tục điểm danh trong buổi đã lưu; các trang khác cần kết nối lại.');return;}
    if(['start','home','overview','reports','attendance','students','celebrations','files','requests','teachers','grades','care','management','excel','accounts','administration','notifications','staff','classes'].includes(destination.split('?')[0])){
      event.preventDefault();if(destination!==view)portalTransition.enter(destination);else document.querySelector('.mobile-menu')?.removeAttribute('open');return;
    }
  }
  if(target.id==='reconnect')bootstrap();
  else if(target.id==='sync-offline')syncOfflineScans();
  else if(target.dataset.offlineRetry){
    offlineAttendance.retry(target.dataset.offlineRetry).then(()=>syncOfflineScans()).catch(error=>toast(error.message));
  }
  else if(target.dataset.offlineRemove){
    const entry=offlineAttendance.list().find(e=>e.id===target.dataset.offlineRemove);
    if(entry&&!offlineAttendance.status().syncing&&confirm(`Bỏ lượt chờ của ${entry.name||entry.code} ngày ${shortDate(entry.date)}? Lượt chưa đồng bộ sẽ không được gửi lại.`)){
      offlineAttendance.remove(entry.id).then(()=>render()).catch(error=>toast(error.message));
    }
  }
  else if(target.dataset.easyAction){if(target.dataset.easyAction==='attendance')beginSetup(true);else route(target.dataset.easyAction);}
  else if(target.id==='change-attendance-session')beginSetup();
  else if(target.dataset.copyPresent)copyPresent(target);
  else if(target.hasAttribute('data-print-session-summary'))printSessionSummary(target);
  else if(target.id==='grade-show-all'){const fields=document.getElementById('grade-fields');fields.dataset.entry=fields.dataset.entry==='full'?'single':'full';refreshGradeEditor();}
  else if(target.id==='grade-permitted'){const name=document.getElementById('grade-kind').value,input=document.querySelector(`#grade-fields [name="${name}"]`);input.value=input.value.toUpperCase()==='P'?'':'P';input.dispatchEvent(new Event('input',{bubbles:true}));refreshGradeEditor();}
  else if(target.dataset.editGradeMobile)openGradesDialog(target.dataset.editGradeMobile);
  else if(target.id==='download-class-book'){const name=document.getElementById('book-class').value,identifier=classes.find(c=>c.name===name)?.id;if(identifier)downloadGradeFile(false,identifier);}
  else if(target.hasAttribute('data-confirm-scan'))confirmScannedStudent();
  else if(target.hasAttribute('data-cancel-scan'))cancelScanConfirmation();
  else if(target.hasAttribute('data-dismiss-scan-bubble'))dismissScanBubble();
  else if(target.dataset.requestStudent)openRequest(target.dataset.requestStudent);
  else if(target.hasAttribute('data-new-request'))openRequest();
  else if(target.dataset.reviewId)openReview(target.dataset.reviewId,target.dataset.decision);
  else if(target.dataset.rescheduleId)openReschedule(target.dataset.rescheduleId);
  else if(target.dataset.requestHistory)showRequestHistory(target.dataset.requestHistory);
  else if(target.id==='finish-makeups'){document.getElementById('finish-makeup-error').textContent='';document.getElementById('finish-makeup-dialog').showModal();}
  else if(target.id==='confirm-finish-makeup')finishMakeups();
  else if(target.id==='review-before-close'){document.getElementById('close-dialog').close();requestFilter='pending';route('requests');}
  else if(target.id==='quick-today')beginSetup(true);
  else if(target.hasAttribute('data-new-session'))newSession();
  else if(target.hasAttribute('data-enter-portal')&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey&&event.button===0){event.preventDefault();portalTransition.enter();}
  else if(target.dataset.homeScroll){event.preventDefault();document.getElementById(`home-${target.dataset.homeScroll}`)?.scrollIntoView({behavior:'instant',block:'start'});page.querySelector('.learn-menu')?.removeAttribute('open');}
  else if(target.dataset.homeClass){studentFilter=target.dataset.homeClass;route('students');}
  else if(target.hasAttribute('data-home-try'))route('attendance');
  else if(target.hasAttribute('data-clear-attendance')||target.id==='clear-attendance-filters')clearAttendanceFilters();
  else if(target.dataset.scanMethod)chooseScanMethod(target.dataset.scanMethod);
  else if(target.hasAttribute('data-focus-code')){chooseScanMethod('text');document.getElementById('student-code').scrollIntoView({block:'center',behavior:'instant'});}
  else if(target.dataset.route)route(target.dataset.route);
  else if(target.dataset.openSession)openSession(target.dataset.openSession);
  else if(target.dataset.filterClass){rememberClass(target.dataset.filterClass);render();}
  else if(target.dataset.useStudent){const id=target.dataset.useStudent;openSession(current().id);setTimeout(()=>{const input=document.getElementById('student-code');input.value=id;input.focus();},0);}
  else if(target.dataset.quickAttend)recordCode(target.dataset.quickAttend,null,true);
  else if(target.dataset.chooseStudent){document.getElementById('student-choice-dialog')?.close();recordCode(target.dataset.chooseStudent,null,true);}
  else if(target.dataset.approvePending)approvePending(target.dataset.approvePending);
  else if(target.dataset.rejectPending)rejectPending(target.dataset.rejectPending);
  else if(target.hasAttribute('data-approve-all-pending'))approveAllPending(current());
  else if(target.hasAttribute('data-reject-all-pending'))rejectAllPending(current());
  else if(target.hasAttribute('data-close-dialog'))target.closest('dialog').close();
  else if(target.id==='camera-toggle')cameraToggle();
  else if(target.id==='close-session')previewClose();
  else if(target.id==='confirm-close')closeSession();
  else if(target.id==='refresh-close-preview')previewClose();
  else if(target.id==='export-all')exportFiles(true);
  else if(target.dataset.openProfile)openProfile(target.dataset.openProfile);
  else if(target.dataset.editTeachers)openTeachersDialog(target.dataset.editTeachers);
  else if(target.dataset.changeSem)loadGrades(gradesClassId, parseInt(target.dataset.changeSem, 10));
  else if(target.dataset.editGrade)openGradesDialog(target.dataset.editGrade);
  else if(target.id==='download-grade-file')downloadGradeFile();
  else if(target.id==='toggle-grade-column'||target.hasAttribute('data-toggle-grade-column'))gradeColumn.toggle();
  else if(target.id==='review-grade-column')gradeColumn.review();
  else if(target.id==='accept-grade-column')gradeColumn.accept();
  else if(target.id==='clear-grade-search'){gradeFilters.query='';render();document.getElementById('grade-search')?.focus();}
  else if(target.id==='clear-student-search'){studentTerm='';render();document.getElementById('student-search')?.focus();}
  else if(target.id==='search-all-classes'){rememberClass('all');render();document.getElementById('student-search')?.focus();}
  else if(target.id==='retry-connection')reconnect();
  else if(target.id==='renew-connection')openConnectionLogin();
  else if(target.id==='reload-grades')loadGrades(gradesClassId,gradesSemester);
  else if(target.id==='refresh-grade-table')loadGrades(gradesClassId,gradesSemester);
  else if(target.id==='review-grade-conflict')reviewGradeConflict();
  else if(target.id==='download-pending-grade-file')downloadGradeFile(true);
  else if(target.dataset.openCareDetail)openCareDetail(target.dataset.openCareDetail);
});
document.addEventListener('submit',async event=>{
  if(event.target.id==='grade-column-form'){gradeColumn.submit(event);}
  else if(event.target.id==='attendance-setup-form'){startAttendance(event);}
  else if(event.target.id==='request-form'){event.preventDefault();submitRequest(event);}
  else if(event.target.id==='review-form'){event.preventDefault();submitReview(event);}
  else if(event.target.id==='reschedule-form'){event.preventDefault();submitReschedule(event);}
  else if(event.target.id==='correction-form'){event.preventDefault();const v=Object.fromEntries(new FormData(event.target));rememberActor(v.actor);if(scanCandidate?.phase==='choice'&&scanCandidate.code===correction.code){scanCandidate.phase='saving';renderScanConfirmation();}changeMark(correction.code,correction.status,v.actor,v.reason,v.attendedTime);}
  else if(event.target.id==='scan-choice-form'){
    event.preventDefault();const v=new FormData(event.target),choice=scanChoice;document.getElementById('scan-choice-dialog').close();
    if(scanCandidate?.phase==='choice'&&scanCandidate.code===choice.code){scanCandidate.phase='saving';renderScanConfirmation();}
    if(choice.entryId)offlineAttendance.choose(choice.entryId,v.get('obligationDate')).then(()=>syncOfflineScans()).catch(error=>toast(error.message));
    else commitCode(choice.code,v.get('obligationDate'),choice.manual);
  }
  else if(event.target.id==='session-form'){
    event.preventDefault();const values=Object.fromEntries(new FormData(event.target)),button=event.target.querySelector('button[type=submit]');button.disabled=true;
    try{const session=await api('sessions',values);applyServer(await api('bootstrap'));document.getElementById('session-dialog').close();openSession(session.id);}
    catch(error){document.getElementById('session-error').textContent=error.message;}
    finally{button.disabled=false;}
  }
  else if(event.target.id==='code-form'){event.preventDefault();handleManualAttendance(new FormData(event.target).get('code'));}
  else if(event.target.id==='export-form'){event.preventDefault();exportFiles();}
  else if(event.target.id==='profile-form'){submitProfile(event);}
  else if(event.target.id==='teachers-form'){submitTeachers(event);}
  else if(event.target.id==='grades-form'){submitGrades(event);}
  else if(event.target.id==='grade-reconcile-form'){reconcileGrades(event);}
});
document.addEventListener('change',event=>{
  if(event.target.id==='workspace-class'){chooseWorkingClass(event.target.value);}
  else if(event.target.id==='book-class'){rememberClass(event.target.value);render();}
  else if(event.target.id==='grade-kind'){refreshGradeEditor();}
  else if(event.target.id==='grade-column-kind'){gradeColumn.changeKind(event.target.value);}
  else if(event.target.id==='grade-mobile-student'){mobileGradeCode=event.target.value;document.querySelectorAll('[data-grade-card]').forEach(card=>card.hidden=card.dataset.gradeCard!==mobileGradeCode);document.getElementById('grade-mobile-empty').hidden=!!mobileGradeCode;}
  else if(event.target.id==='qr-image'){const file=event.target.files[0];event.target.value='';readQrImage(file);}
  else if(event.target.dataset.stateId){openCorrection(event.target.dataset.stateId,event.target.value);}
  else if(event.target.closest('#request-form'))requestFormHelp();
  else if(event.target.id==='request-filter'){
    requestFilter=event.target.value;refreshRequests();
    const params=new URLSearchParams({filter:requestFilter});if(workingClass)params.set('class',workingClass);
    history.replaceState(null,'','#requests?'+params);
  }
  else if(event.target.closest('#session-form') && event.target.matches('select'))calendarHelp();
  else if(event.target.id==='attendance-class'){attendanceClass=event.target.value;refreshAttendanceRows();}
  else if(event.target.id==='attendance-status'){attendanceStatus=event.target.value;refreshAttendanceRows();}
  else if(event.target.id==='student-filter'){rememberClass(event.target.value);render();}
  else if(event.target.id==='export-session'){state.active=event.target.value;save();render();}
  else if(event.target.id==='export-class'){exportClass=event.target.value;refreshExportPlan();}
  else if(event.target.id==='quick-date'||event.target.id==='quick-activity'||event.target.id==='quick-scope'){
    const d=document.getElementById('quick-date')?.value||current().date;
    const a=document.getElementById('quick-activity')?.value||current().activity;
    const s=document.getElementById('quick-scope')?.value||current().scope;
    attendanceDraft={date:d,activity:a,scope:s};attendanceSetupError='';if(event.target.id==='quick-scope'){rememberClass(s);workContext();}
  }
  else if(event.target.id==='grades-class-select'){loadGrades(event.target.value, gradesSemester);}
  else if(event.target.id==='grade-assessment'||event.target.id==='grade-sort'){gradeFilters[event.target.id==='grade-sort'?'sort':'assessment']=event.target.value;render();}
  else if(event.target.id==='care-class-filter'){rememberClass(event.target.value);render();}
  else if(event.target.id==='care-month-filter'){careMonthFilter=event.target.value;render();}
});
document.addEventListener('input',event=>{
  if(event.target.matches('.grade-cell-input,#correction-attended-time')&&event.target.validity.valid){event.target.removeAttribute('aria-invalid');event.target.closest('label')?.querySelector('.grade-field-error')?.remove();if(event.target.matches('.grade-cell-input'))event.target.setAttribute('aria-describedby','grades-score-help grades-dialog-error');}
  if(event.target.id==='request-search'){requestTerm=event.target.value;refreshRequests();}
  if(event.target.id==='request-code')requestFormHelp();
  if(event.target.id==='attendance-search'){attendanceTerm=event.target.value;refreshAttendanceRows();}
  if(event.target.id==='grade-search'){gradeFilters.query=event.target.value;render();}
  if(event.target.id==='student-search'){studentTerm=event.target.value;filterStudentRows();}
  if(event.target.hasAttribute('data-column-code'))gradeColumn.input(event.target);
  if(event.target.id==='care-search-input'){careSearchTerm=event.target.value;render();}
});
document.addEventListener('invalid',event=>{
  if(event.target.hasAttribute('data-column-code')){
    event.target.setAttribute('aria-invalid','true');const field=event.target.closest('label');let error=field.querySelector('.grade-field-error');
    if(!error){error=document.createElement('small');error.className='grade-field-error';error.id='column-error-'+event.target.dataset.columnCode;field.append(error);}
    error.textContent='Nhập 0–10, P hoặc để trống.';event.target.setAttribute('aria-describedby','grade-column-help '+error.id+' grade-column-message');
    document.getElementById('grade-column-message').textContent='Kiểm tra ô điểm đang được chọn; bản nháp vẫn được giữ.';
  }
  if(event.target.matches('.grade-cell-input')){
    event.target.setAttribute('aria-invalid','true');
    if(event.target.closest('[hidden]')){document.getElementById('grade-fields').dataset.entry='full';refreshGradeEditor();}
    const field=event.target.closest('label');let error=field.querySelector('.grade-field-error');
    if(!error){error=document.createElement('small');error.className='grade-field-error';error.id='grade-error-'+event.target.name;field.append(error);}
    error.textContent='Nhập 0–10, P hoặc để trống.';event.target.setAttribute('aria-describedby','grades-score-help '+error.id+' grades-dialog-error');
    document.getElementById('grades-dialog-error').textContent='Kiểm tra ô điểm đang được chọn; nội dung của bạn vẫn được giữ.';
  }
  if(event.target.id==='correction-attended-time'){event.target.setAttribute('aria-invalid','true');document.getElementById('correction-error').textContent='Nhập giờ đi lễ thực tế từ 06:00 đến 06:20.';}
},true);
const privacyUI=createPrivacyUI({api,esc,state:()=>state,classes:()=>classes,applyServer,render,toast});
const reportsUI=createReportsUI({api,esc,state:()=>state});
const auth=createAuthUI({api,esc,page,state:()=>state,classes:()=>classes,render,toast,queueWrite,applyServer,onAccountsChanged:()=>management.clear(),pending:()=>pendingWrites,restoreOffline:()=>offlineAttendance.restore(),
  onClear:()=>{
    offlineRestored=false;offlineAttendance.clearSession();privacyUI.clear();reportsUI.clear();profileLoadId++;
    portalTransition.cancel();
    authEpoch++;staffCalendar.clear();parity.clear();development.clear();management.clear();enrollment.clear();
    connected=false;stopCamera();clearTimeout(reconnectTimer);reconnectTimer=null;connectionIssue=null;
    classes=[];students=[];classNames=[];state={sessions:[],marks:{},requests:[],requestEvents:[],downloads:[],accounts:[],active:null,isManager:false,pendingScans:[]};
    currentGradesData=null;gradesLoadToken++;gradesLoading=false;gradesClassId='';uncertainGradeSave=null;gradeColumn.clear();
    scanCandidate=null;scanConfirmation.replaceChildren();scanFeedback=null;scanBubble.hidden=true;workingClass='';studentTerm='';attendanceTerm='';requestTerm='';
    document.querySelectorAll('dialog[open]').forEach(d=>d.close());
    for(const id of ['profile-dialog-content','grade-fields','care-dialog-content','request-history-content','feature-fields','parity-fields','parity-preview','request-student-options','request-code-options'])document.getElementById(id)?.replaceChildren();
    document.getElementById('connection-banner')?.remove();
  },
  onReady:async (user,{welcome=false,offline=null}={})=>{
    offlineRestored=!!offline;
    await offlineAttendance.activate(user,offline?{expires:offline.expiresAt,prepared:true}:{});
    storageKey='gx-xuan-hoa-live-preferences-v1:'+user.id;
    try{preferences=JSON.parse(localStorage.getItem(storageKey))||{};}catch{preferences={};}
    preferences.actor=user.displayName;workingClass=preferences.className||'';
    if(['camera','text'].includes(preferences.scanMethod))scanMethod=preferences.scanMethod;
    if(offline){
      applyServer(offline.snapshot);state.active=preferences.active||state.active;
      attendanceStage=current()?.closed?'finished':'scan';
      connectionLost(Object.assign(new Error('Mất kết nối mạng.'),{network:true}));
      history.replaceState(null,'','#attendance');decorate();routeFromHash();return;
    }
    if(welcome){history.replaceState(null,'','#home');page.dispatchEvent(new Event('parish:welcome'));}
    await bootstrap();syncOfflineScans();
  }
});
const portalTransition=createPortalTransition({
  canEnter:destination=>connected&&view!==destination&&document.body.dataset.auth==='in'&&(!offlineRestored||destination==='attendance')&&(state.isManager||!adminPages.includes(destination.split('?')[0])),
  mode:destination=>view==='home'||destination==='home'?'portal':'navigation',
  navigate:destination=>{history.pushState(null,'','#'+destination);routeFromHash();},
  onArrive:destination=>{if(view===destination.split('?')[0]){const heading=page.querySelector('h1')||page;heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});}}
});
window.addEventListener('hashchange',routeFromHash);
window.addEventListener('pagehide',stopCamera);
document.addEventListener('visibilitychange',()=>{if(document.hidden&&cameraStream){stopCamera();if(view==='attendance')render();}});
document.body.insertAdjacentHTML('beforeend',requestDialogs()+development.dialogs()+parity.dialogs());parity.bind();
let dialogOpener=null;
document.addEventListener('click',event=>{
  const target=event.target.closest('button,a');
  if(target&&!target.closest('dialog')&&target.matches('[data-open-profile],[data-edit-grade],[data-edit-grade-mobile],[data-edit-teachers],[data-account-edit],[data-account-assign],[data-new-request],[data-request-student],[data-review-id],[data-reschedule-id],#close-session'))dialogOpener=target;
},true);
document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('close',()=>{
  if(dialog.id==='scan-confirmation-dialog')return;
  if(['scan-choice-dialog','correction-dialog'].includes(dialog.id)&&scanCandidate?.phase==='choice')cancelScanConfirmation();
  if(dialog.id==='parity-dialog'||dialog.id==='feature-dialog'||dialog.id==='staff-profile-dialog'||dialog.id==='enrollment-dialog')return;
  if(dialogOpener?.isConnected){dialogOpener.focus({preventScroll:true});return;}
  const attribute=dialogOpener?.getAttributeNames().find(n=>n.startsWith('data-'));
  if(attribute)(document.querySelector(`[${attribute}="${CSS.escape(dialogOpener.getAttribute(attribute))}"]`)||(['data-account-edit','data-account-assign'].includes(attribute)?document.getElementById('account-search'):null))?.focus({preventScroll:true});
  else if(dialogOpener?.id==='close-session')document.querySelector('[data-route=files]')?.focus({preventScroll:true});
}));
let motion=createMotionController(document.body);
let welcomeScene=createWelcomeSceneController(page);
window.addEventListener('pagehide',()=>welcomeScene.destroy());
window.addEventListener('pageshow',event=>{if(event.persisted)welcomeScene=createWelcomeSceneController(page);});
window.addEventListener('pagehide',()=>motion.destroy());
window.addEventListener('pageshow',event=>{if(event.persisted)motion=createMotionController(document.body);});
decorate();auth.init();
if('serviceWorker' in navigator)navigator.serviceWorker.register('/service-worker.js',{updateViaCache:'none'}).catch(()=>{});
setInterval(refreshServer,15000);
window.addEventListener('online',()=>reconnect());
window.addEventListener('offline',()=>connectionLost(new Error('Mất kết nối mạng.')));
document.addEventListener('keydown',event=>{
  if(event.key==='Enter'&&event.target.hasAttribute('data-column-code')){
    event.preventDefault();const inputs=[...document.querySelectorAll('[data-column-code]')];const next=inputs[inputs.indexOf(event.target)+1];
    (next||document.getElementById('save-grade-column'))?.focus();
  }
});
