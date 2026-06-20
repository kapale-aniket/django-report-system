/**
 * Drag & drop + browse for report file input (PDF or DOCX).
 */
(function () {
  var input = document.getElementById('report-file-input') || document.querySelector('#reportSubmitForm input[name="file"]');
  var zone = document.getElementById('report-dropzone');
  var nameEl = document.getElementById('report-file-name');
  if (!input || !zone) return;

  var allowedTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ];

  function isAllowedFile(file) {
    if (!file) return false;
    var name = (file.name || '').toLowerCase();
    if (name.endsWith('.pdf') || name.endsWith('.docx')) return true;
    return allowedTypes.indexOf(file.type) !== -1;
  }

  function showName(file) {
    if (nameEl) nameEl.textContent = file ? file.name : '';
  }

  function assignFile(file) {
    if (!file || !isAllowedFile(file)) {
      if (window.ReportFlowToast) {
        window.ReportFlowToast.warning('Please choose a PDF or DOCX file.', { title: false });
      }
      return;
    }
    try {
      var transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
    } catch (err) {
      return;
    }
    showName(file);
  }

  input.addEventListener('change', function () {
    if (input.files && input.files[0]) {
      if (!isAllowedFile(input.files[0])) {
        input.value = '';
        showName(null);
        if (window.ReportFlowToast) {
          window.ReportFlowToast.warning('Please choose a PDF or DOCX file.', { title: false });
        }
        return;
      }
      showName(input.files[0]);
    }
  });

  ['dragenter', 'dragover'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.add('app-dropzone--active');
    });
  });

  ['dragleave', 'drop'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault();
      e.stopPropagation();
      zone.classList.remove('app-dropzone--active');
    });
  });

  zone.addEventListener('drop', function (e) {
    var dt = e.dataTransfer;
    if (!dt || !dt.files || !dt.files[0]) return;
    e.preventDefault();
    assignFile(dt.files[0]);
  });
})();
