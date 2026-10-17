// Original GLV character redrawn as native Lottie vectors. No bitmap dependencies.
import fs from 'node:fs';
import path from 'node:path';
const C={ink:'#3d2c29',skin:'#ffcc9d',skinShade:'#f3ae82',skinLight:'#ffdfba',cheek:'#f48c79',
 white:'#fffdf9',shade:'#e0e4ec',hat:'#dda359',hatLight:'#f0c586',hatShade:'#bc7b3d',brown:'#9a653f',
 darkBrown:'#704c34',hair:'#4b3026',hairLight:'#6c4631',red:'#ed443d',redShade:'#c92d31',gold:'#ffcd58',
 teal:'#5c9296',tealShade:'#3d6c74',navy:'#34485a',silver:'#c9d2d6',mouth:'#692b2e',tongue:'#f57972'};
const prop=k=>({a:0,k});
const color=c=>c.slice(1).match(/../g).map(v=>parseInt(v,16)/255).concat(1);
const keys=values=>{
 const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 if(values.every(([,value])=>same(value,values[0][1])))return prop(values[0][1]);
 const points=values.filter(([,value],n)=>n===0||n===values.length-1||!same(value,values[n-1][1])||!same(value,values[n+1][1]));
 return {a:1,k:points.map(([t,value],n)=>({t,s:Array.isArray(value)?value:[value],...(n<points.length-1?{o:{x:[0],y:[0]},i:{x:[1],y:[1]}}:{})}))};
};
const transform=()=>({ty:'tr',p:prop([0,0]),a:prop([0,0]),s:prop([100,100]),r:prop(0),o:prop(100),sk:prop(0),sa:prop(0)});
const fill=c=>({ty:'fl',c:prop(color(c)),o:prop(100),r:1});
const stroke=(c=C.ink,w=4)=>({ty:'st',c:prop(color(c)),o:prop(100),w:prop(w),lc:2,lj:2,ml:4});
function group(shape,c,outline=true,w=4){return {ty:'gr',it:[shape,...(c?[fill(c)]:[]),...(outline?[stroke(typeof outline==='string'?outline:C.ink,w)]:[]),transform()]};}
const oval=(x,y,w,h,c,outline=true)=>group({ty:'el',p:prop([x,y]),s:prop([w,h]),d:1},c,outline);
const roundRect=(x,y,w,h,r,c,outline=true)=>group({ty:'rc',p:prop([x,y]),s:prop([w,h]),r:prop(r),d:1},c,outline);
function curve(v,c,closed=true,smooth=.15,outline=true,width=4){
 const tangents=v.map((point,n)=>{
  if(!closed&&(n===0||n===v.length-1))return [0,0];
  const previous=v[(n+v.length-1)%v.length],next=v[(n+1)%v.length];return [(next[0]-previous[0])*smooth,(next[1]-previous[1])*smooth];
 });
 return group({ty:'sh',ks:prop({v,i:tangents.map(([x,y])=>[-x,-y]),o:tangents,c:closed})},c,outline,width);
}
const line=(v,c=C.ink,width=4,smooth=.15)=>curve(v,null,false,smooth,c,width);
const star=(x,y,r,c)=>curve(Array.from({length:10},(_,n)=>{const a=n*Math.PI/5-Math.PI/2,d=n%2?r*.45:r;return [x+Math.cos(a)*d,y+Math.sin(a)*d];}),c,true,0,false);
const layer=(name,shapes,ks={},ind=1)=>({ddd:0,ind,ty:4,nm:name,sr:1,ks:{o:prop(100),r:prop(0),p:prop([0,0,0]),a:prop([0,0,0]),s:prop([100,100,100]),...ks},
 shapes:shapes.slice().reverse(),ao:0,ip:0,op:241,st:0,bm:0});
