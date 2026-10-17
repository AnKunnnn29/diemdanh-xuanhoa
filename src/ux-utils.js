export const normalizeSearch = value => String(value ?? '').normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '').replace(/[đĐ]/g, 'd').toLowerCase().trim();

export function matchesSearch(value, query) {
  return normalizeSearch(query).split(/\s+/).filter(Boolean)
    .every(part => normalizeSearch(value).includes(part));
}

export const gradeFields = [
  ['kt15', 'Kiểm tra 15 phút'], ['kt1Tiet', 'Kiểm tra 1 tiết'],
  ['thiKinh', 'Thi kinh'], ['thiHk', 'Thi học kỳ'],
  ...Array.from({length:20}, (_, index) => ['kb_'+index, 'Khảo bài '+(index+1)])
];
export const scorePattern = 'P|p|(?:10(?:[.,]0+)?|[0-9](?:[.,][0-9]+)?)';
export const scoreValue = (student, kind) => kind.startsWith('kb_')
  ? student.khaoBai?.[Number(kind.slice(3))] : student[kind];
export const normalizedScore = value => {
  const text = String(value ?? '').trim();
  return text === '' ? null : text.toUpperCase() === 'P' ? 'P' : Number(text.replace(',', '.'));
};

export function gradesMatch(book, changes) {
  return changes.every(change=>{
    const student=book.students.find(s=>s.code===change.code);
    return student&&Object.entries(change).every(([field,value])=>field==='code'||(field==='khaoBai'
      ? value.every((score,index)=>normalizedScore(score)===normalizedScore(student.khaoBai?.[index]))
      : normalizedScore(value)===normalizedScore(student[field])));
  });
}

export function dailyWork({students, requests=[], sessions=[], careNotes=[], className='', date}) {
  const people=students.filter(s=>!className||className==='all'||s.className===className);
  const codes=new Set(people.map(s=>s.id));
  return {
    pending: requests.filter(r=>codes.has(r.code)&&r.status==='pending').length,
    makeups: requests.filter(r=>codes.has(r.code)&&r.kind==='makeup'&&r.status==='approved'&&
      (r.exception_day||r.effective_target_day||r.target_day)<=date).length,
    care: careNotes.filter(n=>codes.has(n.code)&&n.status!=='done'&&n.due_day&&n.due_day<=date).length,
    sessions: sessions.filter(s=>s.date===date&&!s.closed&&
      (!className||className==='all'||s.scope===className||s.scope==='all'))
  };
}
