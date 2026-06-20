/**
 * Department dropdowns with inline “Add department…” option for admin forms.
 */
(function () {
  'use strict';

  var ADD_DEPARTMENT_VALUE = '__add_department__';

  function getPreviousValue(selectEl) {
    return selectEl.dataset.rfDepartmentPrevious || '';
  }

  function setPreviousValue(selectEl, value) {
    selectEl.dataset.rfDepartmentPrevious = value || '';
  }

  function appendDepartmentOption(selectEl, departmentName) {
    if (!selectEl || !departmentName) {
      return;
    }

    var existing = Array.from(selectEl.options).some(function (option) {
      return option.value === departmentName;
    });
    if (existing) {
      return;
    }

    var addOption = selectEl.querySelector('option[value="' + ADD_DEPARTMENT_VALUE + '"]');
    var option = document.createElement('option');
    option.value = departmentName;
    option.textContent = departmentName;

    if (addOption) {
      selectEl.insertBefore(option, addOption);
    } else {
      selectEl.appendChild(option);
    }
  }

  function setSelectValue(selectEl, value) {
    if (!selectEl) {
      return;
    }
    selectEl.value = value || '';
    if (window.jQuery && jQuery(selectEl).hasClass('select2-hidden-accessible')) {
      jQuery(selectEl).val(selectEl.value).trigger('change');
    }
  }

  function bindDepartmentSelect(selectEl) {
    if (!selectEl || selectEl.dataset.rfDepartmentBound === 'true') {
      return;
    }
    selectEl.dataset.rfDepartmentBound = 'true';
    setPreviousValue(selectEl, selectEl.value || '');

    selectEl.addEventListener('focus', function () {
      setPreviousValue(selectEl, selectEl.value || '');
    });

    var onSelect = function (event) {
      var selectedValue = event.target.value;
      if (selectedValue !== ADD_DEPARTMENT_VALUE) {
        setPreviousValue(selectEl, selectedValue);
        return;
      }

      setSelectValue(selectEl, getPreviousValue(selectEl));
      var modalEl = document.getElementById('addDepartmentModal');
      if (!modalEl) {
        return;
      }
      modalEl.dataset.rfTargetSelectId = selectEl.id || '';
      if (window.bootstrap && bootstrap.Modal) {
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
      }
    };

    selectEl.addEventListener('change', onSelect);
    if (window.jQuery && jQuery.fn.select2) {
      jQuery(selectEl).on('select2:select', function (event) {
        if (event.params && event.params.data && event.params.data.id === ADD_DEPARTMENT_VALUE) {
          setSelectValue(selectEl, getPreviousValue(selectEl));
          var modalEl = document.getElementById('addDepartmentModal');
          if (modalEl) {
            modalEl.dataset.rfTargetSelectId = selectEl.id || '';
            bootstrap.Modal.getOrCreateInstance(modalEl).show();
          }
        } else if (event.params && event.params.data) {
          setPreviousValue(selectEl, event.params.data.id);
        }
      });
    }
  }

  function bindAllDepartmentSelects(root) {
    (root || document).querySelectorAll('[data-rf-department-select="true"]').forEach(bindDepartmentSelect);
  }

  function applyDepartmentToAllSelects(departmentName) {
    document.querySelectorAll('[data-rf-department-select="true"]').forEach(function (selectEl) {
      appendDepartmentOption(selectEl, departmentName);
    });
  }

  async function saveNewDepartment() {
    var nameInput = document.getElementById('addDepartmentName');
    var modalEl = document.getElementById('addDepartmentModal');
    var saveButton = document.getElementById('addDepartmentSaveBtn');
    if (!nameInput || !window.ReportFlowAPI) {
      return;
    }

    var departmentName = (nameInput.value || '').trim();
    if (!departmentName) {
      window.ReportFlowAPI.showToast('Enter a department name.', 'error');
      nameInput.focus();
      return;
    }

    if (window.ReportFlowLoader) {
      window.ReportFlowLoader.setButtonLoading(saveButton, true, 'Saving…');
    } else {
      saveButton.disabled = true;
    }
    try {
      var result = await window.ReportFlowAPI.apiFetch('/api/v1/departments/', {
        method: 'POST',
        body: JSON.stringify({ name: departmentName }),
      });
      var savedName = (result.data && result.data.name) || departmentName;
      applyDepartmentToAllSelects(savedName);

      var targetSelectId = modalEl ? modalEl.dataset.rfTargetSelectId : '';
      var targetSelect = targetSelectId ? document.getElementById(targetSelectId) : null;
      if (targetSelect) {
        setSelectValue(targetSelect, savedName);
        setPreviousValue(targetSelect, savedName);
        document.dispatchEvent(
          new CustomEvent('rf:department-changed', {
            detail: { department: savedName, selectId: targetSelectId },
          })
        );
      }

      if (window.bootstrap && bootstrap.Modal) {
        bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      }
      nameInput.value = '';
      window.ReportFlowAPI.showToast(result.message || 'Department added', 'success');
    } catch (error) {
      window.ReportFlowAPI.showToast(
        window.ReportFlowAPI.formatApiError(error, 'Could not add department'),
        'error'
      );
    } finally {
      if (window.ReportFlowLoader) {
        window.ReportFlowLoader.setButtonLoading(saveButton, false);
      } else {
        saveButton.disabled = false;
      }
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindAllDepartmentSelects();

    var saveButton = document.getElementById('addDepartmentSaveBtn');
    if (saveButton) {
      saveButton.addEventListener('click', saveNewDepartment);
    }

    var addDepartmentForm = document.getElementById('addDepartmentForm');
    if (addDepartmentForm) {
      addDepartmentForm.addEventListener('submit', function (event) {
        event.preventDefault();
        saveNewDepartment();
      });
    }

    var addDepartmentModal = document.getElementById('addDepartmentModal');
    if (addDepartmentModal) {
      addDepartmentModal.addEventListener('shown.bs.modal', function () {
        var nameInput = document.getElementById('addDepartmentName');
        if (nameInput) {
          nameInput.focus();
        }
      });
      addDepartmentModal.addEventListener('hidden.bs.modal', function () {
        var nameInput = document.getElementById('addDepartmentName');
        if (nameInput) {
          nameInput.value = '';
        }
      });
    }

    document.addEventListener('shown.bs.modal', function (event) {
      if (event.target) {
        bindAllDepartmentSelects(event.target);
      }
    });
  });

  window.ReportFlowDepartmentSelect = {
    bindAll: bindAllDepartmentSelects,
    appendOption: appendDepartmentOption,
  };
})();