const composition=(name,layers,op=61)=>({v:'5.13.0',fr:60,ip:0,op,w:480,h:512,nm:name,ddd:0,assets:[],layers,markers:[]});
const cubic=(a,b,c,d,t)=>[0,1].map(i=>(1-t)**3*a[i]+3*(1-t)**2*t*b[i]+3*(1-t)*t*t*c[i]+t**3*d[i]);
export function armJoints(side,progress){
 const shoulder=[side<0?134:346,354],upper=62,lower=90,reflect=([x,y])=>[side<0?x:480-x,y];
 const hand=progress<=40?cubic(...[[181,442],[82,438],[77,267],[108,229]].map(reflect),progress/40):
  cubic(...[[108,229],[122,203],[178,210],[198,218]].map(reflect),(progress-40)/20);
 const dx=hand[0]-shoulder[0],dy=hand[1]-shoulder[1],distance=Math.max(28.01,Math.min(151.99,Math.hypot(dx,dy)));
 const theta=Math.atan2(dy,dx),bend=Math.acos((upper*upper+distance*distance-lower*lower)/(2*upper*distance));
 const angle=theta+(side<0?1:-1)*bend,elbow=[shoulder[0]+upper*Math.cos(angle),shoulder[1]+upper*Math.sin(angle)];
 return {shoulder,elbow,hand,upperAngle:angle*180/Math.PI-90,lowerAngle:Math.atan2(hand[1]-elbow[1],hand[0]-elbow[0])*180/Math.PI-90,upper,lower};
}
function torso(){return [
 oval(240,491,178,15,'#e9d8c4',false),roundRect(240,390,238,190,34,C.brown),
 roundRect(130,413,44,74,15,C.hatShade),roundRect(350,413,44,74,15,C.hatShade),
 roundRect(240,319,249,56,24,C.teal),oval(119,319,36,57,C.teal),oval(361,319,36,57,C.teal),
 oval(119,319,20,39,C.tealShade),oval(361,319,20,39,C.tealShade),line([[118,306],[113,314],[119,330]],C.teal,3),line([[362,306],[367,314],[361,330]],C.teal,3),
 roundRect(240,478,182,25,10,C.navy),
 curve([[145,327],[180,315],[211,319],[240,331],[269,319],[300,315],[335,327],[354,357],[333,388],[321,459],[159,459],[147,388],[126,357]],C.white),
 curve([[146,355],[167,369],[169,441],[183,457],[159,457],[148,388],[127,357]],C.shade,true,.1,false),
 curve([[334,355],[313,369],[311,441],[297,457],[321,457],[332,388],[353,357]],C.shade,true,.1,false),
 curve([[218,286],[262,286],[265,317],[240,340],[215,317]],C.skin),
 curve([[218,286],[262,286],[261,304],[240,313],[219,304]],C.skinShade,true,.1,false),
 curve([[201,311],[220,315],[239,339],[221,351],[190,327]],C.white,true,.03),
 curve([[279,311],[260,315],[241,339],[259,351],[290,327]],C.white,true,.03),
 curve([[157,326],[177,320],[181,360],[172,416],[159,438],[147,429],[155,379]],C.brown,true,.1),
 curve([[323,326],[303,320],[299,360],[308,416],[321,438],[333,429],[325,379]],C.brown,true,.1),
 roundRect(162,403,29,18,4,C.hat),roundRect(318,403,29,18,4,C.hat),
 line([[154,403],[169,403]],C.darkBrown,3),line([[311,403],[326,403]],C.darkBrown,3),
 curve([[177,316],[198,311],[239,338],[281,311],[303,316],[273,350],[240,359],[207,350]],C.gold,true,.08),
 curve([[185,319],[198,318],[240,346],[282,318],[295,319],[270,343],[240,353],[210,343]],C.red,true,.08,false),
 curve([[235,355],[232,387],[211,427],[207,443],[200,422],[215,378]],C.gold,true,.08),
 curve([[232,365],[226,388],[210,422],[207,432],[207,419],[220,380]],C.red,true,.08,false),
 curve([[245,355],[248,387],[269,427],[273,443],[280,422],[265,378]],C.gold,true,.08),
 curve([[248,365],[254,388],[270,422],[273,432],[273,419],[260,380]],C.red,true,.08,false),
 oval(240,355,34,26,C.gold),oval(240,354,23,16,C.red,false),
 roundRect(240,464,181,20,6,C.darkBrown),roundRect(240,464,41,25,5,C.silver),
 roundRect(240,461,29,7,2,'#e9eff0',false),line([[191,384],[189,432]],'#edf0f4',3)
 ];}
