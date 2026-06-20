(function () {
  'use strict';

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^|;)\\s*' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  function parsePayload() {
    var node = document.getElementById('certCelebrationPayload');
    if (!node || !node.textContent) {
      return null;
    }
    try {
      return JSON.parse(node.textContent);
    } catch (err) {
      return null;
    }
  }

  function fireConfetti() {
    if (typeof window.confetti !== 'function') {
      return;
    }
    var duration = 2800;
    var end = Date.now() + duration;
    var defaults = {
      startVelocity: 42,
      spread: 360,
      ticks: 70,
      zIndex: 1082,
      colors: ['#2d5a47', '#c9a227', '#4a7c59', '#f0d878', '#ffffff'],
    };

    function frame() {
      window.confetti(Object.assign({}, defaults, {
        particleCount: 4,
        origin: { x: Math.random(), y: Math.random() * 0.35 },
      }));
      if (Date.now() < end) {
        window.requestAnimationFrame(frame);
      }
    }
    frame();

    window.confetti({
      particleCount: 120,
      spread: 80,
      origin: { y: 0.55 },
      zIndex: 1082,
      colors: defaults.colors,
    });
  }

  function acknowledge(payload) {
    if (!payload || !payload.ack_url) {
      return Promise.resolve();
    }
    var csrf = getCookie('csrftoken');
    return fetch(payload.ack_url, {
      method: 'POST',
      headers: csrf ? { 'X-CSRFToken': csrf } : {},
      credentials: 'same-origin',
    }).catch(function () {
      return null;
    });
  }

  function closeCelebration(root, payload) {
    document.body.classList.remove('cert-celebration-active');
    root.setAttribute('hidden', 'hidden');
    return acknowledge(payload);
  }

  function initCertificateCelebration() {
    var payload = parsePayload();
    var root = document.getElementById('certCelebrationRoot');
    if (!payload || !root) {
      return;
    }

    document.body.classList.add('cert-celebration-active');
    root.removeAttribute('hidden');
    fireConfetti();

    var closeBtn = document.getElementById('certCelebrationClose');
    var laterBtn = document.getElementById('certCelebrationLater');
    var downloadBtn = document.getElementById('certCelebrationDownload');
    var acknowledged = false;

    function markViewed() {
      if (acknowledged) {
        return Promise.resolve();
      }
      acknowledged = true;
      return acknowledge(payload);
    }

    function dismiss() {
      markViewed().finally(function () {
        document.body.classList.remove('cert-celebration-active');
        root.setAttribute('hidden', 'hidden');
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', dismiss);
    }
    if (laterBtn) {
      laterBtn.addEventListener('click', dismiss);
    }
    if (downloadBtn) {
      downloadBtn.addEventListener('click', function () {
        markViewed().finally(function () {
          document.body.classList.remove('cert-celebration-active');
          root.setAttribute('hidden', 'hidden');
        });
      });
    }

    root.addEventListener('click', function (event) {
      if (event.target === root.querySelector('.cert-celebration-backdrop')) {
        dismiss();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', initCertificateCelebration);
})();
