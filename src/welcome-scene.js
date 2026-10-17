/* Hallmark · pre-emit critique: P5 H4 E4 S5 R5 V5 · original parish welcome artwork */
import {parishLogo} from './parish-logo.js';
import {createWelcomeReveals} from './welcome-reveals.js';
import {prepareWelcomeSvgMotion} from './welcome-svg-motion.js';

function dove() {
  return `<svg viewBox="0 0 160 128" fill="none" aria-hidden="true">
    <g class="dove-wing-far"><path class="dove-shadow" d="M83 84C92 55 108 29 140 11C140 31 129 53 111 71L96 91Z"/><path class="dove-feather" d="M93 76 126 32M101 77 137 28"/></g>
    <path class="dove-shadow" d="M58 85 17 83 31 94 12 100 54 108 82 99Z"/>
    <path class="dove-body" d="M41 92C60 77 81 78 96 73C107 69 109 54 123 53C135 51 142 61 137 69C132 79 117 81 109 94C94 113 64 112 41 92Z"/>
    <g class="dove-wing-near"><path class="dove-body" d="M86 91C62 82 35 65 17 27C11 15 13 8 17 10L38 29 29 9C47 14 60 30 70 47L65 20C86 36 96 63 96 80Z"/><path class="dove-feather" d="M78 76C61 61 49 45 40 30M72 82C50 67 32 49 23 30M86 76 73 45"/></g>
    <path class="dove-beak" d="m138 61 16 5-17 4Z"/><circle class="dove-eye" cx="128" cy="61" r="2.2"/>
    <path class="dove-feather" d="m101 96 8 7m-14-4 8 8M26 99l21 1"/>
    <path class="dove-olive" d="m147 68-2 19m0-5c-9-3-12-8-11-12 7 0 11 6 11 12Zm1-4c7-2 10-6 9-10-6 0-9 4-9 10Z"/>
  </svg>`;
}

function bellTower(){
  return `<g class="welcome-bell-tower" data-welcome-bell-tower transform="translate(1498 0)">
    <ellipse class="welcome-tower-shadow" cy="859" rx="104" ry="15"/>
    <g data-welcome-bell-building>
    <path fill="url(#welcome-stone)" d="M-64 426H64v401H-64Z"/>
    <path class="church-shadow" d="M43 426h21v401H43Z"/>
    <path class="church-pilaster" d="M-61 443h10v367h-10Zm102 0h10v367H41Z"/>
    <path class="church-roof" d="m-81 428 81-101 81 101Z"/>
    <path class="roof-highlight" d="m-3 339-58 78h22Z"/>
    <path class="church-gold-line" d="M0 327v-64m-17 19h34"/>
    <path class="church-cornice" d="M-73 428H73v16H-73Zm7 184H66v16H-66Zm4 190H62v25H-62Z"/>
    <path class="bell-recess" d="M-43 604V498q43-66 86 0v106Z"/>
    <path class="bell-arch-rim" d="M-49 605V496q49-77 98 0v109"/>
    <path class="bell-yoke" d="M-29 488h58v9h-58ZM-4 496h8v19h-8Z"/>
    <path class="bell-tower-bronze" d="M-31 575q13-16 13-42 0-21 18-21t18 21q0 26 13 42l5 7h-72Z"/>
    <path class="bell-tower-highlight" d="M-12 529q0-10 10-12-6 12-5 27-1 19-10 31h-9q12-20 14-46Z"/>
    <path class="bell-tower-lip" d="M-36 582h72v8h-72Z"/>
    <circle class="bell-tower-clapper" cy="595" r="7"/>
    <circle class="tower-clock" cy="681" r="32"/>
    <g class="tower-clock-detail">${Array.from({length:12},(_,n)=>`<path d="M0 655v5" transform="rotate(${n*30} 0 681)"/>`).join('')}<path d="M0 663v18l13 7"/></g>
    <path class="bell-recess" d="M-28 786v-42q28-33 56 0v42Z"/>
    <g class="tower-louvres">${Array.from({length:4},(_,n)=>`<path d="M-22 ${751+n*9}h44"/>`).join('')}</g>
    <path class="church-step" d="M-83 827H83v10H-83Zm-8 10H91v11H-91Z"/>
    <ellipse class="welcome-tower-glow" fill="url(#welcome-sanctuary)" cy="548" rx="59" ry="69"/>
    </g>
  </g>`;
}

