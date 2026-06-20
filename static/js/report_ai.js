(function () {
  'use strict';

  var panel = document.getElementById('reportAiPanel');
  if (!panel) return;

  var reportId = panel.getAttribute('data-report-id');
  var loadBtn = document.getElementById('reportAiLoadBtn');
  var applyBtn = document.getElementById('reportAiApplyBtn');
  var rerunBtn = document.getElementById('reportAiRerunBtn');
  var summaryEl = document.getElementById('reportAiSummary');
  var ocrEl = document.getElementById('reportAiOcrStatus');
  var statusEl = document.getElementById('reportAiStatus');
  var latestPayload = null;

  function toast(msg, type) {
    if (window.ReportFlowAPI && window.ReportFlowAPI.showToast) {
      window.ReportFlowAPI.showToast(msg, type || 'info');
    }
  }

  function setAiButtonsDisabled(disabled) {
    [loadBtn, applyBtn, rerunBtn].forEach(function (btn) {
      if (btn) {
        btn.disabled = disabled;
      }
    });
    if (applyBtn && !disabled && latestPayload) {
      applyBtn.disabled = !(latestPayload.suggested_criterion_scores && Object.keys(latestPayload.suggested_criterion_scores).length);
    }
  }

  function formatOcrBadge(ocr) {
    if (!ocr || !Object.keys(ocr).length) return 'OCR check pending';
    var verified = ocr.verified ? 'Verified' : 'Review recommended';
    var confidence = ocr.confidence ? ' · ' + ocr.confidence + ' confidence' : '';
    var ratio = ocr.similarity_ratio != null ? ' · match ' + Math.round(ocr.similarity_ratio * 100) + '%' : '';
    return verified + confidence + ratio;
  }

  function renderPayload(payload) {
    latestPayload = payload;
    if (summaryEl) summaryEl.textContent = payload.summary || 'No summary available yet.';
    if (ocrEl) {
      ocrEl.textContent = formatOcrBadge(payload.ocr_verification || {});
      ocrEl.className = 'badge rounded-pill ' + ((payload.ocr_verification || {}).verified ? 'text-bg-success' : 'text-bg-warning');
    }
    if (statusEl) {
      statusEl.textContent = (payload.processing_status || 'unknown') + (payload.provider ? ' · ' + payload.provider : '');
    }
    if (applyBtn) applyBtn.disabled = !(payload.suggested_criterion_scores && Object.keys(payload.suggested_criterion_scores).length);
  }

  function fetchSuggestions(options) {
    options = options || {};
    if (!window.ReportFlowAPI) return Promise.reject(new Error('API unavailable'));

    if (window.ReportFlowLoader) {
      window.ReportFlowLoader.setMessage(
        options.message || 'Loading AI insights…',
        options.submessage || 'Please wait.'
      );
    }
    if (options.disableButtons !== false) {
      setAiButtonsDisabled(true);
    }

    return window.ReportFlowAPI.apiFetch('/api/v1/reports/' + reportId + '/ai-suggestions/', {
      method: 'GET',
      loader: options.useGlobalLoader !== false,
      loaderMessage: options.message || 'Loading AI insights…',
      loaderSubmessage: options.submessage || 'Please wait.',
      loaderImmediate: true,
    })
      .then(function (result) {
        renderPayload(result.data || {});
        if (options.showSuccessToast !== false) {
          toast(result.message || 'AI insights loaded', 'success');
        }
        return result;
      })
      .catch(function (err) {
        var msg = window.ReportFlowAPI.formatApiError
          ? window.ReportFlowAPI.formatApiError(err, 'Could not load AI insights')
          : 'Could not load AI insights';
        toast(msg, 'error');
        throw err;
      })
      .finally(function () {
        if (options.disableButtons !== false) {
          setAiButtonsDisabled(false);
        }
      });
  }

  function applySuggestions() {
    if (!latestPayload) return;
    var scores = latestPayload.suggested_criterion_scores || {};
    Object.keys(scores).forEach(function (id) {
      var input = document.querySelector('[name="criterion_' + id + '"]');
      if (input) input.value = scores[id];
    });
    var marks = document.querySelector('#teacherApproveForm [name="teacher_marks"]');
    if (marks && latestPayload.suggested_teacher_marks != null) {
      marks.value = latestPayload.suggested_teacher_marks;
    }
    var feedback = document.querySelector('#teacherApproveForm [name="feedback"]');
    if (feedback && latestPayload.suggested_feedback) {
      feedback.value = latestPayload.suggested_feedback;
    }
    toast('AI suggestions applied — please review before approving.', 'success');
  }

  function rerunAnalysis() {
    if (!window.ReportFlowAPI || !window.ReportFlowLoader) return;

    setAiButtonsDisabled(true);
    window.ReportFlowLoader.show({
      message: 'Analyzing report…',
      submessage: 'Extracting text · generating summary · checking weaknesses…',
      immediate: true,
      delay: 0,
    });

    window.ReportFlowAPI.apiFetch('/api/v1/reports/' + reportId + '/ai-process/', {
      method: 'POST',
      body: '{}',
      loader: false,
    })
      .then(function (result) {
        window.ReportFlowLoader.setMessage('Extracting text from document…', 'Please wait.');
        return window.ReportFlowAPI.apiFetch('/api/v1/reports/' + reportId + '/ai-suggestions/', {
          method: 'GET',
          loader: false,
        });
      })
      .then(function (result) {
        renderPayload(result.data || {});
        toast(result.message || 'AI analysis completed', 'success');
      })
      .catch(function (err) {
        toast(window.ReportFlowAPI.formatApiError(err, 'Could not complete AI analysis'), 'error');
      })
      .finally(function () {
        window.ReportFlowLoader.hide();
        setAiButtonsDisabled(false);
      });
  }

  if (loadBtn) {
    loadBtn.addEventListener('click', function () {
      fetchSuggestions();
    });
  }
  if (applyBtn) applyBtn.addEventListener('click', applySuggestions);
  if (rerunBtn) rerunBtn.addEventListener('click', rerunAnalysis);

  if (panel.getAttribute('data-auto-load') === 'true') {
    fetchSuggestions({ showSuccessToast: false });
  }
})();
