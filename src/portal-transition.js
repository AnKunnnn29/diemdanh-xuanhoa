// The welcome scene and regular route changes share one cancellable controller.
// Named snapshots keep everyday navigation anchored while the page slides.
export function createPortalTransition({canEnter,navigate,onArrive,mode=()=>'portal'}){
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const root=document.documentElement;
  let active=null,committing=false;
  function commit(record){
    if(active!==record||!canEnter(record.destination))return;
    committing=true;
    try{navigate(record.destination);record.entered=true;}finally{committing=false;}
  }
  function cancel(){
    const record=active;active=null;
    record?.transition?.skipTransition();
    record?.effects.forEach(effect=>effect.cancel());
    root.removeAttribute('data-portal-transition');
  }
  async function fallback(record){
    const hero=document.querySelector('.education-home>.welcome-hero')||document.getElementById('main-content');
    if(hero?.animate&&!reduced.matches){
      const exit=hero.animate([{transform:'translateY(0)',opacity:1},{transform:record.kind==='navigation'?'translateY(-24px)':'translateY(-8%)',opacity:0}],{duration:220,easing:'ease-in',fill:'forwards'});
      record.effects.push(exit);await exit.finished.catch(()=>{});
    }
    commit(record);
    if(active!==record||!record.entered)return;
    const workspace=document.querySelector(record.kind==='navigation'?'#main-content':'.workspace');
    if(workspace?.animate&&!reduced.matches){
      const entrance=workspace.animate([{transform:'translateY(32px)',opacity:0},{transform:'translateY(0)',opacity:1}],{duration:320,easing:'cubic-bezier(.2,.7,.2,1)'});
      record.effects.push(entrance);await entrance.finished.catch(()=>{});
    }
  }
  function enter(destination='start'){
    if(active?.destination===destination||!canEnter(destination))return;
    cancel();
    const record={effects:[],transition:null,entered:false,destination,kind:mode(destination)};active=record;
    document.querySelector('.mobile-menu')?.removeAttribute('open');
    if(reduced.matches){commit(record);active=null;if(record.entered)onArrive(destination);return;}
    root.setAttribute('data-portal-transition',record.kind);
    (async()=>{
      try{
        if(typeof document.startViewTransition==='function'){
          record.transition=document.startViewTransition(()=>commit(record));
          record.transition.ready.catch(()=>{});
          record.transition.updateCallbackDone.catch(()=>{});
          await record.transition.finished;
        }else await fallback(record);
      }catch{
        // A skipped/unsupported snapshot must never prevent entering the portal.
        commit(record);
      }finally{
        record.effects.forEach(effect=>effect.cancel());
        if(active===record){active=null;root.removeAttribute('data-portal-transition');if(record.entered)onArrive(destination);}
      }
    })();
  }
  const skip=()=>active?.transition?.skipTransition();
  const key=event=>{if(event.key==='Escape')skip();};
  const preference=()=>{if(reduced.matches){skip();active?.effects.forEach(effect=>effect.finish());}};
  window.addEventListener('resize',skip);window.addEventListener('pagehide',cancel);
  document.addEventListener('keydown',key);reduced.addEventListener('change',preference);
  return {enter,cancel,get committing(){return committing;},destroy(){cancel();window.removeEventListener('resize',skip);window.removeEventListener('pagehide',cancel);document.removeEventListener('keydown',key);reduced.removeEventListener('change',preference);}};
}
