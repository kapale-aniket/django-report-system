/**
 * ReportFlow — centralized tables: Select2, client search/sort/pagination (10 rows).
 */
(function (global) {
  'use strict';

  var DEFAULT_PAGE_SIZE = 10;

  function initSelect2(root) {
    if (!global.jQuery || !global.jQuery.fn.select2) return;
    var scope = root || document;
    scope.querySelectorAll('.rf-select2').forEach(function (el) {
      if (global.jQuery(el).hasClass('select2-hidden-accessible')) return;
      global.jQuery(el).select2({
        width: '100%',
        placeholder: el.getAttribute('data-placeholder') || undefined,
        allowClear: el.getAttribute('data-rf-select2-clear') === 'true',
        minimumResultsForSearch: el.getAttribute('data-rf-select2-search') === 'false' ? Infinity : 0,
        dropdownParent: el.closest('.modal') ? global.jQuery(el.closest('.modal')) : global.jQuery(document.body),
      });
    });
  }

  function buildClientToolbar(panel, columns) {
    var toolbar = document.createElement('div');
    toolbar.className = 'rf-table-toolbar app-card mb-3';
    toolbar.innerHTML =
      '<div class="app-card-body py-3">' +
      '<div class="row g-2 align-items-end">' +
      '<div class="col-md-5 col-lg-4">' +
      '<label class="form-label small fw-semibold text-muted mb-1">Search</label>' +
      '<input type="search" class="form-control rounded-3 rf-table-search" placeholder="Search this table…" autocomplete="off">' +
      '</div>' +
      '<div class="col-md-4 col-lg-3">' +
      '<label class="form-label small fw-semibold text-muted mb-1">Sort by</label>' +
      '<select class="form-select rounded-3 rf-select2 rf-table-sort-col" data-rf-select2-search="false"></select>' +
      '</div>' +
      '<div class="col-md-3 col-lg-2">' +
      '<label class="form-label small fw-semibold text-muted mb-1">Order</label>' +
      '<select class="form-select rounded-3 rf-select2 rf-table-sort-dir" data-rf-select2-search="false">' +
      '<option value="asc">Ascending</option>' +
      '<option value="desc">Descending</option>' +
      '</select>' +
      '</div>' +
      '<div class="col-md-2 col-lg-2 d-flex align-items-end">' +
      '<button type="button" class="btn btn-outline-secondary rounded-3 w-100 rf-table-clear">Clear</button>' +
      '</div>' +
      '</div></div>';

    var sortCol = toolbar.querySelector('.rf-table-sort-col');
    columns.forEach(function (col, index) {
      var opt = document.createElement('option');
      opt.value = String(index);
      opt.textContent = col.label;
      sortCol.appendChild(opt);
    });

    panel.insertBefore(toolbar, panel.firstChild);
    return toolbar;
  }

  function buildClientFooter(panel) {
    var footer = document.createElement('nav');
    footer.className = 'rf-table-pagination mt-3';
    footer.setAttribute('aria-label', 'Table pagination');
    footer.innerHTML =
      '<div class="d-flex flex-wrap justify-content-between align-items-center gap-2">' +
      '<p class="small text-muted mb-0 rf-table-page-info"></p>' +
      '<ul class="pagination mb-0 rf-table-pages"></ul>' +
      '</div>';
    panel.appendChild(footer);
    return footer;
  }

  function cellText(row, index) {
    var cell = row.cells[index];
    return cell ? (cell.textContent || '').trim().toLowerCase() : '';
  }

  function initClientTable(panel) {
    var table = panel.querySelector('table');
    if (!table || !table.tBodies.length) return;

    var tbody = table.tBodies[0];
    var allRows = Array.from(tbody.querySelectorAll('tr')).filter(function (tr) {
      return !tr.querySelector('td[colspan]');
    });
    if (!allRows.length) return;

    var headers = Array.from(table.querySelectorAll('thead th'));
    var columns = headers.map(function (th, index) {
      return {
        index: index,
        label: (th.getAttribute('data-rf-label') || th.textContent || 'Column ' + (index + 1)).trim(),
      };
    });

    var pageSize = parseInt(panel.getAttribute('data-rf-page-size') || DEFAULT_PAGE_SIZE, 10);
    var state = {
      page: 1,
      search: '',
      sortCol: 0,
      sortDir: 'asc',
      filtered: allRows.slice(),
    };

    buildClientToolbar(panel, columns);
    var footer = buildClientFooter(panel);
    var searchInput = panel.querySelector('.rf-table-search');
    var sortColSelect = panel.querySelector('.rf-table-sort-col');
    var sortDirSelect = panel.querySelector('.rf-table-sort-dir');
    var clearBtn = panel.querySelector('.rf-table-clear');
    var pageInfo = footer.querySelector('.rf-table-page-info');
    var pagesUl = footer.querySelector('.rf-table-pages');

    initSelect2(panel);

    function applyFilterSort() {
      var searchQuery = state.search;
      state.filtered = allRows.filter(function (row) {
        if (!searchQuery) return true;
        return Array.from(row.cells).some(function (cell) {
          return (cell.textContent || '').toLowerCase().indexOf(searchQuery) !== -1;
        });
      });

      var columnIndex = state.sortCol;
      var sortDirection = state.sortDir === 'desc' ? -1 : 1;
      state.filtered.sort(function (rowA, rowB) {
        var valueA = cellText(rowA, columnIndex);
        var valueB = cellText(rowB, columnIndex);
        if (valueA < valueB) return -1 * sortDirection;
        if (valueA > valueB) return 1 * sortDirection;
        return 0;
      });
    }

    function renderPage() {
      applyFilterSort();
      var total = state.filtered.length;
      var totalPages = Math.max(1, Math.ceil(total / pageSize));
      if (state.page > totalPages) state.page = totalPages;
      if (state.page < 1) state.page = 1;

      allRows.forEach(function (row) {
        row.style.display = 'none';
      });
      var start = (state.page - 1) * pageSize;
      var end = Math.min(start + pageSize, total);
      state.filtered.slice(start, end).forEach(function (row) {
        row.style.display = '';
      });

      pageInfo.textContent =
        'Page ' +
        state.page +
        ' of ' +
        totalPages +
        ' page' +
        (totalPages === 1 ? '' : 's') +
        (total ? ' · Showing ' + (start + 1) + '–' + end + ' of ' + total : '');

      pagesUl.innerHTML = '';
      if (totalPages <= 1) return;

      function addItem(label, page, disabled, active) {
        var li = document.createElement('li');
        li.className = 'page-item' + (disabled ? ' disabled' : '') + (active ? ' active' : '');
        var a = document.createElement('button');
        a.type = 'button';
        a.className = 'page-link';
        a.textContent = label;
        if (!disabled && !active) {
          a.addEventListener('click', function () {
            state.page = page;
            renderPage();
          });
        }
        li.appendChild(a);
        pagesUl.appendChild(li);
      }

      addItem('Previous', state.page - 1, state.page <= 1, false);
      addItem(String(state.page), state.page, false, true);
      addItem('Next', state.page + 1, state.page >= totalPages, false);
    }

    searchInput.addEventListener('input', function () {
      state.search = (searchInput.value || '').trim().toLowerCase();
      state.page = 1;
      renderPage();
    });

    sortColSelect.addEventListener('change', function () {
      state.sortCol = parseInt(sortColSelect.value, 10) || 0;
      renderPage();
    });

    sortDirSelect.addEventListener('change', function () {
      state.sortDir = sortDirSelect.value;
      renderPage();
    });

    global.jQuery(sortColSelect).on('change', function () {
      state.sortCol = parseInt(sortColSelect.value, 10) || 0;
      renderPage();
    });
    global.jQuery(sortDirSelect).on('change', function () {
      state.sortDir = sortDirSelect.value;
      renderPage();
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        state.search = '';
        state.sortCol = 0;
        state.sortDir = 'asc';
        state.page = 1;
        searchInput.value = '';
        sortColSelect.value = '0';
        sortDirSelect.value = 'asc';
        if (global.jQuery) {
          global.jQuery(sortColSelect).val('0').trigger('change.select2');
          global.jQuery(sortDirSelect).val('asc').trigger('change.select2');
        }
        renderPage();
      });
    }

    renderPage();
  }

  function initAll(root) {
    initSelect2(root);
    var scope = root || document;
    scope.querySelectorAll('[data-rf-table="client"]').forEach(initClientTable);
  }

  global.ReportFlowTable = {
    initAll: initAll,
    initSelect2: initSelect2,
    PAGE_SIZE: DEFAULT_PAGE_SIZE,
  };

  document.addEventListener('DOMContentLoaded', function () {
    initAll(document);
  });
})(window);
