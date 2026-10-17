const kinds={loading:'loading-cat',learning:'learning-book',cat:'playing-cat',success:'success-confetti'};
let playerPromise;
const assets=new Map();

export function animationStage(kind,className=''){
  const asset=kinds[kind];
  if(!asset)throw new Error('Unknown animation.');
  return `<div class="lottie-stage ${className}" data-lottie="${kind}" aria-hidden="true"><img class="lottie-poster" src="assets/animations/${asset}.svg" alt="" width="360" height="260"><div class="lottie-player"></div></div>`;
}
export function loadingPanel(title='Đang mở sổ điểm danh',description='Đang đọc danh sách và lịch của lớp…'){
  return `<section class="connection-card card loading-panel" role="status" aria-live="polite" aria-busy="true">${animationStage('loading')}<h2>${title}</h2><p>${description}</p></section>`;
}

export function busyFeedback(target,message){
  target.replaceChildren();
  target.insertAdjacentHTML('beforeend',animationStage('loading','inline-loader'));
  target.append(document.createTextNode(message));
}

// Only explicit successful operations mount this one-shot effect. A later render
// cannot replay it, and opening an already closed session does not celebrate.
export function celebrateSession(root){
  if(document.body.dataset.motion==='paused'||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const target=root.querySelector('.session-complete');
  if(target)target.insertAdjacentHTML('afterbegin',animationStage('success','session-confetti'));
}

function loadPlayer(){
  return playerPromise ||= import(new URL('assets/vendor/lottie-light.min.js',document.baseURI).href)
    .then(module=>module.default).catch(error=>{playerPromise=null;throw error;});
}
function loadAsset(kind){
  if(!assets.has(kind))assets.set(kind,fetch('assets/animations/'+kinds[kind]+'.json').then(r=>{
    if(!r.ok)throw new Error('Animation unavailable.');return r.json();
  }).catch(error=>{assets.delete(kind);throw error;}));
  return assets.get(kind);
}

export function createMotionController(root){
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),records=new Map();
  let serial=0,scheduled=false,disposed=false;
  const blocked=r=>reduced.matches||document.hidden||!r.visible;
  function controls(){
    root.dataset.motion=reduced.matches?'paused':'enabled';
  }
  function still(r,frame){r.player.resetSegments(true);r.player.goToAndStop(frame,true);}
  function playback(r){
    if(!r.ready)return;
    if(r.completed)return;
    if(blocked(r)){
      if(reduced.matches)still(r,0);else r.player.pause();
      r.host.dataset.playback='paused';return;
    }
    r.player.play();r.host.dataset.playback='playing';
  }
  const intersection=new IntersectionObserver(entries=>{
    for(const entry of entries){const r=records.get(entry.target);if(r){r.visible=entry.isIntersecting;playback(r);}}
  },{threshold:0});
  async function mount(host){
    const kind=host.dataset.lottie;
    if(!kinds[kind])return;
    const r={host,kind,player:null,ready:false,visible:false};
    records.set(host,r);intersection.observe(host);
    try{
      const [lottie,data]=await Promise.all([loadPlayer(),loadAsset(kind)]);
      if(disposed||records.get(host)!==r||!host.isConnected)return;
      r.player=lottie.loadAnimation({container:host.querySelector('.lottie-player'),renderer:'svg',autoplay:false,
        loop:kind!=='success',animationData:structuredClone(data),name:kind+'-'+(++serial),rendererSettings:{progressiveLoad:false,hideOnTransparent:true}});
      r.player.addEventListener('DOMLoaded',()=>{
        if(records.get(host)!==r)return;
        r.ready=true;host.dataset.lottieReady='true';
        playback(r);
      });
      r.player.addEventListener('complete',()=>{
        if(kind==='success'){r.completed=true;host.dataset.playback='complete';host.hidden=true;return;}
      });
      r.player.addEventListener('data_failed',()=>{host.dataset.lottieReady='false';host.dataset.playback='fallback';});
    }catch{host.dataset.playback='fallback';}
  }
  function sync(){
    scheduled=false;if(disposed)return;
    for(const [host,r] of records)if(!host.isConnected||!root.contains(host)){
      records.delete(host);intersection.unobserve(host);r.ready=false;r.player?.destroy();
    }
    root.querySelectorAll('[data-lottie]').forEach(host=>{if(!records.has(host))mount(host);});controls();
  }
  const mutations=new MutationObserver(()=>{if(!scheduled){scheduled=true;queueMicrotask(sync);}});
  mutations.observe(root,{childList:true,subtree:true});
  const visibility=()=>{for(const r of records.values())playback(r);controls();};
  document.addEventListener('visibilitychange',visibility);
  reduced.addEventListener('change',visibility);
  sync();
  return {sync,destroy(){
    disposed=true;mutations.disconnect();intersection.disconnect();document.removeEventListener('visibilitychange',visibility);reduced.removeEventListener('change',visibility);
    for(const r of records.values())r.player?.destroy();records.clear();
  }};
}
