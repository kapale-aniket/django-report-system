/**
 * ReportFlow — global loading overlay, contextual messages, and button states.
 */
(function (global) {
  'use strict';

  var activeRequests = 0;
  var isVisible = false;
  var pendingTimer = null;
  var DEFAULT_DELAY_MS = 300;
  var DEFAULT_MESSAGE = 'Loading…';

  function getLoaderEl() {
    return document.getElementById('rfGlobalLoader');
  }

  function getContentEl() {
    return document.getElementById('appPageMain');
  }

  function getTextEl() {
    return document.getElementById('rfLoaderText');
  }

  function getSubtextEl() {
    return document.getElementById('rfLoaderSubtext');
  }

  function setMessage(message, submessage) {
    var textEl = getTextEl();
    var subEl = getSubtextEl();
    if (textEl) {
      textEl.textContent = message || DEFAULT_MESSAGE;
    }
    if (subEl) {
      var sub = (submessage || '').trim();
      subEl.textContent = sub;
      subEl.classList.toggle('d-none', !sub);
    }
  }

  function resetMessage() {
    setMessage(DEFAULT_MESSAGE, '');
  }

  function revealLoader() {
    var loader = getLoaderEl();
    if (loader) {
      loader.classList.remove('d-none');
      loader.setAttribute('aria-busy', 'true');
    }
    dimContent(true);
    isVisible = true;
  }

  function concealLoader() {
    var loader = getLoaderEl();
    if (loader) {
      loader.classList.add('d-none');
      loader.setAttribute('aria-busy', 'false');
    }
    dimContent(false);
    isVisible = false;
  }

  function dimContent(dim) {
    var main = getContentEl();
    if (main) {
      main.classList.toggle('opacity-50', dim);
      main.classList.toggle('pe-none', dim);
    }
    document.body.classList.toggle('rf-loading-active', dim);
  }

  function clearPendingTimer() {
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
  }

  function show(options) {
    options = options || {};
    activeRequests += 1;

    if (options.message || options.submessage) {
      setMessage(options.message || DEFAULT_MESSAGE, options.submessage);
    }

    if (activeRequests !== 1 || isVisible || pendingTimer) {
      return;
    }

    var immediate = options.immediate === true || options.delay === 0;
    var delay = immediate ? 0 : (options.delay !== undefined ? options.delay : DEFAULT_DELAY_MS);

    if (delay === 0) {
      revealLoader();
      return;
    }

    pendingTimer = setTimeout(function () {
      pendingTimer = null;
      if (activeRequests > 0 && !isVisible) {
        revealLoader();
      }
    }, delay);
  }

  function hide() {
    activeRequests = Math.max(0, activeRequests - 1);
    if (activeRequests !== 0) {
      return;
    }
    clearPendingTimer();
    if (isVisible) {
      concealLoader();
    }
    resetMessage();
  }

  function forceHide() {
    activeRequests = 0;
    clearPendingTimer();
    if (isVisible) {
      concealLoader();
    }
    resetMessage();
  }

  function setButtonLoading(button, loading, loadingLabel) {
    if (!button) {
      return;
    }

    if (loading) {
      if (button.dataset.rfLoadingActive === 'true') {
        return;
      }
      button.dataset.rfLoadingActive = 'true';
      button.dataset.rfOriginalHtml = button.innerHTML;
      button.dataset.rfWasDisabled = button.disabled ? 'true' : 'false';
      button.disabled = true;
      button.classList.add('rf-btn-loading');
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>' +
        (loadingLabel || 'Loading…');
      return;
    }

    if (button.dataset.rfLoadingActive !== 'true') {
      return;
    }

    button.classList.remove('rf-btn-loading');
    button.disabled = button.dataset.rfWasDisabled === 'true';
    if (button.dataset.rfOriginalHtml) {
      button.innerHTML = button.dataset.rfOriginalHtml;
    }
    delete button.dataset.rfLoadingActive;
    delete button.dataset.rfOriginalHtml;
    delete button.dataset.rfWasDisabled;
  }

  function disableInRoot(root, disabled) {
    (root || document).querySelectorAll('button, input, select, textarea, a.btn').forEach(function (el) {
      if (disabled) {
        if (!el.dataset.rfLoaderDisabled) {
          el.dataset.rfLoaderDisabled = el.disabled ? 'was-disabled' : 'was-enabled';
        }
        el.disabled = true;
        el.classList.add('pe-none');
        el.setAttribute('aria-disabled', 'true');
      } else if (el.dataset.rfLoaderDisabled) {
        el.disabled = el.dataset.rfLoaderDisabled === 'was-disabled';
        el.classList.remove('pe-none');
        el.removeAttribute('aria-disabled');
        delete el.dataset.rfLoaderDisabled;
      }
    });
  }

  async function track(promise, options) {
    show(options);
    try {
      return await promise;
    } finally {
      hide();
    }
  }

  function bindForms() {
    document.querySelectorAll(
      'form.app-form-loading:not([data-ajax="true"]):not([data-api-login="true"]):not([data-loader-manual="true"])'
    ).forEach(function (form) {
      if (form.dataset.rfLoaderBound === 'true') {
        return;
      }
      form.dataset.rfLoaderBound = 'true';
      form.addEventListener('submit', function () {
        var message = form.getAttribute('data-loader-message') || 'Loading…';
        var submessage = form.getAttribute('data-loader-submessage') || '';
        var immediate = form.getAttribute('data-loader-immediate') === 'true' || form.enctype === 'multipart/form-data';
        setButtonLoading(
          form.querySelector('[type="submit"]'),
          true,
          form.getAttribute('data-loader-button-label') || message
        );
        show({ message: message, submessage: submessage, immediate: immediate });
      });
    });
  }

  function bindLoadingButtons() {
    document.querySelectorAll('[data-rf-loading="true"]').forEach(function (button) {
      if (button.dataset.rfLoaderBound === 'true') {
        return;
      }
      button.dataset.rfLoaderBound = 'true';
      button.addEventListener('click', function () {
        setButtonLoading(button, true, button.getAttribute('data-rf-loading-label') || 'Loading…');
      });
    });
  }

  function isInternalNavLink(link) {
    if (!link || !link.href) {
      return false;
    }
    if (link.target === '_blank' || link.hasAttribute('download') || link.hasAttribute('data-no-loader')) {
      return false;
    }
    if (link.getAttribute('href').charAt(0) === '#') {
      return false;
    }
    if (link.hasAttribute('data-bs-toggle') || link.hasAttribute('data-bs-target')) {
      return false;
    }
    try {
      var url = new URL(link.href, window.location.origin);
      return url.origin === window.location.origin;
    } catch (error) {
      return false;
    }
  }

  function bindNavigationLoader() {
    document.addEventListener('click', function (event) {
      var link = event.target.closest('a[href]');
      if (!isInternalNavLink(link)) {
        return;
      }
      if (link.hasAttribute('data-rf-download-loader')) {
        return;
      }
      var label = link.querySelector('.app-sidebar-label');
      var navText = label ? label.textContent.trim() : link.textContent.trim();
      var message = link.getAttribute('data-loader-message');
      if (!message && navText) {
        message = 'Loading ' + navText.toLowerCase() + '…';
      }
      show({ message: message || 'Loading page…', immediate: true, delay: 0 });
    });
  }

  function bindDownloadLoader() {
    document.addEventListener('click', function (event) {
      var link = event.target.closest('[data-rf-download-loader]');
      if (!link) {
        return;
      }
      var message = link.getAttribute('data-loader-message') || 'Preparing download…';
      show({ message: message, submessage: 'Please wait.', immediate: true, delay: 0 });
      window.setTimeout(function () {
        hide();
        if (global.ReportFlowToast) {
          global.ReportFlowToast.success('Download started successfully.');
        }
      }, 1200);
    });
  }

  global.ReportFlowLoader = {
    show: show,
    hide: hide,
    forceHide: forceHide,
    track: track,
    setMessage: setMessage,
    resetMessage: resetMessage,
    setButtonLoading: setButtonLoading,
    disableInRoot: disableInRoot,
    bindForms: bindForms,
  };

  document.addEventListener('DOMContentLoaded', function () {
    bindForms();
    bindLoadingButtons();
    bindNavigationLoader();
    bindDownloadLoader();
  });

  window.addEventListener('pageshow', function () {
    forceHide();
  });
})(window);
