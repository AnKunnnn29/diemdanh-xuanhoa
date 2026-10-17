import sheets from '../design/mascot/glv-sequences-v5.json';
let rigId=0;
let atlasReady;
const e=n=>'expression'+n,c=n=>'cover'+n;
const front=e(2);
const expressionIndex=name=>name.startsWith('expression')?Number(name.slice(10)):null;
const coverIndex=name=>name.startsWith('cover')?Number(name.slice(5)):null;
const range=(from,to)=>Array.from({length:Math.abs(to-from)+1},(_,n)=>from+Math.sign(to-from)*n);
function artworkReady(){
  if(!atlasReady)atlasReady=Promise.all(Object.values(sheets).filter(sheet=>sheet.file).map(sheet=>{const image=new Image();image.src='assets/animations/'+sheet.file;return image.decode();})).catch(error=>{atlasReady=null;throw error;});
  return atlasReady;
}

// Registration changes SVG display coordinates only. Original transparent PNG
// pixels stay untouched; each frame is a complete, connected illustration.
export function glvMascotMarkup(){
  const prefix='glv-sequence-'+(++rigId);
  const definitions=[],layers=[];
  for(const [kind,sheet] of Object.entries(sheets)){
    if(!sheet.file)continue;
    const atlas=prefix+'-'+kind;
    definitions.push(`<image id="${atlas}" href="assets/animations/${sheet.file}" width="${sheet.width}" height="${sheet.height}"/>`);
    for(const frame of sheet.frames){
      const [x,y]=frame.rect;
      const bands=frame.bands.map((band,n)=>{
        const clip=prefix+'-'+frame.name+'-'+n,[cx,cy,cw,ch]=band.clip;
        definitions.push(`<clipPath id="${clip}"><rect x="${cx}" y="${cy}" width="${cw}" height="${ch}"/></clipPath>`);
        return `<g data-glv-band="${n}" transform="translate(${band.x} ${band.y}) scale(${band.scaleX} ${band.scaleY}) translate(${-x} ${-y})"><use href="#${atlas}" clip-path="url(#${clip})"/></g>`;
      }).join('');
      layers.push(`<g data-glv-frame="${frame.name}" style="opacity:${frame.name===front?1:0}">${bands}</g>`);
    }
  }
  return `<svg class="glv-character" viewBox="0 0 480 512" width="480" height="512" aria-hidden="true" focusable="false"><defs>${definitions.join('')}</defs><g data-glv-body>${layers.join('')}</g></svg>`;
}

