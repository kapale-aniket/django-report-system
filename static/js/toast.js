/**
 * ReportFlow — centralized toast notifications.
 * Usage: ReportFlowToast.success('Saved'); ReportFlowToast.error('Failed');
 */
(function (global) {
  'use strict';

  var ICONS = {
    success: 'bi-check-circle-fill',
    error: 'bi-exclamation-octagon-fill',
    warning: 'bi-exclamation-triangle-fill',
    info: 'bi-info-circle-fill',
  };

  var TITLES = {
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    info: 'Notice',
  };

  var DEFAULT_DURATION = 5000;

  var MAX_VISIBLE = 5;

  function ensureHost() {
    var host = document.getElementById('rfToastHost');
    if (!host) {
      host = document.createElement('div');
      host.id = 'rfToastHost';
      host.className = 'rf-toast-host';
      host.setAttribute('aria-live', 'polite');
      host.setAttribute('aria-relevant', 'additions');
      document.body.appendChild(host);
    }
    return host;
  }

  function normalizeType(type) {
    var t = (type || 'info').toLowerCase();
    if (t === 'danger') t = 'error';
    return ICONS[t] ? t : 'info';
  }

  function trimHost(host) {
    var items = host.querySelectorAll('.rf-toast');
    if (items.length <= MAX_VISIBLE) return;
    for (var i = 0; i < items.length - MAX_VISIBLE; i++) {
      dismiss(items[i], true);
    }
  }

  function dismiss(el, immediate) {
    if (!el || el._rfDismissed) return;
    el._rfDismissed = true;
    if (el._rfTimer) clearTimeout(el._rfTimer);
    el.classList.remove('is-visible');
    el.classList.add('is-hiding');
    var delay = immediate ? 0 : 280;
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, delay);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function show(message, type, options) {
    if (message === undefined || message === null) return null;
    var text = String(message).trim();
    if (!text) return null;

    options = options || {};
    type = normalizeType(type);
    var host = ensureHost();
    trimHost(host);

    var duration = options.duration != null ? options.duration : DEFAULT_DURATION;
    var title = options.title || TITLES[type];

    var el = document.createElement('div');
    el.className = 'rf-toast rf-toast--' + type;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    el.innerHTML =
      '<i class="bi ' +
      ICONS[type] +
      ' rf-toast__icon" aria-hidden="true"></i>' +
      '<div class="rf-toast__body">' +
      (options.title !== false ? '<span class="visually-hidden">' + escapeHtml(title) + ': </span>' : '') +
      escapeHtml(text) +
      '</div>' +
      '<button type="button" class="rf-toast__close" aria-label="Dismiss notification"><i class="bi bi-x-lg" aria-hidden="true"></i></button>' +
      '<span class="rf-toast__progress" style="animation-duration:' +
      duration +
      'ms"></span>';

    host.appendChild(el);

    var closeBtn = el.querySelector('.rf-toast__close');
    closeBtn.addEventListener('click', function () {
      dismiss(el);
    });

    requestAnimationFrame(function () {
      el.classList.add('is-visible');
    });

    el._rfTimer = setTimeout(function () {
      dismiss(el);
    }, duration);

    return el;
  }

  function flushFlashMessages() {
    document.querySelectorAll('script.rf-flash-messages').forEach(function (script) {
      try {
        var items = JSON.parse(script.textContent || '[]');
        if (!Array.isArray(items)) return;
        items.forEach(function (item, index) {
          setTimeout(function () {
            show(item.text, item.type);
          }, index * 100);
        });
      } catch (e) {
        /* ignore malformed flash payload */
      }
      script.remove();
    });
  }

  function mapDjangoTag(tags) {
    tags = tags || '';
    if (tags.indexOf('error') !== -1) return 'error';
    if (tags.indexOf('success') !== -1) return 'success';
    if (tags.indexOf('warning') !== -1) return 'warning';
    return 'info';
  }

  var Toast = {
    show: show,
    success: function (msg, opts) {
      return show(msg, 'success', opts);
    },
    error: function (msg, opts) {
      return show(msg, 'error', opts);
    },
    warning: function (msg, opts) {
      return show(msg, 'warning', opts);
    },
    info: function (msg, opts) {
      return show(msg, 'info', opts);
    },
    dismiss: dismiss,
    flushFlashMessages: flushFlashMessages,
    mapDjangoTag: mapDjangoTag,
  };

  global.ReportFlowToast = Toast;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', flushFlashMessages);
  } else {
    flushFlashMessages();
  }
})(window);
