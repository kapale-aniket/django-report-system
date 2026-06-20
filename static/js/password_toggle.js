/**
 * Adds a show/hide (eye) button to password fields on login, signup, and profile forms.
 */
(function () {
  'use strict';

  var ICON_CLASS_SHOW = 'bi bi-eye';
  var ICON_CLASS_HIDE = 'bi bi-eye-slash';
  var DATA_ATTRIBUTE_TOGGLE_ADDED = 'passwordVisibilityToggleAdded';

  function isPasswordInput(element) {
    return element && element.type === 'password';
  }

  function hasVisibilityToggleAlready(passwordInput) {
    return passwordInput.dataset[DATA_ATTRIBUTE_TOGGLE_ADDED] === 'true';
  }

  function markVisibilityToggleAdded(passwordInput) {
    passwordInput.dataset[DATA_ATTRIBUTE_TOGGLE_ADDED] = 'true';
  }

  function isPasswordVisible(passwordInput) {
    return passwordInput.type === 'text';
  }

  function setPasswordVisible(passwordInput, shouldShowPlainText) {
    passwordInput.type = shouldShowPlainText ? 'text' : 'password';
  }

  function updateToggleButtonState(toggleButton, passwordInput) {
    var passwordIsVisible = isPasswordVisible(passwordInput);

    toggleButton.setAttribute('aria-pressed', passwordIsVisible ? 'true' : 'false');
    toggleButton.setAttribute('aria-label', passwordIsVisible ? 'Hide password' : 'Show password');

    var eyeIcon = toggleButton.querySelector('i');
    if (eyeIcon) {
      eyeIcon.className = passwordIsVisible ? ICON_CLASS_HIDE : ICON_CLASS_SHOW;
    }
  }

  function createVisibilityToggleButton(passwordInput) {
    var toggleButton = document.createElement('button');
    toggleButton.type = 'button';
    toggleButton.className = 'password-visibility-toggle-button';
    toggleButton.setAttribute('aria-label', 'Show password');
    toggleButton.setAttribute('aria-pressed', 'false');
    toggleButton.innerHTML = '<i class="' + ICON_CLASS_SHOW + '" aria-hidden="true"></i>';

    toggleButton.addEventListener('click', function () {
      var passwordIsVisible = isPasswordVisible(passwordInput);
      setPasswordVisible(passwordInput, !passwordIsVisible);
      updateToggleButtonState(toggleButton, passwordInput);
      passwordInput.focus();
    });

    return toggleButton;
  }

  function getToggleHostElement(passwordInput) {
    var fieldContainer = passwordInput.parentElement;
    if (!fieldContainer) {
      return null;
    }

    if (fieldContainer.classList.contains('password-field-with-visibility-toggle')) {
      return fieldContainer;
    }

    if (fieldContainer.classList.contains('form-floating')) {
      fieldContainer.classList.add('password-field-with-visibility-toggle');
      return fieldContainer;
    }

    var toggleHost = document.createElement('div');
    toggleHost.className = 'password-field-with-visibility-toggle';
    fieldContainer.insertBefore(toggleHost, passwordInput);
    toggleHost.appendChild(passwordInput);
    return toggleHost;
  }

  function addPasswordVisibilityToggle(passwordInput) {
    if (!isPasswordInput(passwordInput) || hasVisibilityToggleAlready(passwordInput)) {
      return;
    }

    var toggleHost = getToggleHostElement(passwordInput);
    if (!toggleHost) {
      return;
    }

    markVisibilityToggleAdded(passwordInput);

    var visibilityToggleButton = createVisibilityToggleButton(passwordInput);
    toggleHost.appendChild(visibilityToggleButton);
  }

  function addPasswordVisibilityTogglesWithinContainer(fieldContainer) {
    initializeAllPasswordVisibilityToggles(fieldContainer);
  }

  function initializeAllPasswordVisibilityToggles(searchRoot) {
    searchRoot = searchRoot || document;
    searchRoot.querySelectorAll('input[type="password"]').forEach(addPasswordVisibilityToggle);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initializeAllPasswordVisibilityToggles();
  });

  document.addEventListener('shown.bs.modal', function (event) {
    if (event.target && event.target.id === 'profileModal') {
      initializeAllPasswordVisibilityToggles(event.target);
    }
  });

  window.ReportFlowPasswordVisibilityToggle = {
    initializeAll: initializeAllPasswordVisibilityToggles,
  };
})();
