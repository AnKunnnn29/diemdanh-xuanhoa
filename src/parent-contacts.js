// Keep the workbook's existing columns while giving each name and number its own UI field.
const text=value=>String(value??'').trim();

export function parentNames(value){
  const raw=text(value),result={fatherName:'',motherName:'',guardianName:''};
  const tags=[...raw.matchAll(/(?:^|[;\n]\s*|\s+)(Cha|Bố|Ba|Mẹ|Má|Phụ huynh)\s*:\s*/giu)];
  if(!tags.length){result.guardianName=raw;return result;}
  const unknown=[raw.slice(0,tags[0].index).replace(/[;\s]+$/u,'')].filter(Boolean);
  tags.forEach((match,index)=>{
    const name=raw.slice(match.index+match[0].length,tags[index+1]?.index??raw.length).replace(/[;\s]+$/u,'').trim();
    const key=/^(cha|bố|ba)$/iu.test(match[1])?'fatherName':/^(mẹ|má)$/iu.test(match[1])?'motherName':'guardianName';
    if(key==='guardianName')unknown.push(name);else result[key]=[result[key],name].filter(Boolean).join('; ');
  });
  result.guardianName=unknown.filter(Boolean).join('; ');return result;
}

// Split only complete, recognizable numbers; keep ambiguous source text for manual review.
function splitDigits(value){
  if(!value)return [];
  for(const [prefix,length] of [['+84',12],['0084',13],['84',11],['0',10]]){
    if(!value.startsWith(prefix)||value.length<length)continue;
    const number=value.slice(0,length);
    if(!/^\+?\d+$/u.test(number))continue;
    const rest=splitDigits(value.slice(length));if(rest)return [number,...rest];
  }
  if(/^[1-9]\d{8}$/u.test(value)||/^01\d{9}$/u.test(value)||/^\+\d{8,15}$/u.test(value))return [value];
  return null;
}
export function parentPhones(value){
  const phones=[],notes=[];
  for(const part of text(value).split(/[;,/|\n]+/u).map(text).filter(Boolean)){
    const plain=part.replace(/^(?:sđt|sdt|đt|điện thoại|số điện thoại)(?:\s+phụ huynh)?(?:\s+\d+)?\s*:\s*/iu,'');
    const numbers=/^[+\d\s().-]+$/u.test(plain)?splitDigits(plain.replace(/[\s().-]/gu,'')):null;
    if(numbers)phones.push(...numbers);else notes.push(part);
  }
  return {phones:[...new Set(phones)],phoneNote:notes.join('; ')};
}
function displayPhone(number){
  if(/^0\d{9}$/u.test(number))return `${number.slice(0,4)} ${number.slice(4,7)} ${number.slice(7)}`;
  if(/^\+84\d{9}$/u.test(number))return `+84 ${number.slice(3,6)} ${number.slice(6,9)} ${number.slice(9)}`;
  return number;
}
export function contactFields(student,{esc,helpId='parent-contact-help'}){
  const names=parentNames(student.parents),{phones,phoneNote}=parentPhones(student.phone);
  return `<label class="field">Tên cha<input name="fatherName" maxlength="200" value="${esc(names.fatherName)}" autocomplete="off"></label>
    <label class="field">Tên mẹ<input name="motherName" maxlength="200" value="${esc(names.motherName)}" autocomplete="off"></label>
    <label class="field">Tên phụ huynh<input name="guardianName" value="${esc(names.guardianName)}" aria-describedby="${esc(helpId)}"></label>
    ${Array.from({length:Math.max(2,phones.length)},(_,index)=>`<label class="field">SĐT phụ huynh ${index+1}<input type="tel" name="parentPhone${index+1}" value="${esc(phones[index]||'')}" autocomplete="off" aria-describedby="${esc(helpId)}"></label>`).join('')}
    ${phoneNote?`<label class="field">Liên hệ chưa tách được<input name="parentPhoneNote" value="${esc(phoneNote)}" aria-describedby="${esc(helpId)}"></label>`:''}
    <p id="${esc(helpId)}" class="field-help parent-contact-help">Mỗi ô SĐT nhập một số. Số 1, 2 theo thứ tự liên hệ, chưa xác định là của cha hay mẹ.</p>`;
}
export function encodeContactFields(values){
  const result={...values};
  const nameKeys=['fatherName','motherName','guardianName'];
  if(nameKeys.some(key=>key in result)){
    result.parents=nameKeys.map((key,index)=>text(result[key])?`${['Cha','Mẹ','Phụ huynh'][index]}: ${text(result[key])}`:'').filter(Boolean).join('; ');
    nameKeys.forEach(key=>delete result[key]);
  }
  const phoneKeys=Object.keys(result).filter(key=>/^parentPhone\d+$/u.test(key)).sort((a,b)=>Number(a.slice(11))-Number(b.slice(11)));
  if(phoneKeys.length){
    const phones=phoneKeys.map(key=>{
      if(!text(result[key]))return '';
      const parsed=parentPhones(result[key]);
      if(parsed.phones.length!==1||parsed.phoneNote)throw new Error('Mỗi ô SĐT phụ huynh cần một số điện thoại. Kiểm tra lại số vừa nhập.');
      return parsed.phones[0];
    });
    result.phone=[...phones,text(result.parentPhoneNote)].filter(Boolean).join('; ');
    phoneKeys.forEach(key=>delete result[key]);delete result.parentPhoneNote;
  }
  return result;
}
export function parentContactMarkup(student,{esc,icon='',names=true}){
  const family=parentNames(student.parents),{phones,phoneNote}=parentPhones(student.phone);
  const entries=names?[['Tên cha',family.fatherName],['Tên mẹ',family.motherName],['Phụ huynh',family.guardianName]].filter(([,value])=>value):[];
  if(!entries.length&&!phones.length&&!phoneNote)return '<span class="text-slate-400">—</span>';
  return `<div class="parent-contacts">${entries.map(([label,value])=>`<div class="parent-contact parent-contact-name"><small>${label}</small><span>${esc(value)}</span></div>`).join('')}
    ${phones.map((number,index)=>`<div class="parent-contact"><small>SĐT phụ huynh ${index+1}</small><a href="tel:${esc(number)}" class="phone-action" aria-label="${esc(`Gọi phụ huynh ${index+1} của ${student.fullName||student.name||'thiếu nhi'}: ${number}`)}">${icon}<span>${esc(displayPhone(number))}</span></a></div>`).join('')}
    ${phoneNote?`<div class="parent-contact parent-contact-note"><small>Liên hệ chưa tách được</small><span>${esc(phoneNote)}</span></div>`:''}</div>`;
}