function headShapes(){return [
 oval(240,181,219,209,C.hair),
 oval(139,232,33,46,C.skin),oval(341,232,33,46,C.skin),
 line([[138,222],[130,231],[140,240]],'#d38c6f',3),line([[342,222],[350,231],[340,240]],'#d38c6f',3),
 oval(240,213,195,185,C.skin),
 curve([[157,252],[192,280],[240,296],[288,280],[323,252],[312,281],[282,299],[240,305],[198,299],[168,281]],C.skinShade,true,.18,false),
 oval(169,252,31,16,C.cheek,false),oval(311,252,31,16,C.cheek,false),
 line([[237,240],[235,246],[242,248]],'#d48b6b',3),
 curve([[207,263],[240,266],[273,263],[267,281],[254,293],[238,296],[220,287]],C.mouth,true,.18),
 curve([[214,267],[240,270],[266,267],[262,276],[218,276]],C.white,true,.1,false),
 oval(242,288,36,13,C.tongue,false),
 line([[177,183],[193,178],[215,183]],C.ink,5),line([[265,183],[287,178],[303,183]],C.ink,5),
 curve([[137,188],[144,145],[174,122],[220,112],[265,119],[310,143],[334,184],[310,170],[298,151],[278,168],[278,145],[248,171],[250,145],[222,168],[225,144],[194,167],[200,143],[166,176]],C.hair,true,.08),
 curve([[155,154],[178,139],[196,130],[181,147],[170,151]],C.hairLight,true,.08,false),
 curve([[205,137],[229,124],[247,125],[231,139],[218,146]],C.hairLight,true,.08,false),
 curve([[267,136],[288,141],[301,157],[283,149]],C.hairLight,true,.08,false),
 curve([[128,104],[151,66],[190,43],[237,36],[285,44],[318,66],[342,112],[327,130],[161,126]],C.hat,true,.13),
 curve([[143,99],[166,70],[204,52],[230,46],[193,78],[177,108]],C.hatLight,true,.1,false),
 curve([[274,45],[299,66],[309,91],[308,121],[330,127],[342,112],[318,66]],C.hatShade,true,.12,false),
 line([[239,39],[224,61],[218,82],[218,104]],'#b87b3e',3),line([[285,48],[297,68],[301,93]],'#b87b3e',3),
 curve([[132,99],[179,91],[230,94],[287,104],[334,120],[339,136],[286,122],[227,109],[175,107],[125,116]],C.darkBrown,true,.1),
 curve([[105,110],[147,98],[198,99],[252,108],[308,123],[352,144],[376,163],[373,174],[350,178],[308,162],[255,144],[202,130],[151,126],[116,131],[101,125]],C.hat,true,.14),
 curve([[111,112],[149,104],[198,105],[251,114],[307,129],[350,148],[366,162],[347,154],[302,136],[248,122],[196,113],[150,111],[110,120]],C.hatLight,true,.1,false),
 oval(157,85,5,8,C.darkBrown,false),oval(322,105,5,8,C.darkBrown,false)
 ];}
function eye(x){return [oval(x,218,53,63,C.white),oval(x+1,220,33,46,'#614334',false),
 oval(x+1,215,28,38,'#271f22',false),oval(x+1,233,23,13,'#8c653a',false),star(x+1,219,12,C.gold),
 oval(x+10,203,8,10,C.white,false),oval(x-7,233,4,5,C.white,false)];}
function upperShapes(){return [roundRect(0,45,32,60,16,C.skin),curve([[-13,33],[-5,31],[-7,66],[-14,70]],C.skinLight,true,.15,false),
 curve([[-24,-5],[-16,-21],[12,-23],[25,-5],[26,20],[18,29],[-20,29],[-27,15]],C.white,true,.16),
 curve([[15,-13],[24,-4],[25,19],[16,26],[9,25],[14,11]],C.shade,true,.15,false),line([[-21,17],[-3,22],[19,19]],'#bbc4d2',2)];}
