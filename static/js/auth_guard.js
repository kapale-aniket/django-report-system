/**
 * Block cached app pages after logout — back button, forward button, and bfcache.
 */
(function () {
  'use strict';

  var LOGIN_URL = '/accounts/login/';
  var CHECK_URL = '/accounts/session-check/';
  var checking = false;

  function redirectToLogin() {
    if (window.location.pathname.indexOf('/accounts/login') === 0) {
      return;
    }
    var next = window.location.pathname + window.location.search + window.location.hash;
    window.location.replace(LOGIN_URL + '?next=' + encodeURIComponent(next));
  }

  function verifySession() {
    if (checking) {
      return;
    }
    checking = true;
    fetch(CHECK_URL, {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then(function (res) {
        if (!res.ok) {
          redirectToLogin();
        }
      })
      .catch(function () {
        redirectToLogin();
      })
      .finally(function () {
        checking = false;
      });
  }

  window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
      window.location.reload();
      return;
    }
    verifySession();
  });

  window.addEventListener('popstate', function () {
    verifySession();
  });

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') {
      verifySession();
    }
  });

  if (window.history && window.history.replaceState) {
    window.history.replaceState({ rfAuthGuard: true }, '', window.location.href);
  }
})();
