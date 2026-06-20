/**
 * App shell: sidebar (mobile offcanvas), dark mode (localStorage), form loading.
 */
(function () {
  'use strict';

  var THEME_KEY = 'app-dashboard-theme';
  var MOBILE_BP = 992;

  function initTheme() {
    var stored = localStorage.getItem(THEME_KEY);
    if (stored === 'dark' || stored === 'light') {
      document.documentElement.setAttribute('data-bs-theme', stored);
    }
  }

  function toggleTheme() {
    var cur = document.documentElement.getAttribute('data-bs-theme') || 'light';
    var next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', next);
    localStorage.setItem(THEME_KEY, next);
  }

  function isMobile() {
    return window.innerWidth < MOBILE_BP;
  }

  function initSidebar() {
    var sidebar = document.getElementById('appSidebar');
    var overlay = document.getElementById('appSidebarOverlay');
    var openBtn = document.getElementById('appSidebarOpen');
    var closeBtn = document.getElementById('appSidebarClose');
    var collapseBtn = document.getElementById('appSidebarCollapse');

    function setMenuOpen(open) {
      if (!sidebar) return;
      if (open) {
        sidebar.classList.add('app-sidebar--open');
        if (overlay) {
          overlay.classList.add('show');
          overlay.setAttribute('aria-hidden', 'false');
        }
        document.body.classList.add('app-sidebar-open');
        if (openBtn) {
          openBtn.classList.add('is-active');
          openBtn.setAttribute('aria-expanded', 'true');
          openBtn.setAttribute('aria-label', 'Close menu');
        }
      } else {
        sidebar.classList.remove('app-sidebar--open');
        if (overlay) {
          overlay.classList.remove('show');
          overlay.setAttribute('aria-hidden', 'true');
        }
        document.body.classList.remove('app-sidebar-open');
        if (openBtn) {
          openBtn.classList.remove('is-active');
          openBtn.setAttribute('aria-expanded', 'false');
          openBtn.setAttribute('aria-label', 'Open menu');
        }
      }
    }

    function closeMobile() {
      setMenuOpen(false);
    }

    function openMobile() {
      setMenuOpen(true);
    }

    function toggleMobile() {
      if (sidebar && sidebar.classList.contains('app-sidebar--open')) {
        closeMobile();
      } else {
        openMobile();
      }
    }

    if (openBtn) {
      openBtn.addEventListener('click', function () {
        if (isMobile()) toggleMobile();
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', closeMobile);
    }

    if (overlay) {
      overlay.addEventListener('click', closeMobile);
    }

    if (sidebar) {
      sidebar.querySelectorAll('.app-sidebar-nav a.app-sidebar-link').forEach(function (link) {
        link.addEventListener('click', function () {
          if (isMobile()) closeMobile();
        });
      });
      sidebar.querySelectorAll('.app-sidebar-footer form').forEach(function (form) {
        form.addEventListener('submit', function () {
          if (isMobile()) closeMobile();
        });
      });
    }

    if (collapseBtn && sidebar) {
      collapseBtn.addEventListener('click', function () {
        if (isMobile()) {
          closeMobile();
        } else {
          sidebar.classList.toggle('app-sidebar--collapsed');
        }
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar && sidebar.classList.contains('app-sidebar--open')) {
        closeMobile();
        if (openBtn) openBtn.focus();
      }
    });

    window.addEventListener(
      'resize',
      function () {
        if (!isMobile()) closeMobile();
      },
      { passive: true }
    );

    var bottomMore = document.getElementById('appBottomNavMore');
    if (bottomMore) {
      bottomMore.addEventListener('click', function () {
        openMobile();
      });
    }
  }

  function initTooltips() {
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
      });
    }
  }

  document.querySelectorAll('[data-app-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', toggleTheme);
  });

  initTheme();
  initSidebar();
  initTooltips();
})();
