(function () {
  'use strict';

  var rejectModal = document.getElementById('listRejectModal');
  var deleteModal = document.getElementById('listDeleteModal');
  if (rejectModal) {
    rejectModal.addEventListener('show.bs.modal', function (e) {
      var btn = e.relatedTarget;
      if (!btn) return;
      var url = btn.getAttribute('data-reject-url') || '';
      var form = rejectModal.querySelector('form');
      if (form && url) {
        form.setAttribute('action', url);
        var apiUrl = url.indexOf('admin-reject') !== -1
          ? url.replace('/reports/', '/api/v1/reports/').replace('/admin-reject/', '/admin-reject/')
          : url.replace('/reports/', '/api/v1/reports/').replace('/teacher-reject/', '/teacher-reject/');
        form.setAttribute('data-api-url', apiUrl);
      }
    });
  }
  if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (e) {
      var btn = e.relatedTarget;
      if (!btn) return;
      var url = btn.getAttribute('data-delete-url') || '';
      var form = deleteModal.querySelector('form');
      if (form && url) {
        form.setAttribute('action', url);
        form.setAttribute('data-api-url', url.replace('/reports/', '/api/v1/reports/').replace('/delete/', '/delete/'));
      }
    });
  }
  var selectAll = document.getElementById('selectAllReports');
  var bulkForm = document.getElementById('bulkReportsForm');
  var bulkIds = document.getElementById('bulkReportIds');
  var bulkAction = document.getElementById('bulkReportAction');
  var approveBtn = document.getElementById('bulkApproveBtn');
  var rejectBtn = document.getElementById('bulkRejectBtn');
  function selectedIds() {
    var boxes = document.querySelectorAll('.report-bulk-cb:checked');
    return Array.prototype.map.call(boxes, function (b) { return parseInt(b.value, 10); });
  }
  if (selectAll) {
    selectAll.addEventListener('change', function () {
      document.querySelectorAll('.report-bulk-cb').forEach(function (cb) {
        cb.checked = selectAll.checked;
      });
    });
  }
  function submitBulk(action) {
    var ids = selectedIds();
    if (!ids.length) {
      window.ReportFlowToast.warning('Select at least one report.');
      return;
    }
    var reason = '';
    if (action === 'reject') {
      reason = window.prompt('Reason for bulk rejection (optional):') || 'Bulk rejection';
    }
    if (!window.ReportFlowAPI) {
      if (bulkForm && bulkIds && bulkAction) {
        bulkIds.value = ids.join(',');
        bulkAction.value = action;
        bulkForm.submit();
      }
      return;
    }

    if (window.ReportFlowLoader) {
      window.ReportFlowLoader.setButtonLoading(
        action === 'approve' ? approveBtn : rejectBtn,
        true,
        'Processing reports…'
      );
    }

    window.ReportFlowAPI.apiFetch('/api/v1/reports/bulk-action/', {
      method: 'POST',
      body: JSON.stringify({
        report_ids: ids,
        action: action,
        reason: reason,
      }),
      loaderMessage: 'Processing reports…',
      loaderSubmessage: 'Please wait.',
      loaderImmediate: true,
    }).then(function (result) {
      window.ReportFlowAPI.showToast(result.message || 'Bulk action completed', 'success');
      window.location.reload();
    }).catch(function (err) {
      var msg = window.ReportFlowAPI.formatApiError
        ? window.ReportFlowAPI.formatApiError(err, 'Bulk action failed')
        : ((err.payload && err.payload.message) || err.message || 'Bulk action failed');
      window.ReportFlowAPI.showToast(msg, 'error');
    }).finally(function () {
      if (window.ReportFlowLoader) {
        window.ReportFlowLoader.setButtonLoading(approveBtn, false);
        window.ReportFlowLoader.setButtonLoading(rejectBtn, false);
      }
    });
  }
  if (approveBtn) approveBtn.addEventListener('click', function () { submitBulk('approve'); });
  if (rejectBtn) rejectBtn.addEventListener('click', function () { submitBulk('reject'); });
})();
