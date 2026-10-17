import {matchesSearch} from './ux-utils.js';

export function gradeValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  return typeof value === 'number' ? new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 1}).format(value) : String(value);
}
export function selectGradeRows(rows, {query = '', assessment = 'all', sort = 'roster'} = {}) {
  const selected = rows.filter(row => matchesSearch(`${row.code} ${row.name}`,query) &&
    (assessment === 'all' || (assessment === 'passed' ? row.assessment === 'ĐẠT' : assessment === 'failed' ? String(row.assessment || '').startsWith('KHÔNG ĐẠT') : !row.assessment)));
  return sort === 'rank' ? selected.sort((a,b) => (typeof a.yearRank === 'number' ? a.yearRank : Infinity) - (typeof b.yearRank === 'number' ? b.yearRank : Infinity) || a.rosterRow - b.rosterRow) : selected;
}
