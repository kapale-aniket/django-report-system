(function () {
  'use strict';

  function toast(msg, type) {
    if (window.ReportFlowAPI && window.ReportFlowAPI.showToast) {
      window.ReportFlowAPI.showToast(msg, type || 'info');
    }
  }

  document.querySelectorAll('[data-qa-suggest]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!window.ReportFlowAPI) return;
      var questionId = btn.getAttribute('data-question-id');
      var questionType = btn.getAttribute('data-question-type') || 'user';
      var textareaId = btn.getAttribute('data-target-textarea');
      var textarea = textareaId ? document.getElementById(textareaId) : null;
      if (!textarea) return;

      if (window.ReportFlowLoader) {
        window.ReportFlowLoader.setButtonLoading(btn, true, 'Generating reply…');
      }

      window.ReportFlowAPI.apiFetch('/api/v1/qa/suggest-reply/', {
        method: 'POST',
        body: JSON.stringify({
          question_id: parseInt(questionId, 10),
          question_type: questionType,
        }),
        loaderMessage: 'Generating suggested reply…',
        loaderSubmessage: 'Please wait.',
        loaderImmediate: true,
      })
        .then(function (result) {
          var answer = (result.data && result.data.suggested_answer) || '';
          textarea.value = answer;
          textarea.focus();
          toast(result.message || 'Suggested reply ready — edit before sending.', 'success');
        })
        .catch(function (err) {
          toast(window.ReportFlowAPI.formatApiError(err, 'Could not suggest reply'), 'error');
        })
        .finally(function () {
          if (window.ReportFlowLoader) {
            window.ReportFlowLoader.setButtonLoading(btn, false);
          }
        });
    });
  });
})();
