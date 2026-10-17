// Original project illustrations. Real Lottie shape layers, no raster frames,
// expressions, external images or remote fonts. Regenerate with npm run build.
import fs from 'node:fs';
import path from 'node:path';

const palette={ink:'#543c32',fur:'#c78c62',furLight:'#dda67b',cream:'#ffebcf',ear:'#edb39a',pink:'#efad9e',green:'#79b88b',paper:'#fff9ed',mint:'#d9ebd7',sky:'#c9e6ed',gold:'#efbb62'};
const property=k=>({a:0,k});
const color=hex=>hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255).concat(1);
const fill=hex=>({ty:'fl',c:property(color(hex)),o:property(100),r:1});
const stroke=(hex=palette.ink,width=3)=>({ty:'st',c:property(color(hex)),o:property(100),w:property(width),lc:2,lj:2,ml:4});
const transform=()=>({ty:'tr',p:property([0,0]),a:property([0,0]),s:property([100,100]),r:property(0),o:property(100),sk:property(0),sa:property(0)});
const ellipse=(x,y,w,h,c,outline=true)=>({ty:'gr',it:[{ty:'el',p:property([x,y]),s:property([w,h]),d:1},fill(c),...(outline?[stroke()]:[]),transform()]});
const rect=(x,y,w,h,r,c,outline=true)=>({ty:'gr',it:[{ty:'rc',p:property([x,y]),s:property([w,h]),r:property(r),d:1},fill(c),...(outline?[stroke()]:[]),transform()]});
const curve=(vertices,c,closed=true,ins,outs,width=3)=>({ty:'gr',it:[{ty:'sh',ks:property({v:vertices,i:ins||vertices.map(()=>[0,0]),o:outs||vertices.map(()=>[0,0]),c:closed})},...(closed?[fill(c)]:[]),stroke(closed?palette.ink:c,width),transform()]});
const frames=points=>({a:1,k:points.map(([t,s],index)=>({t,s:Array.isArray(s)?s:[s],...(index<points.length-1?{o:{x:[.33],y:[.33]},i:{x:[.67],y:[.67]}}:{})}))});
function composition(name,w,h,op){
  const layers=[];let next=0;
  const add=(nm,shapes,props={},parent)=>{
    const ind=++next;
    layers.push({ddd:0,ind,ty:shapes?4:3,nm,sr:1,ks:{o:property(100),r:property(0),p:property([0,0,0]),a:property([0,0,0]),s:property([100,100,100]),...props},...(parent?{parent}:{}),...(shapes?{shapes:shapes.slice().reverse()}:{}),ao:0,ip:0,op,st:0,bm:0});return ind;
  };
  return {add,finish:()=>({v:'5.13.0',fr:30,ip:0,op,w,h,nm:name,ddd:0,assets:[],layers:layers.reverse(),markers:[]})};
}