function lowerShapes(side){
 const hand=[[-14,65],[-23,76],[-34,83],[-35,90],[-28,94],[-20,87],[-22,106],[-18,116],[-12,113],[-9,123],[-2,123],[1,116],[6,126],[13,123],[14,115],[21,118],[27,112],[26,91],[20,74],[14,65]];
 const mirror=v=>v.map(([x,y])=>[side<0?x:-x,y]);
 return [curve([[-16,-8],[15,-8],[17,69],[23,86],[-23,86],[-17,67]],C.skin,true,.16),
  curve([[-12,2],[-5,2],[-6,61],[-12,68]],C.skinLight,true,.13,false),
  curve(mirror(hand),C.skin,true,.16),
  curve(mirror([[-17,81],[-9,76],[11,77],[17,87],[12,96],[-10,95]]),C.skinLight,true,.2,false),
  line(mirror([[-12,105],[-11,113]]),'#db9b77',2),line(mirror([[1,108],[1,116]]),'#db9b77',2),line(mirror([[14,108],[14,115]]),'#db9b77',2)];
}
function arm(side,part){
 const name=`glv-${side<0?'left':'right'}-${part}`,upper=part==='upper';
 const states=Array.from({length:61},(_,n)=>armJoints(side,n));
 const angles=states.map((s,t)=>[t,upper?s.upperAngle:s.lowerAngle]);
 for(let n=1;n<angles.length;n++){
  while(angles[n][1]-angles[n-1][1]>180)angles[n][1]-=360;
  while(angles[n][1]-angles[n-1][1]<-180)angles[n][1]+=360;
 }
 if(upper)return composition(name,[layer(name,upperShapes(),{p:prop([...states[0].shoulder,0]),r:keys(angles)})]);
 const upperAngles=states.map((s,t)=>[t,s.upperAngle]);
 for(let n=1;n<upperAngles.length;n++){
  while(upperAngles[n][1]-upperAngles[n-1][1]>180)upperAngles[n][1]-=360;
  while(upperAngles[n][1]-upperAngles[n-1][1]<-180)upperAngles[n][1]+=360;
 }
 const forearm=layer(name,lowerShapes(side),{p:prop([0,62,0]),r:keys(angles.map(([t,a],n)=>[t,a-upperAngles[n][1]]))});
 forearm.parent=2;
 const pivot={ddd:0,ind:2,ty:3,nm:name+' shoulder pivot',sr:1,ks:{o:prop(100),r:keys(upperAngles),p:prop([...states[0].shoulder,0]),a:prop([0,0,0]),s:prop([100,100,100])},ao:0,ip:0,op:61,st:0,bm:0};
 return composition(name,[forearm,pivot]);
}
export function glvRigAnimations(){
 const blink=keys([[0,[100,100,100]],[87,[100,100,100]],[93,[100,1,100]],[98,[100,100,100]],[181,[100,100,100]],[187,[100,1,100]],[192,[100,100,100]],[240,[100,100,100]]]);
 const alpha=keys([[0,100],[88,100],[93,0],[94,0],[98,100],[182,100],[187,0],[188,0],[192,100],[240,100]]);
 const eyes=[200,280].map((x,n)=>layer('Eye '+x,eye(x),{a:prop([x,218,0]),p:prop([x,218,0]),s:blink,o:alpha},n+1));
 const lids=layer('Closed eyelids',[line([[178,220],[199,211],[222,220]],C.ink,5,.3),line([[258,220],[281,211],[302,220]],C.ink,5,.3)],{},3);
 const face=layer('Face, hair, ears and explorer hat',headShapes(),{},4);
 const headLayers=[...eyes,lids,face].map(l=>({...l,parent:5}));
 headLayers.push({ddd:0,ind:5,ty:3,nm:'Head pivot at neck',sr:1,ks:{o:prop(100),r:keys([[0,-.45],[60,.6],[120,-.35],[180,.5],[240,-.45]]),
  p:prop([240,307,0]),a:prop([240,307,0]),s:prop([100,100,100])},ao:0,ip:0,op:241,st:0,bm:0});
 return {'glv-torso':composition('glv-torso',[layer('Shirt, scarf, backpack and fixed torso',torso())]),
  'glv-head':composition('glv-head',headLayers,241),
  ...Object.fromEntries([-1,1].flatMap(side=>['upper','lower'].map(part=>[`glv-${side<0?'left':'right'}-${part}`,arm(side,part)])))};
}
function interpolate(property,t){
 if(!property.a)return property.k;
 const points=property.k;let index=0;while(index<points.length-1&&points[index+1].t<=t)index++;
 if(index===points.length-1)return points[index].s;
 const a=points[index],b=points[index+1],fraction=(t-a.t)/(b.t-a.t);return a.s.map((v,n)=>v+(b.s[n]-v)*fraction);
}
function remap(property,samples){if(!property.a)return property;return keys(samples.map(([time,source])=>[time,interpolate(property,source)]));}
function trajectory(points){return Array.from({length:361},(_,t)=>{
 let n=0;while(n<points.length-2&&points[n+1][0]<=t)n++;
 const [a,x]=points[n],[b,y]=points[n+1],f=Math.max(0,Math.min(1,(t-a)/(b-a))),ease=f*f*f*(10+f*(-15+6*f));
 return [t,x+(y-x)*ease];
});}
export function standaloneGlv(data=glvRigAnimations()){
 const greeting=[[0,0],[28,40],[40,36],[52,44],[64,37],[76,40],[108,0],[240,0],[270,30],[300,60],[330,60],[360,0]];
 const right=[[0,0],[240,0],[270,30],[300,60],[330,60],[360,0]],layers=[];let next=0;
 for(const part of ['left-lower','right-lower','head','left-upper','right-upper','torso']){
  const source=data['glv-'+part],offset=next;
  for(const original of source.layers){
   const item=structuredClone(original);item.ind=++next;item.ip=0;item.op=361;
   if(item.parent)item.parent+=offset;
   if(part.includes('-')){
    const samples=trajectory(part.startsWith('left')?greeting:right);
    item.ks.p=remap(item.ks.p,samples);item.ks.r=remap(item.ks.r,samples);
   }else if(part==='head'){
    // Keep the blink in the middle of the idle section and the head still for cover.
    for(const key of ['r','s','o'])if(item.ks[key].a){
     const samples=Array.from({length:362},(_,n)=>[n,n<240?n:0]);item.ks[key]=remap(item.ks[key],samples);
    }
   }
   layers.push(item);
  }
 }
 return {...composition('GLV Xuân Hoà · hello, blink and cover eyes',layers,361),markers:[{tm:0,cm:'greeting',dr:108},{tm:108,cm:'idle',dr:132},{tm:240,cm:'cover',dr:60},{tm:300,cm:'covered',dr:30},{tm:330,cm:'uncover',dr:30}]};
}
const hex=c=>'#'+c.slice(0,3).map(v=>Math.round(v*255).toString(16).padStart(2,'0')).join('');
export function vectorPoster(data,time=0){
 const mapping=new Map(data.layers.map(l=>[l.ind,l]));
 const trans=l=>{const p=interpolate(l.ks.p,time),a=interpolate(l.ks.a,time),s=interpolate(l.ks.s,time),r=interpolate(l.ks.r,time);return `translate(${p[0]} ${p[1]}) rotate(${Array.isArray(r)?r[0]:r}) scale(${s[0]/100} ${s[1]/100}) translate(${-a[0]} ${-a[1]})`;};
 const shapes=groups=>groups.slice().reverse().map(g=>{
  const shape=g.it[0],f=g.it.find(s=>s.ty==='fl'),s=g.it.find(s=>s.ty==='st');
  const attrs=`fill="${f?hex(f.c.k):'none'}" ${s?`stroke="${hex(s.c.k)}" stroke-width="${s.w.k}" stroke-linecap="round" stroke-linejoin="round"`:''}`;
  if(shape.ty==='el'){const [x,y]=shape.p.k,[w,h]=shape.s.k;return `<ellipse cx="${x}" cy="${y}" rx="${w/2}" ry="${h/2}" ${attrs}/>`;}
  if(shape.ty==='rc'){const [x,y]=shape.p.k,[w,h]=shape.s.k;return `<rect x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" rx="${shape.r.k}" ${attrs}/>`;}
  const q=shape.ks.k;let d='M'+q.v[0].join(' ');
  for(let n=1;n<(q.c?q.v.length+1:q.v.length);n++){const a=(n-1)%q.v.length,b=n%q.v.length;d+=` C${q.v[a][0]+q.o[a][0]} ${q.v[a][1]+q.o[a][1]} ${q.v[b][0]+q.i[b][0]} ${q.v[b][1]+q.i[b][1]} ${q.v[b].join(' ')}`;}
  return `<path d="${d}${q.c?' Z':''}" ${attrs}/>`;
 }).join('');
 return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 512">${data.layers.slice().reverse().filter(l=>l.ty===4).map(l=>`${l.parent?`<g transform="${trans(mapping.get(l.parent))}">`:''}<g transform="${trans(l)}" opacity="${(interpolate(l.ks.o,time)[0]??interpolate(l.ks.o,time))/100}">${shapes(l.shapes)}</g>${l.parent?'</g>':''}`).join('')}</svg>`;
}
export function writeGlvLottie(destination){
 fs.mkdirSync(destination,{recursive:true});const data=glvRigAnimations();
 for(const [name,animation] of Object.entries(data))fs.writeFileSync(path.join(destination,name+'.json'),JSON.stringify(animation));
 const standalone=standaloneGlv(data);fs.writeFileSync(path.join(destination,'glv-mascot.json'),JSON.stringify(standalone));
 fs.writeFileSync(path.join(destination,'glv-mascot.svg'),vectorPoster(standalone,0));
 fs.writeFileSync(path.join(destination,'glv-mascot-covered.svg'),vectorPoster(standalone,300));
}
