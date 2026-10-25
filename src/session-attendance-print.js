import {sessionStudentName} from './session-summary.js';

export function sessionAttendancePrintHtml({groups,earlyGroups=null,scope,date,activityLabel,year,title,closed=false},{esc}) {
  const section=(kind,label,entries)=>{
    const saved=entries.filter(({mark})=>mark?.status==='X');
    return `<section data-print-attendance="${kind}"><h2>${esc(label)} <span>(${saved.length} em)</span></h2>${saved.length?`<table><thead><tr><th scope="col">Mã số</th><th scope="col">Tên Thánh, họ và tên</th></tr></thead><tbody>${saved.map(({student})=>`<tr><td class="code">${esc(student.id)}</td><td>${esc(sessionStudentName(student)||'Chưa có tên')}<small>${esc(student.className||'')}</small></td></tr>`).join('')}</tbody></table>`:'<p>Chưa có kết quả có mặt đã lưu.</p>'}</section>`;
  };
  return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>
    @page{size:A4 portrait;margin:14mm}
    *{box-sizing:border-box}body{font:16px/1.5 Arial,sans-serif;color:#172c24;background:#fff;max-width:820px;margin:0 auto;padding:24px}
    .brand{font-weight:700;color:#155b3a;margin:0}h1{font-size:24px;line-height:1.3;margin:12px 0}h2{font-size:19px;break-after:avoid;margin:24px 0 10px}h2 span{font-weight:400}
    .meta,.note{overflow-wrap:anywhere}.note{color:#40554a}section{margin-top:20px}table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{text-align:left;vertical-align:top;padding:9px 10px;border-bottom:1px solid #b5c1ba;overflow-wrap:anywhere}th:first-child{width:105px}.code{font-variant-numeric:tabular-nums}small{display:block;font-size:13px;color:#40554a}thead{display:table-header-group}tr{break-inside:avoid}button{font:inherit;min-height:52px;padding:10px 20px;border:1px solid #155b3a;border-radius:8px;background:#155b3a;color:#fff;cursor:pointer}button:focus-visible{outline:3px solid #d59438;outline-offset:3px}button:disabled{opacity:.5}
    @media(max-width:480px){body{padding:16px}h1{font-size:21px}th,td{padding:8px 5px}th:first-child{width:85px}}
    @media print{body{max-width:none;padding:0;color:#000}.print-toolbar{display:none}h1{font-size:18pt}body{font-size:12pt}small{color:#333}thead{display:table-header-group}}
    </style></head><body><div class="print-toolbar"><button type="button" id="print" disabled>In / Lưu PDF</button></div><header><p class="brand">Giáo xứ Xuân Hoà</p><h1>${esc(title)}</h1><p class="meta">${esc(scope)} · ${esc(date)} · ${esc(activityLabel)}${year?' · Năm học '+esc(year):''}</p><p class="report-state">${closed?'Buổi đã chốt.':'Buổi đang mở · Kết quả đã lưu đến thời điểm in.'}</p></header>
    ${section('present',activityLabel,groups.present)}${earlyGroups?section('early','Đi lễ sớm',earlyGroups.present):''}
    ${earlyGroups?'<p class="note">Thánh lễ và lễ sớm được thống kê riêng; một em có thể xuất hiện ở cả hai mục.</p>':''}
    </body></html>`;
}
