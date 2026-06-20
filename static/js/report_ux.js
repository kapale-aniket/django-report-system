/**
 * Report detail: keyboard shortcuts (A / R), collapsible prefs via localStorage.
 */
(function () {
  'use strict';

  document.addEventListener('keydown', function (keyboardEvent) {
    if (!keyboardEvent.key || keyboardEvent.ctrlKey || keyboardEvent.metaKey || keyboardEvent.altKey) return;
    var focusedElement = keyboardEvent.target;
    if (
      focusedElement &&
      (focusedElement.tagName === 'INPUT' ||
        focusedElement.tagName === 'TEXTAREA' ||
        focusedElement.isContentEditable)
    ) {
      return;
    }
    var pressedKey = keyboardEvent.key.toLowerCase();
    if (pressedKey === 'a') {
      var teacherApproveForm = document.getElementById('teacherApproveForm');
      if (teacherApproveForm) {
        keyboardEvent.preventDefault();
        teacherApproveForm.scrollIntoView({ behavior: 'smooth' });
      }
    }
    if (pressedKey === 'r') {
      var teacherRejectModal = document.getElementById('teacherRejectModal');
      if (teacherRejectModal && window.bootstrap) {
        keyboardEvent.preventDefault();
        new bootstrap.Modal(teacherRejectModal).show();
      }
    }
  });

  var dashboardCollapseStorageKey = 'pr_dashboard_collapsed_sections';
  document.querySelectorAll('[data-collapse-section]').forEach(function (collapseButton) {
    var sectionId = collapseButton.getAttribute('data-collapse-section');
    var sectionElement = document.getElementById(sectionId);
    if (!sectionElement) return;
    try {
      var collapsedSections = JSON.parse(localStorage.getItem(dashboardCollapseStorageKey) || '{}');
      if (collapsedSections[sectionId]) sectionElement.classList.add('d-none');
    } catch (storageError) {}
    collapseButton.addEventListener('click', function () {
      sectionElement.classList.toggle('d-none');
      try {
        var updatedCollapsedSections = JSON.parse(localStorage.getItem(dashboardCollapseStorageKey) || '{}');
        updatedCollapsedSections[sectionId] = sectionElement.classList.contains('d-none');
        localStorage.setItem(dashboardCollapseStorageKey, JSON.stringify(updatedCollapsedSections));
      } catch (storageError) {}
    });
  });
})();