function bear(){
  const {add,finish}=composition('Xuân Hoà · Gấu đồng hành',320,280,133);
  add('Ground',[ellipse(160,261,163,16,palette.mint,false)]);
  add('Body',[ellipse(160,216,143,108,palette.fur),ellipse(160,230,98,72,palette.cream,false)]);
  add('Feet',[ellipse(117,253,58,32,palette.furLight),ellipse(203,253,58,32,palette.furLight)]);
  const head=add('Head motion',null,{p:frames([[0,[0,0,0]],[60,[0,2,0]],[120,[0,0,0]],[132,[0,0,0]]])});
  add('Ears',[ellipse(104,76,50,50,palette.fur),ellipse(216,76,50,50,palette.fur),ellipse(104,76,30,30,palette.ear,false),ellipse(216,76,30,30,palette.ear,false)],{},head);
  add('Face',[ellipse(160,123,146,128,palette.furLight)],{},head);
  add('Hair',[curve([[147,64],[154,52],[161,64],[169,55],[178,69]],palette.furLight)],{},head);
  add('Muzzle',[ellipse(160,155,66,43,palette.cream,false)],{},head);
  add('Cheeks',[ellipse(113,148,23,12,palette.pink,false),ellipse(207,148,23,12,palette.pink,false)],{},head);
  const blink=frames([[0,[100,100,100]],[47,[100,100,100]],[49,[100,8,100]],[51,[100,100,100]],[120,[100,100,100]],[132,[100,100,100]]]);
  for(const x of [133,187])add('Eye '+x,[ellipse(0,0,12,18,palette.ink,false),ellipse(2,-4,3,5,palette.paper,false)],{p:property([x,129,0]),s:blink},head);
  add('Nose',[ellipse(160,145,18,12,palette.ink,false),ellipse(157,143,4,2,palette.paper,false)],{},head);
  add('Smile',[curve([[145,158],[160,166],[175,158]],palette.ink,false,[[0,0],[-6,0],[-3,6]],[[3,6],[6,0],[0,0]],2.5)],{},head);
  add('Scarf',[rect(160,189,92,19,8,palette.green),curve([[151,197],[175,197],[171,222],[150,218]],palette.green)]);
  for(const side of [-1,1]){
    add(side<0?'Left paw':'Right paw',[
      ellipse(0,7,46,92,palette.furLight),ellipse(0,-13,19,25,palette.cream,false),
      ellipse(-9,-30,7,8,palette.cream,false),ellipse(0,-33,7,8,palette.cream,false),ellipse(9,-30,7,8,palette.cream,false)
    ],{p:frames([[0,[160+side*58,210,0]],[120,[160+side*58,210,0]],[126,[160+side*25,131,0]],[132,[160+side*58,210,0]]]),r:frames([[0,side*22],[120,side*22],[126,side*15],[132,side*22]])});
  }
  const data=finish();data.markers=[{tm:0,cm:'idle',dr:120},{tm:120,cm:'cover',dr:6},{tm:126,cm:'uncover',dr:6}];return data;
}

function book(loading=false){
  const {add,finish}=composition(loading?'Xuân Hoà · Mở sổ':'Xuân Hoà · Hành trình giáo lý',360,260,120);
  add('Ground',[ellipse(180,231,244,20,palette.mint,false)]);
  const anchor=add('Book float',null,{p:frames([[0,[0,0,0]],[60,[0,-7,0]],[120,[0,0,0]]])});
  add('Cover',[curve([[51,107],[173,123],[187,123],[309,107],[309,219],[190,229],[170,229],[51,219]],palette.green)],{},anchor);
  add('Left page',[curve([[57,86],[166,96],[180,109],[180,218],[165,207],[57,197]],palette.paper)],{},anchor);
  add('Right page',[curve([[180,109],[194,96],[303,86],[303,197],[195,207],[180,218]],palette.paper)],{},anchor);
  add('Spine',[curve([[180,109],[180,216]],palette.ink,false,undefined,undefined,2)],{},anchor);
  add('Bookmark',[curve([[269,89],[286,87],[286,138],[277,130],[269,138]],palette.gold)],{},anchor);
  add('Cross',[rect(112,133,12,57,3,palette.green,false),rect(112,121,40,12,3,palette.green,false)],{},anchor);
  add('Page lines',[
    curve([[79,173],[145,179]],palette.furLight,false),curve([[79,185],[145,191]],palette.furLight,false),
    curve([[214,139],[267,134]],palette.furLight,false),curve([[214,153],[276,147]],palette.furLight,false),curve([[214,167],[276,161]],palette.furLight,false),curve([[214,181],[260,177]],palette.furLight,false)
  ],{},anchor);
  const star=(x,y,r,c)=>curve([[x,y-r],[x+r*.28,y-r*.28],[x+r,y],[x+r*.28,y+r*.28],[x,y+r],[x-r*.28,y+r*.28],[x-r,y],[x-r*.28,y-r*.28]],c);
  add('Star left',[star(52,48,13,palette.gold)],{r:frames([[0,-8],[60,8],[120,-8]]),a:property([52,48,0]),p:property([52,48,0])});
  add('Star right',[star(304,49,10,palette.sky)],{p:frames([[0,[0,0,0]],[60,[0,5,0]],[120,[0,0,0]]])});
  add('Leaf',[curve([[166,61],[145,37],[151,20],[169,39]],palette.green)],{r:frames([[0,-6],[60,6],[120,-6]]),a:property([166,61,0]),p:property([166,61,0])});
  for(const [index,x] of [155,180,205].entries())add('Reading dot '+index,[ellipse(x,loading?249:60,7,7,palette.green,false)],{o:frames([[0,45],[20+index*12,100],[60+index*12,45],[120,45]])});
  return finish();
}

