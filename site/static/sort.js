// Click a column heading to sort. Numeric columns carry data-v so that "$1,234"
// sorts as a number rather than a string.
document.querySelectorAll('table.sortable thead th').forEach((th, i) => {
  th.tabIndex = 0;
  th.addEventListener('click', () => sortBy(th, i));
  th.addEventListener('keydown', e => { if (e.key === 'Enter') sortBy(th, i); });
});
function sortBy(th, i) {
  const table = th.closest('table');
  const tbody = table.tBodies[0];
  const asc = th.dataset.dir !== 'asc';
  table.querySelectorAll('th').forEach(h => { delete h.dataset.dir; h.removeAttribute('aria-sort'); });
  th.dataset.dir = asc ? 'asc' : 'desc';
  th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
  const val = tr => {
    const td = tr.cells[i];
    if (td.dataset.v !== undefined) return parseFloat(td.dataset.v) || 0;
    return td.textContent.trim().toLowerCase();
  };
  Array.from(tbody.rows)
    .sort((a, b) => { const x = val(a), y = val(b);
      return (x < y ? -1 : x > y ? 1 : 0) * (asc ? 1 : -1); })
    .forEach(tr => tbody.appendChild(tr));
}
