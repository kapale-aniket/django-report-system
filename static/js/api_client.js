/**
 * ReportFlow Enterprise API Client
 * Standard envelope: { success, message, data, errors, status_code }
 */
(function (global) {
  'use strict';

  const TOKEN_KEY = 'rf_access_token';
  const REFRESH_KEY = 'rf_refresh_token';
  const API_BASE = '/api/v1';

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^|;)\\s*' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  function getAccessToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function setTokens(access, refresh) {
    if (access) localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  }

  function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }

  function showToast(message, type, options) {
    if (global.ReportFlowToast) {
      return global.ReportFlowToast.show(message, type, options);
    }
    console.log('[toast]', type || 'info', message);
  }

  function sanitizeFriendlyMessage(message) {
    var text = String(message || '').trim();
    if (!text) return 'Something went wrong. Please try again.';
    var friendlyMap = {
      'Authentication required': 'Please sign in to continue.',
      'Permission denied': "You don't have permission to do that.",
      'Validation failed': 'Please check your input and try again.',
      'Resource not found': "We couldn't find what you're looking for.",
      'Database error': 'Something went wrong saving your data. Please try again.',
      'Internal server error': 'Something went wrong. Please try again in a moment.',
      'Unexpected service error': 'Something went wrong. Please try again.',
      'Business rule violation': "This action isn't allowed right now.",
      'Request failed': "We couldn't complete that request. Please try again.",
    };
    if (friendlyMap[text]) return friendlyMap[text];
    if (/traceback|integrityerror|doesnotexist|operationalerror|file "/i.test(text)) {
      return 'Something went wrong. Please try again.';
    }
    return text.length > 280 ? text.slice(0, 277) + '…' : text;
  }

  function formatApiError(error, fallbackMessage) {
    const errorMessage =
      (error && error.payload && error.payload.message) ||
      (error && error.message) ||
      fallbackMessage ||
      'Something went wrong. Please try again.';
    const fieldErrors = error && error.payload && error.payload.errors;
    if (Array.isArray(fieldErrors) && fieldErrors.length) {
      return sanitizeFriendlyMessage(fieldErrors.join(' '));
    }
    if (fieldErrors && typeof fieldErrors === 'object') {
      const joined = Object.values(fieldErrors).flat().join(' ');
      return sanitizeFriendlyMessage(joined || errorMessage);
    }
    return sanitizeFriendlyMessage(errorMessage);
  }

  function inferLoaderMessage(url, method, body) {
    const path = (url || '').split('?')[0];
    const upperMethod = (method || 'GET').toUpperCase();

    if (body instanceof FormData) {
      if (path.indexOf('/profile/photo') !== -1) {
        return 'Uploading photo…';
      }
      return 'Uploading report…';
    }
    if (path.indexOf('/auth/login') !== -1) {
      return 'Signing in…';
    }
    if (path.indexOf('/reports/submit') !== -1) {
      return 'Uploading report…';
    }
    if (path.indexOf('/ai-process') !== -1) {
      return 'Analyzing report…';
    }
    if (path.indexOf('/ai-suggestions') !== -1) {
      return 'Loading AI insights…';
    }
    if (path.indexOf('/bulk-action') !== -1) {
      return 'Processing reports…';
    }
    if (path.indexOf('/suggest-reply') !== -1) {
      return 'Generating suggested reply…';
    }
    if (path.indexOf('/users/') !== -1 && path.indexOf('/students') !== -1) {
      return 'Loading students…';
    }
    if (upperMethod === 'GET' && path.indexOf('/reports') !== -1) {
      return 'Loading reports…';
    }
    if (path.indexOf('/auth/profile') !== -1 && upperMethod === 'GET') {
      return 'Loading profile…';
    }
    if (path.indexOf('/auth/profile') !== -1) {
      return 'Saving profile…';
    }
    if (path.indexOf('/auth/change-password') !== -1) {
      return 'Updating password…';
    }
    if (upperMethod === 'DELETE') {
      return 'Deleting…';
    }
    if (upperMethod === 'PATCH' || upperMethod === 'PUT') {
      return 'Saving changes…';
    }
    return 'Loading…';
  }

  function inferLoaderSubmessage(url, body) {
    const path = (url || '').split('?')[0];
    if (body instanceof FormData && path.indexOf('/reports/submit') !== -1) {
      return 'Please wait while your report file is uploaded.';
    }
    if (path.indexOf('/ai-process') !== -1) {
      return 'Extracting text · generating summary · checking weaknesses…';
    }
    if (path.indexOf('/ai-suggestions') !== -1) {
      return 'Please wait.';
    }
    if (path.indexOf('/auth/login') !== -1) {
      return 'Please wait.';
    }
    return '';
  }

  function showLoader(options) {
    if (!global.ReportFlowLoader) {
      return;
    }
    global.ReportFlowLoader.show(options || {});
  }

  function hideLoader() {
    if (!global.ReportFlowLoader) {
      return;
    }
    global.ReportFlowLoader.hide();
  }

  function setFormButtonLoading(form, loading, loadingLabel) {
    if (!form || !global.ReportFlowLoader) {
      return;
    }
    global.ReportFlowLoader.setButtonLoading(
      form.querySelector('[type="submit"]'),
      loading,
      loadingLabel
    );
  }

  function dismissParentModal(form) {
    if (form.getAttribute('data-api-dismiss-modal') === 'false') return;
    if (global.ReportFlowModals && global.ReportFlowModals.dismiss) {
      global.ReportFlowModals.dismiss(form);
    }
  }

  const PUBLIC_AUTH_PATHS = [
    '/auth/login/',
    '/auth/register/',
    '/auth/forgot-password/',
    '/auth/reset-password/',
  ];

  function isPublicAuthUrl(url) {
    const path = (url || '').split('?')[0];
    return PUBLIC_AUTH_PATHS.some(function (segment) {
      return path.indexOf(segment) !== -1;
    });
  }

  async function apiFetch(url, options) {
    options = options || {};
    const useLoader = options.loader !== false;
    const fetchOptions = Object.assign({}, options);
    delete fetchOptions.loader;
    delete fetchOptions.loaderMessage;
    delete fetchOptions.loaderSubmessage;
    delete fetchOptions.loaderImmediate;
    delete fetchOptions.loaderDelay;
    delete fetchOptions.skipAuth;

    const body = fetchOptions.body;
    const method = fetchOptions.method || 'GET';
    const loaderMessage =
      options.loaderMessage ||
      inferLoaderMessage(url, method, body);
    const loaderSubmessage =
      options.loaderSubmessage !== undefined
        ? options.loaderSubmessage
        : inferLoaderSubmessage(url, body);
    const loaderImmediate =
      options.loaderImmediate === true ||
      body instanceof FormData ||
      options.loaderDelay === 0;
    const loaderDelay = loaderImmediate
      ? 0
      : options.loaderDelay !== undefined
        ? options.loaderDelay
        : undefined;

    if (useLoader) {
      showLoader({
        message: loaderMessage,
        submessage: loaderSubmessage,
        immediate: loaderImmediate,
        delay: loaderDelay,
      });
    }

    try {
      const headers = Object.assign({}, fetchOptions.headers || {});
      const skipAuth = options.skipAuth === true || isPublicAuthUrl(url);
      const token = skipAuth ? '' : getAccessToken();
      if (token) headers['Authorization'] = 'Bearer ' + token;
      if (!(body instanceof FormData)) {
        headers['Content-Type'] = headers['Content-Type'] || 'application/json';
      }
      const csrf = getCookie('csrftoken');
      if (csrf) headers['X-CSRFToken'] = csrf;

      const response = await fetch(
        url,
        Object.assign({}, fetchOptions, {
          headers: headers,
          credentials: fetchOptions.credentials || 'same-origin',
        })
      );
      let payload;
      try {
        payload = await response.json();
      } catch (parseError) {
        throw new Error('Invalid JSON response');
      }
      if (!payload.success) {
        const err = new Error(payload.message || 'Request failed');
        err.payload = payload;
        throw err;
      }
      return payload;
    } finally {
      if (useLoader) {
        hideLoader();
      }
    }
  }

  async function login(username, password, roleHint) {
    clearTokens();
    const payload = await apiFetch(API_BASE + '/auth/login/', {
      method: 'POST',
      body: JSON.stringify({
        username: username,
        password: password,
        role_hint: roleHint || '',
      }),
      loaderMessage: 'Signing in…',
      loaderSubmessage: 'Please wait.',
      loaderImmediate: true,
      skipAuth: true,
    });
    const tokens = payload.data.tokens || {};
    setTokens(tokens.access, tokens.refresh);
    return payload;
  }

  async function logout() {
    const refresh = localStorage.getItem(REFRESH_KEY) || '';
    try {
      await apiFetch(API_BASE + '/auth/logout/', {
        method: 'POST',
        body: JSON.stringify({ refresh: refresh }),
        loaderMessage: 'Signing out…',
        loaderImmediate: true,
      });
    } catch (e) { /* ignore */ }
    clearTokens();
    window.location.href = '/';
  }

  function bindAjaxForms() {
    document.querySelectorAll('form[data-ajax="true"]').forEach(function (form) {
      form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        const apiUrl = form.getAttribute('data-api-url');
        if (!apiUrl) return;
        const method = (form.getAttribute('data-api-method') || 'POST').toUpperCase();
        const loaderMessage = form.getAttribute('data-loader-message') || inferLoaderMessage(apiUrl, method, null);
        const loaderSubmessage = form.getAttribute('data-loader-submessage') || '';
        const buttonLabel = form.getAttribute('data-loader-button-label') || loaderMessage;
        setFormButtonLoading(form, true, buttonLabel);

        try {
          let body;
          const apiBody = form.getAttribute('data-api-body');
          if (apiBody) {
            body = apiBody;
          } else if (method === 'DELETE') {
            body = undefined;
          } else if (form.enctype === 'multipart/form-data' || form.querySelector('input[type="file"]')) {
            body = new FormData(form);
          } else {
            const formData = new FormData(form);
            const formFields = {};
            formData.forEach(function (fieldValue, fieldName) {
              if (formFields[fieldName] !== undefined) {
                if (!Array.isArray(formFields[fieldName])) formFields[fieldName] = [formFields[fieldName]];
                formFields[fieldName].push(fieldValue);
              } else {
                formFields[fieldName] = fieldValue;
              }
            });
            body = JSON.stringify(formFields);
          }
          const remap = form.getAttribute('data-api-remap');
          if (remap && typeof body === 'string') {
            try {
              const parsed = JSON.parse(body);
              remap.split(',').forEach(function (pair) {
                const parts = pair.split(':');
                if (parts.length === 2 && parsed[parts[0].trim()] !== undefined) {
                  parsed[parts[1].trim()] = parsed[parts[0].trim()];
                  delete parsed[parts[0].trim()];
                }
              });
              body = JSON.stringify(parsed);
            } catch (e) { /* ignore */ }
          }

          const result = await apiFetch(apiUrl, {
            method: method,
            body: body,
            loaderMessage: loaderMessage,
            loaderSubmessage: loaderSubmessage || inferLoaderSubmessage(apiUrl, body),
            loaderImmediate: body instanceof FormData || form.getAttribute('data-loader-immediate') === 'true',
          });

          dismissParentModal(form);
          showToast(result.message || 'Done', 'success');

          const redirect = form.getAttribute('data-api-redirect');
          const reload = form.getAttribute('data-api-reload');
          const followLink = form.getAttribute('data-api-follow-link') === 'true';
          const payloadRedirect =
            followLink && result.data && result.data.redirect_url ? result.data.redirect_url : '';
          if (redirect) {
            window.location.href = redirect;
          } else if (payloadRedirect) {
            window.location.href = payloadRedirect;
          } else if (reload !== 'false') {
            window.location.reload();
          }
        } catch (err) {
          showToast(formatApiError(err), 'error');
        } finally {
          setFormButtonLoading(form, false);
        }
      });
    });
  }

  function bindAjaxButtons() {
    document.querySelectorAll('[data-api-action]').forEach(function (btn) {
      btn.addEventListener('click', async function (ev) {
        ev.preventDefault();
        const url = btn.getAttribute('data-api-url');
        const method = (btn.getAttribute('data-api-method') || 'POST').toUpperCase();
        if (!url) return;
        const loaderMessage = btn.getAttribute('data-loader-message') || inferLoaderMessage(url, method, null);
        global.ReportFlowLoader && global.ReportFlowLoader.setButtonLoading(btn, true, loaderMessage);
        try {
          const body = btn.getAttribute('data-api-body');
          const result = await apiFetch(url, {
            method: method,
            body: body ? body : undefined,
            loaderMessage: loaderMessage,
            loaderImmediate: true,
          });
          showToast(result.message || 'Done', 'success');
          if (btn.getAttribute('data-api-reload') !== 'false') {
            window.location.reload();
          }
        } catch (err) {
          showToast(formatApiError(err), 'error');
        } finally {
          global.ReportFlowLoader && global.ReportFlowLoader.setButtonLoading(btn, false);
        }
      });
    });
  }

  function bindLoginForms() {
    document.querySelectorAll('form[data-api-login="true"]').forEach(function (form) {
      form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        const loginFormData = new FormData(form);
        setFormButtonLoading(form, true, 'Signing in…');
        try {
          const result = await login(
            loginFormData.get('username'),
            loginFormData.get('password'),
            loginFormData.get('login_role_hint') || loginFormData.get('role_hint') || ''
          );
          showToast(result.message || 'Login successful', 'success');
          window.location.href = '/accounts/redirect/';
        } catch (err) {
          showToast(formatApiError(err, 'Sign in failed'), 'error');
        } finally {
          setFormButtonLoading(form, false);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindAjaxForms();
    bindAjaxButtons();
    bindLoginForms();
    const logoutBtn = document.getElementById('apiLogoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function (e) {
        e.preventDefault();
        logout();
      });
    }
  });

  global.ReportFlowAPI = {
    apiFetch: apiFetch,
    login: login,
    logout: logout,
    setTokens: setTokens,
    clearTokens: clearTokens,
    getAccessToken: getAccessToken,
    API_BASE: API_BASE,
    showToast: showToast,
    formatApiError: formatApiError,
    showLoader: showLoader,
    hideLoader: hideLoader,
    toast: global.ReportFlowToast,
  };
})(window);