export function createGlvMascot(host){
  const frames=Object.fromEntries([...host.querySelectorAll('[data-glv-frame]')].map(el=>[el.dataset.glvFrame,el]));
  const body=host.querySelector('[data-glv-body]'),animated=typeof body.animate==='function';
  let phase='open',greeted=false,covered=false,blocked=true,disposed=false,artReady=false,look=null;
  let visible=front,sequence=null,raf=0,ambientTimer,ambientIndex=0;
  const breathing=animated?body.animate([
    {transform:'translateY(0px) rotate(-.4deg)'},{transform:'translateY(2px) rotate(.4deg)'},{transform:'translateY(0px) rotate(-.4deg)'}
  ],{duration:4800,iterations:Infinity,easing:'ease-in-out'}):null;
  const desiredGaze=()=>e(look===-1?0:look===1?4:2);
  const report=playback=>{host.dataset.playback=playback;host.dataset.pose=covered?'covered':phase==='greeting'?'greeting':'open';};
  function show(name){
    if(name===visible&&host.dataset.frame===name)return;
    if(name!==visible){frames[visible].style.opacity='0';frames[name].style.opacity='1';visible=name;}
    host.dataset.frame=name;
    const n=expressionIndex(name);
    host.dataset.expression=covered?'covered':n===null?'open':n>=8?'greeting':n>=5?'blink':n<2?'lookLeft':n>2?'lookRight':'open';
  }
  function stopAmbient(){clearTimeout(ambientTimer);ambientTimer=undefined;}
  function cancelSequence(){if(raf)cancelAnimationFrame(raf);raf=0;sequence=null;}
  function pauseSequence(){if(raf)cancelAnimationFrame(raf);raf=0;if(sequence)sequence.last=0;}
  function tick(time){
    raf=0;
    if(disposed||blocked||!sequence)return;
    const current=sequence;
    // A delayed browser frame must not jump over illustrated hand positions.
    if(current.last)current.elapsed+=Math.min(time-current.last,50);
    current.last=time;
    const next=current.index+1;
    if(next<current.names.length&&current.elapsed>=current.times[next]){
      current.index=next;show(current.names[next]);
    }
    if(current.index>=current.names.length-1){
      sequence=null;current.done();return;
    }
    // This loop exists only during a finite gesture or expression transition.
    raf=requestAnimationFrame(tick);
  }
  function resumeSequence(){if(sequence&&!raf&&!blocked){sequence.last=performance.now();raf=requestAnimationFrame(tick);}}
  function run(names,interval,done){
    cancelSequence();stopAmbient();
    const path=names.filter((name,n)=>n===0||name!==names[n-1]);
    if(!path.length){done();return;}
    show(path[0]);
    if(path.length===1){done();return;}
    const times=[0];
    for(let n=1;n<path.length;n++){
      const a=coverIndex(path[n-1]),b=coverIndex(path[n]);
      // Slow at the waist/eyes, faster through the middle of the arm movement.
      // Keep the complete source illustrations: no blended faces or limb rig.
      const pace=a!==null&&b!==null ? .7+.6*Math.abs((a+b)/2-5.5)/5.5 : 1;
      times.push(times[n-1]+interval*pace);
    }
    sequence={names:path,times,index:0,elapsed:0,last:0,done};resumeSequence();
  }
  function faceRoute(from,to){
    const a=expressionIndex(from),b=expressionIndex(to);
    if(a===null)return [front,to].filter((name,n,list)=>n===0||name!==list[n-1]);
    let path=[];
    if(a>=8){
      path=[from];
      if(a>12)path.push(e(15),e(12));
      path.push(...range(Math.min(a,12),8).map(e),front);
    }else if(a>=5){
      path=[from];if(a===6)path.push(e(7));if(a!==5)path.push(e(5));path.push(front);
    }else path=[from,...range(a,2).slice(1).map(e)];
    path.push(...range(2,b??2).slice(1).map(e));
    return path;
  }
  function settle(){
    phase=covered?'covered':'open';
    report(blocked?'paused':!animated?'fallback':covered?'held':'playing');
    if(!covered)scheduleAmbient();
  }
  function staticPose(){
    cancelSequence();stopAmbient();show(covered?c(11):desiredGaze());settle();
  }
  function moveGaze(target,done=settle){
    phase='gaze';report('playing');run(faceRoute(visible,target),45,done);
  }
  function scheduleAmbient(delay=2600){
    stopAmbient();if(disposed||blocked||covered||phase!=='open'||!artReady||!animated)return;
    ambientTimer=setTimeout(()=>{
      ambientTimer=undefined;if(disposed||blocked||covered||phase!=='open')return;
      const actions=[['blink',2200],['left',1000],['front',1300],['blink',2300],['right',1000],['front',2600]];
      const [action,nextDelay]=actions[ambientIndex++%actions.length];
      const finish=()=>{phase='open';report('playing');scheduleAmbient(nextDelay);};
      if(action==='blink'){
        phase='blink';run([...faceRoute(visible,front),e(5),e(7),e(6),e(7),e(5),front,...faceRoute(front,desiredGaze()).slice(1)],30,finish);
      }else moveGaze(look===null?e(action==='left'?0:action==='right'?4:2):desiredGaze(),finish);
    },delay);
  }
  function transitionCover(){
    cancelSequence();stopAmbient();phase=covered?'cover':'uncover';report('playing');
    const n=coverIndex(visible);
    if(covered){
      const path=n===null?[...faceRoute(visible,front),...range(0,11).map(c)]:range(n,11).map(c);
      run(path,44,()=>{show(c(11));settle();});
    }else{
      const path=n===null?faceRoute(visible,desiredGaze()):[...range(n,0).map(c),front,...faceRoute(front,desiredGaze()).slice(1)];
      run(path,44,()=>{if(visible!==desiredGaze())moveGaze(desiredGaze());else settle();});
    }
  }
  function greet(){
    if(greeted||disposed||covered||blocked||!artReady||!animated)return;
    greeted=true;phase='greeting';report('playing');
    run([front,...range(8,12).map(e),e(13),e(14),e(13),e(14),e(15),...range(12,8).map(e),front],80,()=>{
      phase='open';
      if(desiredGaze()!==front)moveGaze(desiredGaze());else settle();
    });
  }
  show(front);breathing?.pause();
  artworkReady().then(()=>{
    if(disposed)return;artReady=true;host.dataset.artReady='true';
    if(covered&&animated&&!blocked)transitionCover();else if(!greeted)greet();else scheduleAmbient();
  }).catch(()=>{if(!disposed)host.dataset.artReady='false';});
  return {
    setPose(value){
      if(disposed||value===covered)return;covered=value;if(covered)greeted=true;
      if(blocked||!animated||!artReady)staticPose();else transitionCover();
    },
    setLook(value){
      if(disposed)return;const next=value===null?null:value<9?-1:1;if(next===look)return;look=next;
      if(!covered&&!['greeting','cover','uncover'].includes(phase)&&!blocked&&animated&&artReady)moveGaze(desiredGaze());
    },
    playback({offscreen,reduced,paused}){
      if(disposed)return;blocked=offscreen||reduced||paused;
      if(blocked){
        stopAmbient();breathing?.pause();pauseSequence();
        if(reduced||paused){greeted=true;staticPose();}else report('paused');
        return;
      }
      if(!animated){staticPose();return;}
      breathing?.play();
      if(sequence){report('playing');resumeSequence();return;}
      if(!greeted&&!covered)greet();else{
        report(covered?'held':'playing');
        if(!covered&&ambientTimer===undefined){phase='open';scheduleAmbient();}
      }
    },
    destroy(){disposed=true;cancelSequence();stopAmbient();breathing?.cancel();},
  };
}
