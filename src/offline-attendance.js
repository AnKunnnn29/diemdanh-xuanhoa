// Durable, account-scoped outbox. A queued scan never changes confirmed marks.
const DB_NAME='xuanhoa-attendance-v1';
const SESSION_TTL=12*60*60*1000;
let database;
function openDatabase(){
  if(!globalThis.indexedDB)return Promise.reject(new Error('Thiết bị chưa hỗ trợ lưu lượt chờ. Điểm danh trực tuyến vẫn dùng được.'));
  if(database)return database;
  database=new Promise((resolve,reject)=>{
    const request=indexedDB.open(DB_NAME,1);
    request.onupgradeneeded=()=>{
      const entries=request.result.createObjectStore('entries',{keyPath:'id'});
      entries.createIndex('dedupe','dedupe',{unique:true});entries.createIndex('owner','owner');
      request.result.createObjectStore('meta',{keyPath:'key'});
    };
    request.onsuccess=()=>{request.result.onversionchange=()=>{request.result.close();database=null;};resolve(request.result);};
    request.onerror=()=>{database=null;reject(new Error('Chưa lưu được trên thiết bị. Kiểm tra dung lượng hoặc chế độ riêng tư.'));};
  });
  return database;
}
async function transact(store,mode,action){
  const db=await openDatabase();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(store,mode);let value;
    const request=action(tx.objectStore(store));
    if(request)request.onsuccess=()=>{value=request.result;};
    tx.oncomplete=()=>resolve(value);
    tx.onabort=tx.onerror=()=>reject(new Error('Chưa lưu được trên thiết bị. Lượt này chưa được giữ; kiểm tra dung lượng rồi thử lại.'));
  });
}
export function attendanceSnapshot(data){
  const pick=(row,fields)=>Object.fromEntries(fields.filter(k=>k in row).map(k=>[k,row[k]]));
  const students=data.students.map(s=>Object.fromEntries(['id','name','saintName','fullName','classId','className','enrolledFrom'].map(k=>[k,s[k]??''])));
  return {year:data.year,yearId:data.yearId,mode:data.mode,user:data.user,classes:data.classes.map(c=>pick(c,['id','name','calendar','archived','count'])),students,
    sessions:data.sessions,marks:Object.fromEntries(Object.entries(data.marks).map(([k,v])=>[k,pick(v,['status','timestamp'])])),
    requests:data.requests.map(r=>pick(r,['id','code','kind','status','day','activity','target_day','exception_day','actual_day'])),
    studentStatuses:(data.studentStatuses||[]).map(s=>pick(s,['code','status','effective_day'])),
    isManager:data.isManager,gradeMode:data.gradeMode,pendingScans:[]};
}
export function createOfflineAttendance({onChange=()=>{}}={}){
  let owner='',expiresAt=0,entries=[],ready=false,error='',syncing=false;
  const changed=()=>onChange();
  const list=()=>entries.slice();
  async function reload(){
    const who=owner;
    const rows=who?await transact('entries','readonly',store=>store.index('owner').getAll(who)):[];
    if(owner===who){entries=rows.sort((a,b)=>a.capturedAt.localeCompare(b.capturedAt));changed();}
    return list();
  }
  async function activate(user,{expires=Date.now()+SESSION_TTL,prepared=false}={}){
    owner=user.id;expiresAt=expires;ready=prepared;error='';
    try{await reload();}catch(e){error=e.message;changed();}
  }
  async function remember(data){
    if(!owner||data.user.id!==owner||data.mode!=='cloud'||!data.yearId)return;
    const who=owner;
    try{
      await transact('meta','readwrite',store=>owner===who?store.put({key:'session',user:data.user,snapshot:attendanceSnapshot(data),expiresAt}):null);
      if(owner===who){ready=true;error='';changed();}
    }catch(e){if(owner===who){ready=false;error=e.message;changed();}}
  }
  async function restore(){
    try{
      const cached=await transact('meta','readonly',store=>store.get('session'));
      if(!cached||cached.expiresAt<=Date.now()||cached.user.mustChangePassword)return null;
      return cached;
    }catch{return null;}
  }
  async function clearSession(){
    owner='';entries=[];ready=false;expiresAt=0;changed();
    try{await transact('meta','readwrite',store=>store.delete('session'));}catch{}
  }
  async function enqueue({yearId,session,student,manual,obligationDate=null,capturedAt=new Date().toISOString()}){
    if(!owner||Date.now()>expiresAt)throw new Error('Cần kết nối và đăng nhập lại trước khi giữ thêm lượt điểm danh.');
    const who=owner,dedupe=JSON.stringify([owner,yearId,session.id,student.id]);
    const db=await openDatabase();let entry,duplicate=false;
    await new Promise((resolve,reject)=>{
      const tx=db.transaction('entries','readwrite'),store=tx.objectStore('entries'),request=store.index('dedupe').get(dedupe);
      request.onsuccess=()=>{
        entry=request.result;duplicate=!!entry;
        if(entry){
          if(obligationDate&&entry.obligationDate!==obligationDate){entry={...entry,obligationDate,status:'pending',error:''};store.put(entry);}
        }else{
          entry={id:crypto.randomUUID(),owner:who,dedupe,yearId,sessionId:session.id,date:session.date,activity:session.activity,scope:session.scope,
            code:student.id,name:student.name,className:student.className,manual,obligationDate,capturedAt,status:'pending',error:''};
          store.add(entry);
        }
      };
      tx.oncomplete=resolve;tx.onabort=tx.onerror=()=>reject(new Error('Chưa lưu được lượt chờ trên thiết bị. Giữ mã thẻ và thử lại.'));
    });
    if(owner===who)await reload();
    return {entry,duplicate};
  }
  async function remove(id){
    const entry=entries.find(e=>e.id===id);if(!entry||entry.owner!==owner)return;
    await transact('entries','readwrite',store=>store.delete(id));await reload();
  }
  async function retry(id){
    const entry=entries.find(e=>e.id===id);if(!entry||entry.owner!==owner)return;
    await transact('entries','readwrite',store=>store.put({...entry,status:'pending',error:''}));await reload();
  }
  async function choose(id,obligationDate){
    const entry=entries.find(e=>e.id===id);if(!entry||entry.owner!==owner)return;
    await transact('entries','readwrite',store=>store.put({...entry,obligationDate,status:'pending',error:''}));await reload();
  }
  async function sync(send,{onResult=()=>{},onChoice=()=>{},isCurrent=()=>true}={}){
    if(syncing||!owner)return;
    const who=owner;syncing=true;changed();
    try{
      await reload();
      while(owner===who&&isCurrent()){
        const entry=entries.find(e=>e.status==='pending');if(!entry)break;
        try{
          const result=await send(entry);
          if(owner!==who||!isCurrent())break;
          if(result.choiceRequired){
            await transact('entries','readwrite',store=>store.put({...entry,status:'blocked',error:'Chọn ngày cần tính cho lượt lễ bù này.'}));
            await reload();onChoice(result,entry);break;
          }
          // Delete only after a positive server acknowledgement, never on timeout.
          await remove(entry.id);onResult(result,entry);
        }catch(e){
          if(owner!==who||!isCurrent())break;
          if(e.network||e.uncertain||!e.status||e.status===401||e.status>=500||e.status===429)break;
          await transact('entries','readwrite',store=>store.put({...entry,status:'blocked',error:e.message,errorCode:e.code||''}));
          await reload();
        }
      }
    }catch(e){error=e.message;changed();}
    finally{syncing=false;changed();}
  }
  return {activate,remember,restore,clearSession,enqueue,reload,list,remove,retry,choose,sync,
    status:()=>({owner,ready,error,syncing,expiresAt}),
    pendingFor:session=>entries.filter(e=>e.date===session.date&&e.activity===session.activity&&(session.scope==='all'||e.className===session.scope)),
    find:(session,code)=>entries.find(e=>e.sessionId===session.id&&e.code===code)};
}

