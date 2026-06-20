/**
 * ReportFlow — shared Bootstrap modal behavior (reset, Select2, deep links).
 */
(function (global) {
  'use strict';

  function getModalInstance(modalElement) {
    if (!modalElement || !global.bootstrap || !global.bootstrap.Modal) return null;
    return global.bootstrap.Modal.getInstance(modalElement) || new global.bootstrap.Modal(modalElement);
  }

  function dismissModalForElement(triggerElement) {
    if (!triggerElement || !triggerElement.closest) return;
    var modalElement = triggerElement.closest('.modal');
    if (!modalElement) return;
    var modalInstance = getModalInstance(modalElement);
    if (modalInstance) modalInstance.hide();
  }

  function resetModalForms(modal) {
    modal.querySelectorAll('form').forEach(function (form) {
      if (form.hasAttribute('data-rf-no-reset')) return;
      form.reset();
      form.querySelectorAll('.is-invalid').forEach(function (node) {
        node.classList.remove('is-invalid');
      });
      form.querySelectorAll('.invalid-feedback.d-block').forEach(function (node) {
        node.remove();
      });
      if (global.jQuery) {
        global.jQuery(form).find('.rf-select2').each(function () {
          if (global.jQuery(this).hasClass('select2-hidden-accessible')) {
            global.jQuery(this).val(null).trigger('change');
          }
        });
      }
    });
  }

  function initModalSelect2(modal) {
    if (global.ReportFlowTable && global.ReportFlowTable.initSelect2) {
      global.ReportFlowTable.initSelect2(modal);
    }
  }

  function getOpenModals() {
    return Array.prototype.slice
      .call(document.querySelectorAll('.modal.show'))
      .sort(function (a, b) {
        var zIndexA = parseInt(global.getComputedStyle(a).zIndex, 10) || 0;
        var zIndexB = parseInt(global.getComputedStyle(b).zIndex, 10) || 0;
        return zIndexA - zIndexB;
      });
  }

  /** Dim every open modal except the topmost (nested modal stacks). */
  function updateModalStackDimming() {
    document.querySelectorAll('.modal.rf-modal-stack-dimmed').forEach(function (modal) {
      modal.classList.remove('rf-modal-stack-dimmed');
    });

    var openModals = getOpenModals();
    if (openModals.length <= 1) {
      return;
    }

    openModals.slice(0, -1).forEach(function (modal) {
      modal.classList.add('rf-modal-stack-dimmed');
    });
  }

  function bindModalStackDimming() {
    document.addEventListener('shown.bs.modal', function () {
      updateModalStackDimming();
    });
    document.addEventListener('hidden.bs.modal', function () {
      global.setTimeout(updateModalStackDimming, 0);
    });
  }

  function bindModalLifecycle() {
    document.querySelectorAll('.modal').forEach(function (modal) {
      modal.addEventListener('shown.bs.modal', function () {
        initModalSelect2(modal);
      });
      modal.addEventListener('hidden.bs.modal', function () {
        resetModalForms(modal);
      });
    });
  }

  function openModal(modalId) {
    var modalElement = document.getElementById(modalId);
    if (!modalElement) return;
    getModalInstance(modalElement).show();
  }

  function openFromQuery() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('compose') === '1') openModal('composeMessageModal');
    if (params.get('ask') === '1') openModal('qaAskModal');
    if (params.get('add_user') === '1') openModal('userCreateModal');
    if (params.get('settings') === '1') openModal('systemSettingsModal');
    if (params.get('visitor_ask') === '1') openModal('visitorAskModal');
  }

  global.ReportFlowModals = {
    dismiss: dismissModalForElement,
    open: openModal,
  };

  document.addEventListener('DOMContentLoaded', function () {
    bindModalStackDimming();
    bindModalLifecycle();
    openFromQuery();
  });
})(window);
