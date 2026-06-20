/**
 * Create-user form: role-based teacher assignment and inline teacher creation.
 */
(function () {
  'use strict';

  var ADD_DEPARTMENT_VALUE = '__add_department__';
  var ADD_TEACHER_VALUE = '__add_teacher__';
  var ADD_TEACHER_LABEL = '+ Add teacher…';
  var STUDENT_ROLE = 'student';
  var TEACHER_ROLE = 'teacher';

  function getRoleSelect() {
    return document.getElementById('userCreateRole');
  }

  function getDepartmentSelect() {
    return document.getElementById('userCreateDepartment');
  }

  function getTeacherSelect() {
    return document.getElementById('userCreateAssignedTeacher');
  }

  function getTeacherWrap() {
    var selectEl = getTeacherSelect();
    return selectEl ? selectEl.closest('.user-create-teacher-field') : null;
  }

  function getPreviousTeacherValue(selectEl) {
    return selectEl ? selectEl.dataset.rfTeacherPrevious || '' : '';
  }

  function setPreviousTeacherValue(selectEl, value) {
    if (selectEl) {
      selectEl.dataset.rfTeacherPrevious = value || '';
    }
  }

  function getSelectedDepartment() {
    var departmentSelect = getDepartmentSelect();
    if (!departmentSelect) {
      return '';
    }
    var value = (departmentSelect.value || '').trim();
    if (!value || value === ADD_DEPARTMENT_VALUE) {
      return '';
    }
    return value;
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

  function teacherLabel(teacher) {
    var fullName = (teacher.full_name || '').trim();
    var username = (teacher.username || '').trim();
    if (fullName && username && fullName !== username) {
      return fullName + ' · ' + username;
    }
    return fullName || username || 'Teacher';
  }

  function rebuildTeacherOptions(selectEl, teachers, selectedValue) {
    if (!selectEl) {
      return;
    }

    var previousValue = selectedValue || getPreviousTeacherValue(selectEl) || '';
    selectEl.innerHTML = '';

    var emptyOption = document.createElement('option');
    emptyOption.value = '';
    emptyOption.textContent = '— None —';
    selectEl.appendChild(emptyOption);

    teachers.forEach(function (teacher) {
      var option = document.createElement('option');
      option.value = String(teacher.id);
      option.textContent = teacherLabel(teacher);
      selectEl.appendChild(option);
    });

    var addOption = document.createElement('option');
    addOption.value = ADD_TEACHER_VALUE;
    addOption.textContent = ADD_TEACHER_LABEL;
    selectEl.appendChild(addOption);

    var nextValue = '';
    if (previousValue && previousValue !== ADD_TEACHER_VALUE) {
      nextValue = Array.from(selectEl.options).some(function (option) {
        return option.value === previousValue;
      })
        ? previousValue
        : '';
    }
    setSelectValue(selectEl, nextValue);
    setPreviousTeacherValue(selectEl, nextValue);
  }

  function setTeacherPlaceholder(message) {
    var selectEl = getTeacherSelect();
    if (!selectEl) {
      return;
    }
    selectEl.innerHTML = '';
    var option = document.createElement('option');
    option.value = '';
    option.textContent = message;
    selectEl.appendChild(option);
    setSelectValue(selectEl, '');
    setPreviousTeacherValue(selectEl, '');
  }

  async function loadTeachersForDepartment(department, selectedValue) {
    var selectEl = getTeacherSelect();
    if (!selectEl || !window.ReportFlowAPI) {
      return;
    }

    if (!department) {
      setTeacherPlaceholder('Select department first…');
      return;
    }

    selectEl.disabled = true;
    setTeacherPlaceholder('Loading teachers…');
    try {
      var result = await window.ReportFlowAPI.apiFetch(
        '/api/v1/teachers/?department=' + encodeURIComponent(department)
      );
      rebuildTeacherOptions(selectEl, result.data || [], selectedValue);
    } catch (error) {
      setTeacherPlaceholder('Could not load teachers');
      window.ReportFlowAPI.showToast(
        window.ReportFlowAPI.formatApiError(error, 'Could not load teachers for this department'),
        'error'
      );
    } finally {
      selectEl.disabled = false;
      if (window.ReportFlowTable && window.ReportFlowTable.initSelect2) {
        window.ReportFlowTable.initSelect2(selectEl.closest('.modal') || document);
      }
    }
  }

  function updateTeacherFieldVisibility() {
    var roleSelect = getRoleSelect();
    var wrap = getTeacherWrap();
    if (!roleSelect || !wrap) {
      return;
    }

    var isStudent = roleSelect.value === STUDENT_ROLE;
    wrap.classList.toggle('d-none', !isStudent);

    if (!isStudent) {
      setSelectValue(getTeacherSelect(), '');
      setPreviousTeacherValue(getTeacherSelect(), '');
      return;
    }

    var department = getSelectedDepartment();
    if (department) {
      loadTeachersForDepartment(department);
    } else {
      setTeacherPlaceholder('Select department first…');
    }
  }

  function openAddTeacherModal() {
    var department = getSelectedDepartment();
    if (!department) {
      window.ReportFlowAPI.showToast('Select a department for the student first.', 'error');
      return;
    }

    var departmentInput = document.getElementById('addTeacherDepartment');
    if (departmentInput) {
      departmentInput.value = department;
    }

    var modalEl = document.getElementById('addTeacherModal');
    if (modalEl && window.bootstrap && bootstrap.Modal) {
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
  }

  function bindTeacherSelect(selectEl) {
    if (!selectEl || selectEl.dataset.rfTeacherBound === 'true') {
      return;
    }
    selectEl.dataset.rfTeacherBound = 'true';
    setPreviousTeacherValue(selectEl, selectEl.value || '');

    selectEl.addEventListener('focus', function () {
      setPreviousTeacherValue(selectEl, selectEl.value || '');
    });

    var onSelect = function (event) {
      var selectedValue = event.target.value;
      if (selectedValue !== ADD_TEACHER_VALUE) {
        setPreviousTeacherValue(selectEl, selectedValue);
        return;
      }

      setSelectValue(selectEl, getPreviousTeacherValue(selectEl));
      openAddTeacherModal();
    };

    selectEl.addEventListener('change', onSelect);

    if (window.jQuery && jQuery.fn.select2) {
      jQuery(selectEl).on('select2:select', function (event) {
        if (event.params && event.params.data && event.params.data.id === ADD_TEACHER_VALUE) {
          setSelectValue(selectEl, getPreviousTeacherValue(selectEl));
          openAddTeacherModal();
        } else if (event.params && event.params.data) {
          setPreviousTeacherValue(selectEl, event.params.data.id);
        }
      });
    }
  }

  async function saveNewTeacher() {
    var form = document.getElementById('addTeacherForm');
    var saveButton = document.getElementById('addTeacherSaveBtn');
    if (!form || !window.ReportFlowAPI) {
      return;
    }

    var firstName = (document.getElementById('addTeacherFirstName').value || '').trim();
    var lastName = (document.getElementById('addTeacherLastName').value || '').trim();
    var email = (document.getElementById('addTeacherEmail').value || '').trim();
    var department = (document.getElementById('addTeacherDepartment').value || '').trim();

    if (!firstName || !lastName || !email) {
      window.ReportFlowAPI.showToast('Enter first name, last name, and email.', 'error');
      return;
    }
    if (!department) {
      window.ReportFlowAPI.showToast('Department is required.', 'error');
      return;
    }

    if (window.ReportFlowLoader) {
      window.ReportFlowLoader.setButtonLoading(saveButton, true, 'Saving…');
    } else {
      saveButton.disabled = true;
    }
    try {
      var result = await window.ReportFlowAPI.apiFetch('/api/v1/users/create/', {
        method: 'POST',
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          email: email,
          role: TEACHER_ROLE,
          department: department,
        }),
      });

      var teacher = result.data && result.data.user ? result.data.user : null;
      if (teacher && teacher.id) {
        await loadTeachersForDepartment(department, String(teacher.id));
      } else {
        await loadTeachersForDepartment(department);
      }

      var modalEl = document.getElementById('addTeacherModal');
      if (modalEl && window.bootstrap && bootstrap.Modal) {
        bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      }
      form.reset();
      if (document.getElementById('addTeacherDepartment')) {
        document.getElementById('addTeacherDepartment').value = department;
      }

      var toastMessage = result.message || 'Teacher added';
      var loginDetails = result.data && result.data.login_details;
      if (loginDetails && loginDetails.username && loginDetails.password) {
        toastMessage +=
          ' Email could not be sent — share these credentials with the teacher manually: Username: ' +
          loginDetails.username +
          ' · Password: ' +
          loginDetails.password;
        window.ReportFlowAPI.showToast(toastMessage, 'warning');
      } else {
        window.ReportFlowAPI.showToast(toastMessage, 'success');
      }
    } catch (error) {
      window.ReportFlowAPI.showToast(
        window.ReportFlowAPI.formatApiError(error, 'Could not add teacher'),
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

  function bindCreateForm() {
    var roleSelect = getRoleSelect();
    var departmentSelect = getDepartmentSelect();
    var teacherSelect = getTeacherSelect();

    if (roleSelect) {
      roleSelect.addEventListener('change', updateTeacherFieldVisibility);
      if (window.jQuery && jQuery.fn.select2) {
        jQuery(roleSelect).on('select2:select', updateTeacherFieldVisibility);
      }
    }

    if (departmentSelect) {
      var onDepartmentChange = function () {
        if (getRoleSelect() && getRoleSelect().value === STUDENT_ROLE) {
          loadTeachersForDepartment(getSelectedDepartment());
        }
      };
      departmentSelect.addEventListener('change', onDepartmentChange);
      if (window.jQuery && jQuery.fn.select2) {
        jQuery(departmentSelect).on('select2:select', onDepartmentChange);
      }
    }

    if (teacherSelect) {
      bindTeacherSelect(teacherSelect);
    }

    document.addEventListener('rf:department-changed', function (event) {
      if (!event.detail || event.detail.selectId !== 'userCreateDepartment') {
        return;
      }
      if (getRoleSelect() && getRoleSelect().value === STUDENT_ROLE) {
        loadTeachersForDepartment(event.detail.department || getSelectedDepartment());
      }
    });

    var createModal = document.getElementById('userCreateModal');
    if (createModal) {
      createModal.addEventListener('shown.bs.modal', function () {
        updateTeacherFieldVisibility();
        bindTeacherSelect(getTeacherSelect());
      });
    }

    updateTeacherFieldVisibility();
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindCreateForm();

    var addTeacherForm = document.getElementById('addTeacherForm');
    if (addTeacherForm) {
      addTeacherForm.addEventListener('submit', function (event) {
        event.preventDefault();
        saveNewTeacher();
      });
    }

    var addTeacherModal = document.getElementById('addTeacherModal');
    if (addTeacherModal) {
      addTeacherModal.addEventListener('shown.bs.modal', function () {
        var firstNameInput = document.getElementById('addTeacherFirstName');
        if (firstNameInput) {
          firstNameInput.focus();
        }
      });
      addTeacherModal.addEventListener('hidden.bs.modal', function () {
        var form = document.getElementById('addTeacherForm');
        if (form) {
          form.reset();
        }
        var departmentInput = document.getElementById('addTeacherDepartment');
        if (departmentInput) {
          departmentInput.value = getSelectedDepartment();
        }
      });
    }
  });
})();
