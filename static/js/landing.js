/**
 * Landing page: theme (synced with app), nav scroll, mobile menu, reveal, progress.
 */
(function () {
  'use strict';

  const html = document.documentElement;
  const header = document.getElementById('lpNavbar');
  const progress = document.getElementById('lpScrollProgress');
  const themeToggle = document.getElementById('lpThemeToggle');
  const menuBtn = document.getElementById('lpMenuBtn');
  const mobileNav = document.getElementById('lpMobileNav');
  const THEME_KEY = 'reportflow-theme';

  function applyTheme(mode) {
    html.setAttribute('data-bs-theme', mode);
    if (themeToggle) {
      const icon = themeToggle.querySelector('i');
      if (icon) {
        icon.className = mode === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
      }
    }
  }

  function initTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'dark' || stored === 'light') {
      applyTheme(stored);
      return;
    }
    applyTheme('light');
  }

  function toggleTheme() {
    const next = html.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem(THEME_KEY, next);
  }

  function onScroll() {
    const y = window.scrollY || window.pageYOffset;
    if (header) {
      header.classList.toggle('is-scrolled', y > 16);
    }
    if (progress) {
      const doc = document.documentElement;
      const total = doc.scrollHeight - doc.clientHeight;
      progress.style.width = (total > 0 ? (y / total) * 100 : 0) + '%';
    }
  }

  function closeMobileNav() {
    if (!mobileNav || !menuBtn) return;
    mobileNav.classList.remove('is-open');
    menuBtn.setAttribute('aria-expanded', 'false');
  }

  function toggleMobileNav() {
    if (!mobileNav || !menuBtn) return;
    const open = mobileNav.classList.toggle('is-open');
    menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  function initReveal() {
    const revealElements = document.querySelectorAll('.lp-reveal');
    if (!revealElements.length) return;

    function onRevealVisible(element) {
      element.classList.add('is-visible');
      if (element.id === 'lpWorkflow') {
        initWorkflow(true);
      }
      if (element.id === 'lpBubbleField') {
        initFeatureBubbles(element);
      }
    }

    if (!('IntersectionObserver' in window)) {
      revealElements.forEach(onRevealVisible);
      return;
    }

    const revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            onRevealVisible(entry.target);
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { root: null, rootMargin: '0px 0px -6% 0px', threshold: 0.06 }
    );

    revealElements.forEach(function (element) {
      revealObserver.observe(element);
    });
  }

  function initFeatureBubbles(bubbleField) {
    if (!bubbleField || bubbleField.dataset.bubblesInit === '1') return;
    bubbleField.dataset.bubblesInit = '1';
    bubbleField.classList.add('is-visible');

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      bubbleField.classList.add('is-animated');
      return;
    }

    window.setTimeout(function () {
      bubbleField.classList.add('is-animated');
    }, 400);
  }

  var workflowTimer = null;

  function initWorkflow(immediate) {
    var workflow = document.getElementById('lpWorkflow');
    if (!workflow || workflow.classList.contains('is-animated')) return;

    function start() {
      workflow.classList.add('is-animated');
      var steps = workflow.querySelectorAll('.lp-workflow-step');
      if (!steps.length) return;

      var index = 0;
      steps[index].classList.add('is-active');

      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        steps.forEach(function (step) {
          step.classList.add('is-active');
        });
        return;
      }

      workflowTimer = window.setInterval(function () {
        steps.forEach(function (step) {
          step.classList.remove('is-active');
        });
        index = (index + 1) % steps.length;
        steps[index].classList.add('is-active');
      }, 2800);
    }

    if (immediate) {
      start();
      return;
    }

    window.setTimeout(start, 120);
  }

  window.addEventListener('beforeunload', function () {
    if (workflowTimer) window.clearInterval(workflowTimer);
  });

  initTheme();
  document.body.classList.add('is-loaded');
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }

  if (menuBtn) {
    menuBtn.addEventListener('click', toggleMobileNav);
  }

  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const id = this.getAttribute('href');
      if (id.length > 1) {
        const target = document.querySelector(id);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          closeMobileNav();
        }
      }
    });
  });

  initReveal();

  if (window.location.search.indexOf('signed_out=1') !== -1) {
    if (window.ReportFlowToast) {
      window.ReportFlowToast.info('You have been signed out.');
    }
    if (window.history.replaceState) {
      var clean = window.location.pathname + window.location.hash;
      window.history.replaceState({ lp: true }, '', clean);
    }
  }
})();
