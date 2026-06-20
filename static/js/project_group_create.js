(function () {
  'use strict';

  var form = document.getElementById('projectGroupCreateForm');
  if (!form) return;

  var matesSelect = document.getElementById('projectMatesSelect');
  var matesHidden = document.getElementById('id_project_mate_ids');

  function initMatesSelect2() {
    if (!matesSelect || !window.jQuery || !window.jQuery.fn.select2) return;
    var $select = window.jQuery(matesSelect);
    if ($select.hasClass('select2-hidden-accessible')) {
      $select.select2('destroy');
    }
    $select.select2({
      placeholder: matesSelect.getAttribute('data-placeholder') || 'Search project mates…',
      allowClear: true,
      width: '100%',
      closeOnSelect: false,
    });
  }

  function setMateIdsFromSelect() {
    if (!matesSelect || !matesHidden) return;
    var values = [];
    if (window.jQuery && window.jQuery(matesSelect).hasClass('select2-hidden-accessible')) {
      values = window.jQuery(matesSelect).val() || [];
    } else {
      Array.prototype.forEach.call(matesSelect.selectedOptions, function (option) {
        values.push(option.value);
      });
    }
    matesHidden.value = values.join(',');
  }

  function showValidationToast(message) {
    if (window.ReportFlowToast) {
      window.ReportFlowToast.warning(message, { title: false });
    }
  }

  initMatesSelect2();

  form.addEventListener('submit', function (event) {
    setMateIdsFromSelect();
    if (!matesHidden.value.trim()) {
      event.preventDefault();
      showValidationToast('Select at least one project mate from your department.');
    }
  });
})();