// Static SVG posters use the same geometry. They remain visible until Lottie
// loads, and provide a complete illustration when a script or JSON fails.
function interpolate(prop,t){
  if(!prop.a)return prop.k;
  const points=prop.k;let left=points[0],right=left;
  for(const point of points){if(point.t<=t)left=point;else {right=point;break;}}
  if(right.t<=left.t)return left.s;
  const f=(t-left.t)/(right.t-left.t);return left.s.map((v,i)=>v+(right.s[i]-v)*f);
}
function poster(data,t=0){
  const hex=c=>'#'+c.slice(0,3).map(x=>Math.round(x*255).toString(16).padStart(2,'0')).join('');
  const parents=new Map(data.layers.map(l=>[l.ind,l]));
  function layerTransform(layer){const p=interpolate(layer.ks.p,t),a=interpolate(layer.ks.a,t),s=interpolate(layer.ks.s,t),r=interpolate(layer.ks.r,t)[0]??interpolate(layer.ks.r,t);return `translate(${p[0]} ${p[1]}) rotate(${r}) scale(${s[0]/100} ${s[1]/100}) translate(${-a[0]} ${-a[1]})`;}
  const groups=data.layers.slice().reverse().filter(l=>l.ty===4).map(layer=>{
    const body=layer.shapes.slice().reverse().map(group=>{
      const shape=group.it[0],f=group.it.find(x=>x.ty==='fl'),s=group.it.find(x=>x.ty==='st');
      const attrs=`fill="${f?hex(f.c.k):'none'}" ${s?`stroke="${hex(s.c.k)}" stroke-width="${s.w.k}" stroke-linejoin="round" stroke-linecap="round"`:''}`;
      if(shape.ty==='el'){const [x,y]=shape.p.k,[w,h]=shape.s.k;return `<ellipse cx="${x}" cy="${y}" rx="${w/2}" ry="${h/2}" ${attrs}/>`;}
      if(shape.ty==='rc'){const [x,y]=shape.p.k,[w,h]=shape.s.k;return `<rect x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" rx="${shape.r.k}" ${attrs}/>`;}
      const v=shape.ks.k;let d=`M${v.v[0].join(' ')}`;
      const count=v.c?v.v.length+1:v.v.length;
      for(let n=1;n<count;n++){const prev=(n-1)%v.v.length,i=n%v.v.length,a=v.v[prev],b=v.v[i],o=v.o[prev],inside=v.i[i];d+=` C${a[0]+o[0]} ${a[1]+o[1]} ${b[0]+inside[0]} ${b[1]+inside[1]} ${b.join(' ')}`;}
      return `<path d="${d}${v.c?' Z':''}" ${attrs}/>`;
    }).join('');
    return `${layer.parent?`<g transform="${layerTransform(parents.get(layer.parent))}">`:''}<g transform="${layerTransform(layer)}">${body}</g>${layer.parent?'</g>':''}`;
  }).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${data.w} ${data.h}">${groups}</svg>`;
}

export function writeAnimations(destination='dist/assets/animations'){
  fs.mkdirSync(destination,{recursive:true});
  for(const [name,data] of [['bear-login',bear()],['loading-book',book(true)],['learning-book',book()]]){
    fs.writeFileSync(path.join(destination,name+'.json'),JSON.stringify(data));
    fs.writeFileSync(path.join(destination,name+'.svg'),poster(data));
    if(name==='bear-login')fs.writeFileSync(path.join(destination,'bear-covered.svg'),poster(data,126));
  }
}
