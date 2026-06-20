/**
 * ReportFlow — server-side filter forms auto-submit on change.
 * Forms containing .rf-filter-actions reload when any filter field changes.
 */
(function (global) {
  'use strict';

  var DEBOUNCE_MS = 450;
  var timers = new WeakMap();

  function findFilterForm(el) {
    if (!el || !el.closest) return null;
    var form = el.closest('form[method="get"]');
    if (!form || !form.querySelector('.rf-filter-actions')) return null;
    return form;
  }

  function isTextLikeInput(el) {
    if (!el || el.tagName !== 'INPUT') return false;
    var type = (el.getAttribute('type') || 'text').toLowerCase();
    return type === 'text' || type === 'search' || type === 'number' || type === 'email';
  }

  function submitFilterForm(form) {
    if (form._rfFilterSubmitting) return;
    form._rfFilterSubmitting = true;
    if (global.ReportFlowLoader) {
      global.ReportFlowLoader.show({
        message: 'Loading reports…',
        submessage: 'Applying filters…',
        immediate: true,
        delay: 0,
      });
    }
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit();
    } else {
      form.submit();
    }
  }

  function scheduleSubmit(form, debounceMs) {
    if (!form) return;
    var delay = debounceMs != null ? debounceMs : 50;
    var existing = timers.get(form);
    if (existing) clearTimeout(existing);

    timers.set(
      form,
      setTimeout(function () {
        timers.delete(form);
        submitFilterForm(form);
      }, delay)
    );
  }

  function bindEvents() {
    document.addEventListener('change', function (e) {
      var form = findFilterForm(e.target);
      if (!form) return;
      if (
        e.target.matches('select') ||
        e.target.matches('input[type="checkbox"]') ||
        e.target.matches('input[type="radio"]') ||
        e.target.matches('input[type="date"]')
      ) {
        scheduleSubmit(form, 50);
      }
    });

    document.addEventListener('input', function (e) {
      var form = findFilterForm(e.target);
      if (!form || !isTextLikeInput(e.target)) return;
      scheduleSubmit(form, DEBOUNCE_MS);
    });

    if (global.jQuery) {
      global.jQuery(document).on(
        'select2:select select2:clear change.rfFilter',
        'form[method="get"] select.rf-select2',
        function () {
          scheduleSubmit(findFilterForm(this), 50);
        }
      );
    }
  }

  global.ReportFlowFilters = {
    scheduleSubmit: scheduleSubmit,
    findFilterForm: findFilterForm,
  };

  document.addEventListener('DOMContentLoaded', bindEvents);
})(window);
