const activities=new Set(['mass','early','lesson']);

export function attendanceHistory(marks, code=null, month='all') {
  return Object.entries(marks).flatMap(([key,mark])=>{
    const [date,activity,studentId,...extra]=key.split('|');
    if(extra.length||!/^\d{4}-\d{2}-\d{2}$/.test(date)||!activities.has(activity)||!['X','P','O'].includes(mark?.status))return [];
    if(code!==null&&studentId!==code||month!=='all'&&!date.startsWith(month+'-'))return [];
    return [{date,activity,studentId,...mark}];
  }).sort((a,b)=>b.date.localeCompare(a.date)||a.activity.localeCompare(b.activity));
}

export function summarizeAttendance(people, marks, month='all') {
  const grouped=new Map();
  for(const entry of attendanceHistory(marks,null,month)){
    if(!grouped.has(entry.studentId))grouped.set(entry.studentId,[]);
    grouped.get(entry.studentId).push(entry);
  }
  return people.map(student=>{
    const history=grouped.get(student.id)||[];
    const count=(status,activity=null)=>history.filter(h=>h.status===status&&(!activity||h.activity===activity)).length;
    const presentCount=count('X'),totalSessions=history.length;
    const rawRatio=totalSessions?presentCount/totalSessions*100:null;
    const ratio=rawRatio===null?null:Math.round(rawRatio*10)/10;
    return {student,massCount:count('X','mass'),earlyCount:count('X','early'),lessonCount:count('X','lesson'),
      presentCount,permittedCount:count('P'),absentCount:count('O'),totalSessions,ratio,
      health:rawRatio===null?'none':rawRatio>=80?'good':rawRatio>=50?'warn':'danger'};
  });
}