export function offlinePanel({entries,ready,error,syncing,online,esc,shortDate}){
  const blocked=entries.some(e=>e.status==='blocked');
  return `<section class="card offline-attendance" aria-labelledby="offline-title"><div class="card-body">
    <div class="offline-heading"><div><h2 id="offline-title">Điểm danh khi mất mạng</h2><p class="field-help">${error?esc(error):ready?'Danh sách và buổi đã được lưu trên thiết bị.':'Đang chuẩn bị danh sách trên thiết bị…'}</p></div>
    ${entries.length?`<button type="button" class="button button-secondary" id="sync-offline" ${!online||syncing?'disabled':''}>${syncing?'Đang đồng bộ…':'Đồng bộ lượt chờ'}</button>`:''}</div>
    <p id="offline-count" role="status" aria-live="polite" aria-atomic="true">${entries.length?`${entries.length} lượt trên thiết bị đang chờ đồng bộ${blocked?' · Có lượt cần kiểm tra':''}.`:'Không có lượt chờ trên thiết bị.'}</p>
    ${entries.length?`<details class="offline-queue-details" ${blocked?'open':''}><summary>Xem ${entries.length} lượt chờ</summary><ul class="offline-queue">${entries.map(e=>`<li><div><strong>${esc(e.name||e.code)}</strong><small>${esc(e.className)} · ${shortDate(e.date)} · ${esc({mass:'Thánh lễ',lesson:'Giáo lý',early:'Lễ sớm'}[e.activity])} · ${esc(new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit'}).format(new Date(e.capturedAt)))}</small><p>${e.status==='blocked'?esc(e.error):'Đã giữ trên thiết bị · Chờ máy chủ xác nhận'}</p></div><div class="feature-actions">${e.status==='blocked'?`<button type="button" class="button button-secondary" data-offline-retry="${esc(e.id)}" ${!online||syncing?'disabled':''}>Thử lại</button>`:''}<button type="button" class="button button-text" data-offline-remove="${esc(e.id)}" ${syncing?'disabled':''}>Bỏ lượt chờ</button></div></li>`).join('')}</ul></details>`:''}
    <details class="offline-help"><summary>Cách dùng khi mất mạng</summary><p class="field-help">Mở buổi hôm nay khi có mạng trước khi quét. Lượt chờ chưa được tính có mặt; cần đồng bộ xong trước khi chốt buổi. Lễ sớm gửi lại ngoài khung giờ cần Admin xác nhận.</p></details>
  </div></section>`;
}