function churchArtwork() {
  const stars=[[120,160,2],[255,270,1.5],[430,100,2],[550,300,1],[725,125,1.5],[870,230,2],[1110,110,2],[1280,250,1.2],[1450,140,2],[1500,360,1.2],[660,390,1],[1350,450,1.5]];
  const windows=(x,y,count,step)=>Array.from({length:count},(_,n)=>`<use href="#welcome-window" x="${x+n*step}" y="${y}"/>`).join('');
  return `<svg class="welcome-panorama" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMax slice" fill="none" aria-hidden="true">
    <defs>
      <linearGradient id="welcome-sky" x1="800" y1="0" x2="800" y2="1000" gradientUnits="userSpaceOnUse"><stop class="sky-stop-top"/><stop class="sky-stop-mid" offset=".6"/><stop class="sky-stop-bottom" offset="1"/></linearGradient>
      <radialGradient id="welcome-halo"><stop class="halo-stop-inner"/><stop class="halo-stop-mid" offset=".4"/><stop class="halo-stop-outer" offset="1"/></radialGradient>
      <radialGradient id="welcome-sanctuary"><stop class="sanctuary-stop-inner"/><stop class="sanctuary-stop-mid" offset=".35"/><stop class="halo-stop-outer" offset="1"/></radialGradient>
      <linearGradient id="welcome-stone" x1="0" y1="0" x2="1" y2="1"><stop class="stone-stop-light"/><stop class="stone-stop-dark" offset="1"/></linearGradient>
      <linearGradient id="welcome-path" x1="1000" y1="820" x2="900" y2="1000" gradientUnits="userSpaceOnUse"><stop class="path-stop-light"/><stop class="path-stop-dark" offset="1"/></linearGradient>
      <linearGradient id="welcome-glass" x1="0" y1="0" x2="0" y2="1"><stop class="glass-stop-light"/><stop class="glass-stop-dark" offset="1"/></linearGradient>
      <g id="welcome-window"><path class="church-window-frame" d="M0 48V15Q12-8 24 15V48Z"/><path fill="url(#welcome-glass)" d="M5 43V17Q12 1 19 17V43Z"/><path class="church-mullion" d="M12 10v34M5 26h14"/></g>
      <g id="welcome-tree"><path class="tree-trunk" d="M0 0v-68"/><path class="tree-crown" d="M-30-30Q-52-53-22-68Q-35-97-4-111Q29-113 27-85Q58-76 34-48Q41-22 0-28Z"/></g>
      <g id="welcome-lamp"><path class="lamp-post" d="M0 0v-69m-8 0h16m-18-29h20l-3 28H-7Z"/><path class="lamp-light" d="M-7-95H7L5-73H-5Z"/><path class="lamp-cap" d="m-14-99 14-11 14 11Z"/><circle fill="url(#welcome-halo)" cy="-84" r="48" opacity=".55"/></g>
    </defs>
    <path class="welcome-sky-fill" fill="url(#welcome-sky)" d="M0 0h1600v1000H0Z"/>
    <g data-welcome-depth="sky">
    <g class="welcome-halo-motion" data-welcome-light="halo"><circle fill="url(#welcome-halo)" cx="1050" cy="400" r="440"/></g>
    <g class="welcome-rays"><path d="m1050 352-330-352h92Zm0 0L1124 0h95Zm0 0 550-176v100Zm0 0L1510 0h90Z"/></g>
    <g class="welcome-moon-motion" data-welcome-ambient="moon"><circle class="welcome-moon" cx="1050" cy="350" r="118"/>
    <circle class="moon-ring" cx="1050" cy="350" r="132"/></g>
    <g class="welcome-stars">${stars.map(([x,y,r],n)=>`<circle cx="${x}" cy="${y}" r="${r}"${n%2?` data-welcome-star="${n}"`:''}/>`).join('')}</g>
    <g class="welcome-clouds"><path d="M700 255c32-24 72-29 110-8 15-36 78-40 102-7 42-13 76-2 88 18H670Z"/><path d="M1160 175c25-22 62-20 80-2 33-25 68-16 87 6 41-7 56 6 61 16h-256Z"/><path d="M280 410c40-30 82-24 102 0 30-18 61-10 75 14h-210Z"/></g>
    </g>
    <g data-welcome-depth="hills">
    <path class="hill-far" d="M0 660 170 500l200 150 225-220 190 204 230-149 181 166 222-187 182 178v358H0Z"/>
    <path class="hill-near" d="M0 769Q214 610 410 711T787 692Q1037 612 1228 704T1600 683v317H0Z"/>
    </g>
    <g class="village">
      <path class="village-wall" d="M56 764h150v87H56Zm172-21h128v108H228Zm1107 16h129v92h-129Zm142-25h123v117h-123Z"/>
      <path class="village-roof" d="m34 766 96-61 97 61Zm172-22 86-65 86 65Zm1108 16 85-56 85 56Zm141-25 80-57 89 57Z"/>
      ${windows(82,789,3,38)}${windows(250,785,2,48)}${windows(1357,791,2,43)}${windows(1501,781,2,43)}
    </g>
    <path class="church-ground" d="M0 854Q520 793 1000 830T1600 827v173H0Z"/>
    <path fill="url(#welcome-path)" d="m970 824 121 0 226 176H680Z"/>
    <path class="path-seam" d="M925 892h252M868 936h365M804 982h488"/>
    <g data-welcome-depth="church"><g class="welcome-architecture-layout">
    <g class="welcome-church-layout"><g class="welcome-church" data-welcome-ambient="church">
      <!-- The church retains its twin spires; the campanile stands outside it. -->
      <path class="church-side" d="M705 664h650v166H705Z"/>
      <path class="church-roof" d="m679 667 105-111h485l111 111Z"/>
      <path class="roof-rim" d="M686 668h688M722 637h618"/>
      ${[0,437].map(dx=>`<g transform="translate(${dx} 0)">
      <path fill="url(#welcome-stone)" d="M750 465h116v362H750Z"/>
      <path class="church-shadow" d="M838 465h28v362h-28Z"/>
      <path class="church-roof" d="m732 466 77-139 76 139Z"/>
      <path class="roof-highlight" d="m809 337-56 119h22Z"/>
      <path class="church-gold-line" d="M809 327v-64m-17 19h34"/>
      <path class="church-cornice" d="M737 464h142v16H737ZM742 594h132v13H742Z"/>
      <path class="bell-recess" d="M773 568v-44q35-54 70 0v44Z"/>
      <path class="bell" d="M794 557q3-11 3-28 11-14 22 0 0 17 3 28Z"/>
      <path class="church-gold-line" d="M787 559h42"/>
      ${windows(796,652,1,0)}</g>`).join('')}
      <path fill="url(#welcome-stone)" d="M864 615 1027 469l163 146v211H864Z"/>
      <path class="church-facade" d="m886 615 141-124 141 124v211H886Z"/>
      <g class="church-stonework"><path d="M754 624h80m-80 86h80m-80 87h80m357-173h80m-80 86h80m-80 87h80M889 646h67m138 0h68m-273 37h67m138 0h68m-273 64h58m159 0h57m-274 38h58m159 0h57"/></g>
      <path class="church-pilaster" d="M875 631h13v181h-13Zm290 0h13v181h-13ZM755 615h10v197h-10Zm437 0h10v197h-10Z"/>
      <path class="church-roof" d="m842 621 185-177 185 177-19 10-166-156-166 156Z"/>
      <path class="church-gold-line" d="M1027 446v-69m-19 19h38"/>
      <path class="church-cornice" d="M862 714h329v14H862ZM866 812h324v15H866Z"/>
      <circle class="rose-frame" cx="1027" cy="613" r="48"/>
      <circle fill="url(#welcome-glass)" cx="1027" cy="613" r="37"/>
      <g class="rose-petals">${Array.from({length:8},(_,n)=>`<ellipse cx="1027" cy="594" rx="7" ry="15" transform="rotate(${n*45} 1027 613)"/>`).join('')}<circle cx="1027" cy="613" r="9"/></g>
      <path class="church-door-frame" d="M967 827v-58q60-91 120 0v58Z"/>
      <path fill="url(#welcome-glass)" d="M980 827v-53q47-73 94 0v53Z"/>
      <path class="door-detail" d="M1027 744v83m-37-32h74m-37-29-21 29m21-29 21 29"/>
      <path class="church-gold-line" d="M900 742v69m25-69v69m204-69v69m25-69v69"/>
      ${windows(911,664,1,0)}${windows(1119,664,1,0)}${windows(716,734,1,0)}${windows(1314,734,1,0)}
      <path class="church-step" d="M737 828h581v12H737Zm-15 12h611v12H722Zm-15 12h641v12H707Z"/>
      <path class="church-step-line" d="M738 839h579m-594 12h609"/>
      <g class="welcome-sanctuary-light" data-welcome-light="sanctuary" fill="url(#welcome-sanctuary)">
        <circle cx="1027" cy="613" r="75"/><ellipse cx="1027" cy="790" rx="80" ry="73"/>
        ${[[808,677],[1244,677],[923,689],[1131,689],[728,759],[1326,759]].map(([cx,cy])=>`<circle cx="${cx}" cy="${cy}" r="34"/>`).join('')}
      </g>
    </g></g>
    <g class="welcome-tower-layout">${bellTower()}</g>
    </g></g>
    <g>${[500,625,1580].map((x,n)=>`<use href="#welcome-tree" transform="translate(${x} ${875+n%2*32}) scale(${n%2?.9:.8})"/>`).join('')}</g>
    <g class="garden-shrubs"><ellipse cx="747" cy="879" rx="84" ry="20"/><ellipse cx="1312" cy="879" rx="84" ry="20"/><ellipse cx="450" cy="945" rx="180" ry="54"/><ellipse cx="1510" cy="946" rx="174" ry="54"/></g>
    <use href="#welcome-lamp" x="813" y="915"/><use href="#welcome-lamp" x="1250" y="915"/>
    <path class="garden-edge" d="M0 971q260-71 610 21m744-4q135-55 246-16"/>
  </svg>`;
}

