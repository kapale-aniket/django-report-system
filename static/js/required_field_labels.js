/**
 * Append * to labels for required form fields (static HTML + Django widgets).
 */
(function (global) {
  'use strict';

  function labelIsOptional(label) {
    if (!label) return false;
    var text = (label.textContent || '').toLowerCase();
    return text.indexOf('optional') !== -1;
  }

  function hasRequiredMark(label) {
    return !!(label && label.querySelector('.rf-required-mark'));
  }

  function appendRequiredMark(label) {
    if (!label || hasRequiredMark(label) || labelIsOptional(label)) {
      return;
    }
    var mark = document.createElement('span');
    mark.className = 'rf-required-mark text-danger';
    mark.setAttribute('aria-hidden', 'true');
    mark.textContent = ' *';
    label.appendChild(mark);
  }

  function markLabelForControl(control, root) {
    if (!control || !control.id) {
      return;
    }
    if (control.type === 'checkbox' || control.type === 'radio' || control.type === 'hidden') {
      return;
    }
    var label = (root || document).querySelector('label[for="' + CSS.escape(control.id) + '"]');
    appendRequiredMark(label);
  }

  function markRequiredLabels(root) {
    root = root || document;
    root.querySelectorAll('input[required], select[required], textarea[required]').forEach(function (control) {
      markLabelForControl(control, root);
    });
    root.querySelectorAll('[data-rf-required="true"]').forEach(function (control) {
      markLabelForControl(control, root);
    });
    root.querySelectorAll('label[data-rf-required="true"]').forEach(function (label) {
      appendRequiredMark(label);
    });
  }

  global.ReportFlowRequiredLabels = {
    mark: markRequiredLabels,
  };

  document.addEventListener('DOMContentLoaded', function () {
    markRequiredLabels();
  });

  document.addEventListener('shown.bs.modal', function (event) {
    if (event.target) {
      markRequiredLabels(event.target);
    }
  });
})(window);
