import {matchesSearch} from './ux-utils.js';

let activePopup=null;
if(typeof window!=='undefined'){
  const reposition=()=>activePopup?.position();
  window.addEventListener('resize',reposition,{passive:true});
  window.addEventListener('scroll',reposition,{passive:true,capture:true});
  window.visualViewport?.addEventListener('resize',reposition,{passive:true});
  window.visualViewport?.addEventListener('scroll',reposition,{passive:true});
}

// Keep focus in the text field so touch selection does not dismiss its keyboard.
export function attachStudentCombobox(input,{people,label='Gợi ý thiếu nhi',limit=8}={}){
  if(!input||input.dataset.comboboxReady)return;
  input.dataset.comboboxReady='true';
  input.removeAttribute('list');
  // Options live inside the visual field label; keep its accessible name stable.
  if(!input.hasAttribute('aria-label')&&!input.hasAttribute('aria-labelledby'))input.setAttribute('aria-label',[...input.labels||[]].map(el=>el.textContent.trim()).join(' ')||label);
  const host=document.createElement('span');host.className='student-combobox';
  input.before(host);host.append(input);
  host.closest('.card')?.classList.add('student-combobox-card');
  const list=document.createElement('span');list.id=input.id+'-options';list.className='student-options';
  list.setAttribute('role','listbox');list.setAttribute('aria-label',label);list.hidden=true;host.append(list);
  const status=document.createElement('span');status.className='sr-only';status.setAttribute('role','status');host.append(status);
  input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');
  input.setAttribute('aria-haspopup','listbox');input.setAttribute('aria-controls',list.id);input.setAttribute('aria-expanded','false');
  input.setAttribute('autocapitalize','none');input.setAttribute('spellcheck','false');
  let rows=[],active=-1,composing=false;
  let touchStart=null;
  function close(){list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;status.textContent='';if(activePopup?.input===input)activePopup=null;}
  function position(){
    if(!input.isConnected||list.hidden){close();return;}
    const rect=input.getBoundingClientRect(),viewport=window.visualViewport;
    const top=viewport?.offsetTop||0,bottom=top+(viewport?.height||innerHeight);
    const tabs=document.querySelector('.mobile-tabs'),tabTop=tabs?.getClientRects().length?tabs.getBoundingClientRect().top:bottom;
    const dialog=input.closest('dialog'),bounds=dialog?.getBoundingClientRect();
    const below=Math.max(0,Math.min(bottom,tabTop,bounds?.bottom??bottom)-rect.bottom-12);
    const above=Math.max(0,rect.top-Math.max(top,bounds?.top??top)-12);
    const upwards=below<180&&above>below;
    list.classList.toggle('student-options-above',upwards);
    list.style.maxHeight=Math.min(352,upwards?above:below)+'px';
  }
  function highlight(index){
    active=index;
    [...list.querySelectorAll('[role=option]')].forEach((option,n)=>option.setAttribute('aria-selected',String(n===active)));
    if(active<0){input.removeAttribute('aria-activedescendant');return;}
    const option=list.querySelectorAll('[role=option]')[active];input.setAttribute('aria-activedescendant',option.id);option.scrollIntoView({block:'nearest'});
  }
  function show(){
    const query=input.value.trim();if(!query||input.disabled){close();return;}
    const matches=people().filter(p=>matchesSearch(`${p.id} ${p.name} ${p.className}`,query));
    rows=matches.slice(0,limit);active=-1;input.removeAttribute('aria-activedescendant');list.replaceChildren();
    for(const [n,person] of rows.entries()){
      const option=document.createElement('span');option.id=list.id+'-'+n;option.className='student-option';
      option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.dataset.optionIndex=String(n);
      const name=document.createElement('strong');name.textContent=person.name;
      const detail=document.createElement('small');detail.textContent=`${person.id} · ${person.className}`;
      option.append(name,detail);list.append(option);
    }
    const hint=document.createElement('span');hint.className='student-options-hint';hint.setAttribute('role','presentation');
    hint.textContent=matches.length?matches.length>limit?`Hiện ${limit}/${matches.length} kết quả · Gõ thêm để thu hẹp`:'Chọn đúng em theo mã và lớp': 'Không tìm thấy · Thử tên không dấu hoặc mã thẻ';
    list.append(hint);list.hidden=false;input.setAttribute('aria-expanded','true');
    // Fit the popup above/below the field, including the mobile tab bar/keyboard.
    if(activePopup?.input!==input)activePopup?.close();
    activePopup={input,position,close};position();
    status.textContent=matches.length?`${matches.length} kết quả, hiển thị ${rows.length}. Dùng phím mũi tên để chọn.`:'Không tìm thấy thiếu nhi phù hợp.';
  }
  function choose(index){
    const person=rows[index];if(!person)return;input.value=person.id;
    input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));close();input.focus({preventScroll:true});
  }
  input.addEventListener('input',()=>{if(!composing)show();});
  input.addEventListener('focus',show);
  input.addEventListener('compositionstart',()=>{composing=true;close();});
  input.addEventListener('compositionend',()=>{composing=false;show();});
  input.addEventListener('blur',close);
  input.addEventListener('keydown',event=>{
    if(event.isComposing||composing)return;
    if(event.key==='Escape'&&!list.hidden){event.preventDefault();event.stopPropagation();close();return;}
    if(event.key==='Tab'){close();return;}
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();if(list.hidden)show();if(!rows.length)return;
      highlight(event.key==='ArrowDown'?(active+1)%rows.length:active<0?rows.length-1:(active-1+rows.length)%rows.length);return;
    }
    if(event.key==='Enter'&&!list.hidden&&active>=0){event.preventDefault();event.stopPropagation();choose(active);return;}
    if(event.key==='Enter')close();
  });
  // Click supports mouse, touch and synthesized assistive-technology activation.
  list.addEventListener('click',event=>{const option=event.target.closest('[data-option-index]');if(option){event.preventDefault();if(!list.hidden)choose(Number(option.dataset.optionIndex));}});
  // A touch blur happens before click; keep the popup until that click is handled.
  list.addEventListener('pointerdown',event=>{
    if(!event.target.closest('[data-option-index]'))return;
    touchStart=event.pointerType==='touch'?{x:event.clientX,y:event.clientY}:null;
    event.preventDefault();
  });
  list.addEventListener('pointerup',event=>{
    const option=event.target.closest('[data-option-index]');
    if(touchStart&&option&&Math.hypot(event.clientX-touchStart.x,event.clientY-touchStart.y)<10){event.preventDefault();choose(Number(option.dataset.optionIndex));}
    touchStart=null;
  });
  list.addEventListener('pointercancel',()=>{touchStart=null;});
  return {close};
}