export function welcomeBackdrop(){
  return `<div class="welcome-scene" data-welcome-scene>
      ${churchArtwork()}
      <div class="welcome-doves" data-welcome-depth="flock" aria-hidden="true">${Array.from({length:5},(_,n)=>`<div class="welcome-dove-track" data-welcome-dove="${n}"><div class="welcome-dove-float"><div class="welcome-dove-depth">${dove()}</div></div>${n<2?Array.from({length:4},(_,m)=>`<span class="welcome-dust" data-welcome-dust="${m}"></span>`).join(''):''}</div>`).join('')}</div>
    </div>`;
}

export function welcomeIdentity(){
  return `<div class="welcome-identity">${parishLogo(88)}<div class="welcome-identity-copy"><strong>Giáo xứ Xuân Hoà</strong><span>Giáo phận Xuân Lộc</span><span>Giáo hạt Tân Mai</span></div></div>`;
}

export function welcomeHero({i}) {
  return `<section class="welcome-hero" aria-labelledby="home-title">
    ${welcomeBackdrop()}${welcomeIdentity()}
    <div class="welcome-copy">
      <h1 id="home-title"><span class="welcome-title-start" data-welcome-enter="0">Cùng em lớn lên </span><span class="welcome-gold-text" data-welcome-enter="1">trong đức tin.<span class="welcome-shine-window" aria-hidden="true"><span class="welcome-shine-ink">trong đức tin.</span></span></span></h1>
      <a class="button welcome-primary" data-welcome-enter="2" data-enter-portal href="#start">Vào cổng giáo lý ${i('arrow')}</a>
    </div>
    <svg class="welcome-edge" viewBox="0 0 1600 80" preserveAspectRatio="none" aria-hidden="true"><path class="welcome-edge-mist" d="M0 28C280 72 490 0 800 24S1300 66 1600 16V80H0Z"/><path d="M0 44C280 80 490 10 800 38S1300 80 1600 32V80H0Z"/></svg>
  </section>`;
}

