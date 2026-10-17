// Reveal newly visible landing sections once. Refreshes and keyboard focus show
// the final readable state; no scroll handlers or persistent rendering loop.
export function createWelcomeReveals(root,reduced){
  const records=new Map(),seen=new Set();
  const selector='.education-home :is(.learn-facts,.hero-progress,.learn-section-heading,.course-card,.journey-item,.enrollment-card)';
  function remove(element,r){r.animation.cancel();observer.unobserve(element);records.delete(element);}
  function finish(element,r){seen.add(r.key);remove(element,r);}
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries){
      const r=records.get(entry.target);if(!r)continue;
      r.visible=entry.isIntersecting;
      if(r.visible&&!document.hidden){seen.add(r.key);r.animation.play();}
      else r.animation.pause();
    }
  },{threshold:.08,rootMargin:'0px 0px -20px 0px'});
  function sync(){
    for(const [element,r] of records)if(!root.contains(element))remove(element,r);
    if(reduced.matches||!Element.prototype.animate)return;
    root.querySelectorAll(selector).forEach((element,n)=>{
      const key=`landing-section-${n}`;
      if(records.has(element)||seen.has(key))return;
      const animation=element.animate([
        {opacity:0,transform:'translateY(14px)'},{opacity:1,transform:'translateY(0)'}
      ],{duration:480,easing:'ease-out',fill:'backwards'});
      animation.id=`welcome-reveal-${n}`;animation.pause();animation.currentTime=0;
      const r={key,animation,visible:false};records.set(element,r);observer.observe(element);
      animation.finished.then(()=>{if(records.get(element)===r)finish(element,r);}).catch(()=>{});
    });
  }
  function visibility(){
    for(const [element,r] of records){
      if(reduced.matches)finish(element,r);
      else if(!document.hidden&&r.visible)r.animation.play();
      else r.animation.pause();
    }
  }
  const focus=event=>{
    for(const [element,r] of records)if(element.contains(event.target))finish(element,r);
  };
  root.addEventListener('focusin',focus);
  return {sync,visibility,reset(){for(const [element,r] of records)finish(element,r);seen.clear();sync();},
    destroy(){observer.disconnect();root.removeEventListener('focusin',focus);for(const r of records.values())r.animation.cancel();records.clear();}};
}
