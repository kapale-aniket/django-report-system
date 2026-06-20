(function () {
  'use strict';

  var form = document.getElementById('reportSubmitForm');
  if (!form) return;

  var groupBlock = document.getElementById('groupSelectBlock');
  var groupSelect = form.querySelector('[name="project_group_id"]');

  function selectedSubmissionType() {
    var checked = form.querySelector('input[name="submission_type"]:checked');
    return checked ? checked.value : 'individual';
  }

  function toggleGroupBlock() {
    if (!groupBlock) return;
    var isGroup = selectedSubmissionType() === 'group';
    groupBlock.style.display = isGroup ? '' : 'none';
    if (groupSelect) {
      groupSelect.required = isGroup;
      if (!isGroup) {
        groupSelect.value = '';
      }
    }
  }

  Array.prototype.forEach.call(form.querySelectorAll('input[name="submission_type"]'), function (radio) {
    radio.addEventListener('change', toggleGroupBlock);
  });

  toggleGroupBlock();
})();