// A finite entrance brings the flock into the sky; drifting and wingbeats then
// continue alongside the moon/church. All effects share the visibility guards.
export function createWelcomeSceneController(root) {
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer=matchMedia('(hover: hover) and (pointer: fine)');
  const reveals=createWelcomeReveals(root,reduced);
  const phases=new Map();
  let record=null,hasPlayed=false,disposed=false,queued=false;
  const animations=r=>[...r.animations,...r.ambient,...r.effects,...r.depthEffects.values()];
  function resetPointer(r){
    if(r.pointerFrame)cancelAnimationFrame(r.pointerFrame);
    r.pointerFrame=0;
    for(const a of r.depthEffects.values())a.cancel();
    r.depthEffects.clear();
  }
  const stop=r=>{r.token++;resetPointer(r);animations(r).forEach(a=>{
    if(a.currentTime!==null)phases.set(a.id,a.currentTime);
    a.cancel();
  });r.animations=[];r.ambient=[];r.effects=[];r.flights=[];};
  function loop(r,element,keyframes,timing,id,phase=0){
    const animation=element.animate(keyframes,{iterations:Infinity,easing:'ease-in-out',...timing});
    animation.id=id;animation.currentTime=phases.get(id)??phase;r.ambient.push(animation);
  }
  function ambient(r){
    if(r.ambient.length||reduced.matches||!Element.prototype.animate)return;
    const settings=[
      ['moon',4000,'translate3d(-16px,-26px,0) scale(1.035)'],
      ['church',5000,'translate3d(-2px,-8px,0) scale(1.018)']
    ];
    for(const [kind,duration,peak] of settings){
      const element=r.host.querySelector(`[data-welcome-ambient="${kind}"]`);
      loop(r,element,[
        {transform:'translate3d(0,0,0) scale(1)'},{transform:peak}
      ],{duration,direction:'alternate'},`welcome-${kind}`);
    }
    loop(r,r.host.querySelector('[data-welcome-light="halo"]'),[
      {transform:'scale(.97)',opacity:.7},{transform:'scale(1.04)',opacity:1}
    ],{duration:3000,direction:'alternate'},'welcome-halo');
    loop(r,r.host.querySelector('[data-welcome-light="sanctuary"]'),[
      {transform:'scale(1)',opacity:.45},{transform:'scale(1.014)',opacity:.85}
    ],{duration:3800,direction:'alternate'},'welcome-sanctuary');
    r.host.querySelectorAll('[data-welcome-star]').forEach((star,n)=>{
      loop(r,star,[{opacity:.25},{opacity:1}],{duration:2300+n*310,direction:'alternate'},`welcome-star-${n}`,n*870);
    });
    // Counter-moving glyphs stay still while the narrow highlight sweeps past.
    // Only transforms/opacity change; the feathered mask and gradient stay static.
    const offsets=[0,.12,.2,.44,.5,1],shine=r.hero.querySelector('.welcome-shine-window');
    if(shine){loop(r,shine,offsets.map((offset,n)=>({
      offset,transform:`translateX(${n<3?-100:333.333333}%)`,opacity:n===2||n===3?.65:0
    })),{duration:9000},'welcome-shine-window');
    loop(r,r.hero.querySelector('.welcome-shine-ink'),offsets.map((offset,n)=>({
      offset,transform:`translateX(${n<3?30:-100}%)`
    })),{duration:9000},'welcome-shine-ink');}
  }
  function bindPointer(r){
    const strengths={sky:[5,3],hills:[2,1],church:[8,4],flock:[-4,-3]};
    const depths=[...r.host.querySelectorAll('[data-welcome-depth]')];
    let bounds=null,target=[0,0];
    const enabled=()=>finePointer.matches&&!reduced.matches&&r.visible&&!document.hidden&&Element.prototype.animate;
    const flush=()=>{
      r.pointerFrame=0;if(record!==r||!enabled())return;
      const current=depths.map(element=>getComputedStyle(element).transform);
      depths.forEach((element,n)=>{
        const [x,y]=strengths[element.dataset.welcomeDepth];
        r.depthEffects.get(element)?.cancel();
        const animation=element.animate([{transform:current[n]},{transform:`translate3d(${target[0]*x}px,${target[1]*y}px,0)`}],{duration:300,easing:'ease-out',fill:'forwards'});
        animation.id=`welcome-depth-${element.dataset.welcomeDepth}`;r.depthEffects.set(element,animation);
      });
    };
    const schedule=()=>{if(!r.pointerFrame)r.pointerFrame=requestAnimationFrame(flush);};
    const enter=()=>{if(enabled())bounds=r.hero.getBoundingClientRect();};
    const move=event=>{
      if(!enabled()||event.pointerType!=='mouse')return;
      if(!bounds)bounds=r.hero.getBoundingClientRect();
      target=[Math.max(-1,Math.min(1,(event.clientX-bounds.left)/bounds.width*2-1)),Math.max(-1,Math.min(1,(event.clientY-bounds.top)/bounds.height*2-1))];schedule();
    };
    const leave=()=>{target=[0,0];bounds=null;if(enabled())schedule();};
    r.hero.addEventListener('pointerenter',enter);r.hero.addEventListener('pointermove',move);r.hero.addEventListener('pointerleave',leave);
    r.unbind=()=>{r.hero.removeEventListener('pointerenter',enter);r.hero.removeEventListener('pointermove',move);r.hero.removeEventListener('pointerleave',leave);};
  }
  function layout(r){
    if(!r.flights.length)return;
    // Read geometry together only on mount/resize; no measurement during flight.
    const rect=r.host.getBoundingClientRect(),{width,height}=rect;
    const svg=r.host.querySelector('.welcome-panorama'),matrix=svg.getScreenCTM();
    const sky=new DOMPoint(1050,263).matrixTransform(matrix);
    sky.y=Math.min(sky.y,r.host.querySelector('[data-welcome-bell-building]').getBoundingClientRect().top);
    const portrait=width<900&&innerHeight>innerWidth;
    const content=r.hero.querySelector(r.hero.matches('.auth-scene-page')?'.welcome-identity':'.welcome-primary');
    const contentBottom=content.getBoundingClientRect().bottom-rect.top;
    const sizes=r.flights.map(({bird})=>({width:bird.offsetWidth,height:bird.offsetHeight}));
    const gap=Math.min(width*(portrait?.14:.065),90);
    const destinations=sizes.map((size,n)=>({
      x:Math.max(12,Math.min(width-size.width-12,sky.x-rect.left+[-1.3,-.55,.12,.8,1.45][n]*gap-size.width/2)),
      y:Math.max(portrait?contentBottom+14:24,sky.y-rect.top-28-size.height-[8,28,14,36,18][n])
    }));
    for(const [n,{animation}] of r.flights.entries()){
      const end=destinations[n],start={x:-sizes[n].width-20,y:height+20+n*12};
      const control={x:width*.16,y:height*.36};
      animation.effect.setKeyframes([0,.12,.32,.56,.8,1].map(t=>({
        transform:`translate3d(${(1-t)**2*start.x+2*(1-t)*t*control.x+t*t*end.x}px,${(1-t)**2*start.y+2*(1-t)*t*control.y+t*t*end.y}px,0) rotate(${-18+12*t}deg)`,
        opacity:t===0?0:1,offset:t
      })));
    }
  }
  function play(r,entrance=!hasPlayed){
    if(disposed||reduced.matches||document.hidden||!r.visible||!Element.prototype.animate)return;
    const birds=[...r.host.querySelectorAll('[data-welcome-dove]')];
    stop(r);if(entrance)phases.clear();
    const token=r.token;hasPlayed=true;r.host.dataset.welcomeState=entrance?'flying':'complete';
    ambient(r);
    if(entrance)r.hero.querySelectorAll('[data-welcome-enter]').forEach((element,n)=>{
      const animation=element.animate([{opacity:0,transform:'translateY(12px)'},{opacity:1,transform:'translateY(0)'}],{duration:680,delay:120+n*110,easing:'ease-out',fill:'backwards'});
      animation.id=`welcome-title-${n}`;r.effects.push(animation);
    });
    birds.forEach((bird,n)=>{
      const delay=n*140,duration=3600+n*100;
      const flight=bird.animate([{opacity:0},{opacity:1}],{duration,delay,easing:'cubic-bezier(.22,.7,.22,1)',fill:'both'});
      flight.id=`welcome-flight-${n}`;
      r.animations.push(flight);r.flights.push({bird,animation:flight});
      if(!entrance)flight.currentTime=phases.get(flight.id)??duration+delay;
      loop(r,bird.querySelector('.welcome-dove-float'),[
        {transform:'translate3d(0,0,0) rotate(0deg)'},
        {transform:`translate3d(${n%2?8:-9}px,${-10-n*2}px,0) rotate(${n%2?3:-3}deg)`}
      ],{duration:1800+n*270+([2,4].includes(n)?1000:0),direction:'alternate'},`welcome-hover-${n}`);
      for(const [selector,sign] of [['.dove-wing-near',1],['.dove-wing-far',-1]]){
        const tucked={transform:`rotate(${sign*18}deg) scaleY(.28)`},open={transform:`rotate(${sign*-8}deg) scaleY(1)`};
        loop(r,bird.querySelector(selector),[
          {...open,offset:0},{...tucked,offset:.055},{...open,offset:.11},
          {...tucked,offset:.165},{...open,offset:.22},{...tucked,offset:.275},
          {...open,offset:.33},{...open,offset:.8},{...tucked,offset:.88},
          {...open,offset:.96},{...open,offset:1}
        ].map(frame=>({...frame,easing:'ease-in-out'})),{duration:5500+n*290+([2,4].includes(n)?1600:0),easing:'linear'},`welcome-wing-${n}-${sign}`);
      }
      if(entrance)bird.querySelectorAll('[data-welcome-dust]').forEach((dust,m)=>{
        const animation=dust.animate([
          {opacity:0,transform:`translate3d(8px,${22+m*3}px,0) scale(.6)`},
          {opacity:.65,transform:`translate3d(${-8-m*4}px,${28+m*3}px,0) scale(1)`,offset:.25},
          {opacity:0,transform:`translate3d(${-35-m*7}px,${44+m*4}px,0) scale(.4)`}
        ],{duration:1700,delay:900+n*140+m*220,easing:'ease-out'});
        animation.id=`welcome-dust-${n}-${m}`;r.effects.push(animation);
      });
    });
    layout(r);
    Promise.all(r.animations.map(a=>a.finished.catch(()=>{}))).then(()=>{
      if(record!==r||r.token!==token||disposed)return;
      r.host.dataset.welcomeState='complete';
    });
  }
  function visibility(){
    reveals.visibility();
    const r=record;if(!r)return;
    if(reduced.matches){stop(r);r.host.dataset.welcomeState='reduced';return;}
    if(document.hidden||!r.visible){resetPointer(r);animations(r).forEach(a=>{if(a.playState==='running')a.pause();});return;}
    animations(r).forEach(a=>{if(a.playState==='paused')a.play();});
    if(r.host.dataset.welcomeState==='reduced')r.host.dataset.welcomeState='still';
    if(!r.flights.length)play(r);
  }
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries)if(record?.host===entry.target){record.visible=entry.isIntersecting;visibility();}
  },{threshold:.08});
  const resize=new ResizeObserver(()=>{if(record){resetPointer(record);layout(record);}});
  function sync(){
    queued=false;if(disposed)return;
    reveals.sync();
    const host=root.querySelector('[data-welcome-scene]');
    if(host===record?.host)return;
    if(record){observer.unobserve(record.host);resize.unobserve(record.host);record.unbind();stop(record);record=null;}
    if(!host)return;
    prepareWelcomeSvgMotion(host);
    record={host,hero:host.closest('.welcome-hero'),animations:[],ambient:[],effects:[],flights:[],depthEffects:new Map(),pointerFrame:0,visible:false,token:0};
    bindPointer(record);
    host.dataset.welcomeState=reduced.matches?'reduced':'still';observer.observe(host);resize.observe(host);
  }
  const mutations=new MutationObserver(()=>{if(!queued){queued=true;queueMicrotask(sync);}});
  mutations.observe(root,{childList:true,subtree:true});
  const login=()=>{hasPlayed=false;reveals.reset();if(record&&!record.hero.matches('.auth-scene-page'))play(record,true);};
  const pointerChange=()=>{if(record&&!finePointer.matches)resetPointer(record);};
  root.addEventListener('parish:welcome',login);
  document.addEventListener('visibilitychange',visibility);reduced.addEventListener('change',visibility);finePointer.addEventListener('change',pointerChange);sync();
  return {destroy(){disposed=true;mutations.disconnect();observer.disconnect();resize.disconnect();reveals.destroy();if(record){record.unbind();stop(record);}
    root.removeEventListener('parish:welcome',login);
    document.removeEventListener('visibilitychange',visibility);reduced.removeEventListener('change',visibility);finePointer.removeEventListener('change',pointerChange);
  }};
}
