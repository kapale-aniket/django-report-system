(function () {
  'use strict';

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^|;)\\s*' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  function normalizeHexColor(value) {
    if (!value) {
      return '';
    }
    var raw = String(value).trim().toLowerCase();
    if (raw.charAt(0) === '#') {
      raw = raw.slice(1).replace(/[^0-9a-f]/g, '');
    }
    if (raw.length >= 6) {
      return '#' + raw.slice(0, 6);
    }
    return value;
  }

  function setFieldValue(id, value) {
    var input = document.getElementById(id);
    if (!input || value === undefined || value === null) {
      return;
    }
    if (input.type === 'checkbox') {
      input.checked = !!value;
      return;
    }
    if (input.type === 'color') {
      input.value = normalizeHexColor(value);
      return;
    }
    input.value = value;
  }

  function setCheckbox(id, value) {
    var input = document.getElementById(id);
    if (input) {
      input.checked = !!value;
    }
  }

  function showToast(message, type) {
    if (window.ReportFlowToast) {
      window.ReportFlowToast.show(message, type || 'info');
    }
  }

  function applyAnalysis(data) {
    if (!data) {
      return;
    }
    setFieldValue('id_accent_color', data.accent_color);
    setFieldValue('id_secondary_color', data.secondary_color);
    setFieldValue('id_background_color', data.background_color);
    setFieldValue('id_text_color', data.text_color);
    setFieldValue('id_muted_color', data.muted_color);
    setFieldValue('id_border_color', data.border_color || data.accent_color);
    setFieldValue('id_name_color', data.name_color || data.accent_color);
    setCheckbox('id_use_reference_background', data.use_reference_background !== false);

    var design = data.design || {};
    var border = design.border || {};
    var background = design.background || {};
    var typography = design.typography || {};
    var layout = design.layout || {};
    var decorative = design.decorative || {};
    var signatures = design.signatures || {};
    var page = design.page || {};

    setFieldValue('id_border_style', border.style);
    setFieldValue('id_border_width', border.width);
    setFieldValue('id_border_radius', border.radius);
    setFieldValue('id_border_pattern', border.pattern);
    setFieldValue('id_background_mode', background.mode || 'image');
    setFieldValue('id_background_opacity', background.opacity);
    setFieldValue('id_title_font', typography.title_font);
    setFieldValue('id_recipient_font', typography.recipient_font);
    setFieldValue('id_body_font', typography.body_font);
    setFieldValue('id_font_size', typography.font_size);
    setFieldValue('id_font_weight', typography.font_weight);
    setFieldValue('id_text_alignment', typography.text_alignment);
    setFieldValue('id_name_font', typography.name_font);
    setFieldValue('id_name_size', typography.name_size);
    setFieldValue('id_name_underline', typography.name_underline);
    setFieldValue('id_margin_cm', layout.margin_cm);
    setFieldValue('id_padding_cm', layout.padding_cm);
    setFieldValue('id_header_position', layout.header_position);
    setFieldValue('id_logo_position', layout.logo_position);
    setFieldValue('id_title_position', layout.title_position);
    setFieldValue('id_name_position', layout.name_position);
    setFieldValue('id_footer_position', layout.footer_position);
    setCheckbox('id_decorative_gold_seal', decorative.gold_seal);
    setCheckbox('id_decorative_ribbon', decorative.ribbon);
    setCheckbox('id_decorative_laurel', decorative.laurel_wreath);
    setCheckbox('id_decorative_trophy', decorative.trophy_icon);
    setCheckbox('id_decorative_star', decorative.star_badge);
    setCheckbox('id_decorative_corners', decorative.corner_decorations);
    setFieldValue('id_signature_count', signatures.count);
    var signatories = signatures.signatories || [];
    if (signatories[0]) {
      setFieldValue('id_sig1_name', signatories[0].name);
      setFieldValue('id_sig1_designation', signatories[0].designation);
    }
    if (signatories[1]) {
      setFieldValue('id_sig2_name', signatories[1].name);
      setFieldValue('id_sig2_designation', signatories[1].designation);
    }
    if (signatories[2]) {
      setFieldValue('id_sig3_name', signatories[2].name);
      setFieldValue('id_sig3_designation', signatories[2].designation);
    }
    setFieldValue('id_page_size', page.size);
    setFieldValue('id_custom_width_mm', page.custom_width_mm);
    setFieldValue('id_custom_height_mm', page.custom_height_mm);
    syncCustomSizeFields(document.getElementById('id_page_size'));
  }

  function syncCustomSizeFields(pageSizeSelect) {
    if (!pageSizeSelect) {
      return;
    }
    var showCustom = pageSizeSelect.value === 'custom';
    document.querySelectorAll('.cert-custom-size-field').forEach(function (el) {
      el.classList.toggle('d-none', !showCustom);
    });
  }

  function initCertificateDesigner() {
    var form = document.getElementById('certificateTemplateForm');
    if (!form) {
      return;
    }

    var modeInputs = form.querySelectorAll('input[name="creation_mode"]');
    var fromImagePanel = document.getElementById('certFromImagePanel');
    var fromScratchPanel = document.getElementById('certFromScratchPanel');
    var pageSizeSelect = document.getElementById('id_page_size');
    var referenceInput = document.getElementById('id_reference_image');
    var generateBtn = document.getElementById('certGenerateFromImageBtn');
    var previewDraftBtn = document.getElementById('certPreviewDraftBtn');
    var generateStatus = document.getElementById('certGenerateStatus');
    var previewWrap = document.getElementById('certImagePreviewWrap');
    var previewImg = document.getElementById('certImagePreview');
    var generatedHint = document.getElementById('certGeneratedHint');
    var imagesTabHint = document.getElementById('certImagesTabReferenceHint');
    var analyzeUrl = form.getAttribute('data-analyze-url');
    var previewDraftUrl = form.getAttribute('data-preview-draft-url');
    var backgroundMode = document.getElementById('id_background_mode');
    var useReferenceBg = document.getElementById('id_use_reference_background');

    function selectedMode() {
      var checked = form.querySelector('input[name="creation_mode"]:checked');
      return checked ? checked.value : 'from_image';
    }

    function syncModePanels() {
      var mode = selectedMode();
      if (fromImagePanel) {
        fromImagePanel.classList.toggle('d-none', mode !== 'from_image');
      }
      if (fromScratchPanel) {
        fromScratchPanel.classList.toggle('d-none', mode !== 'from_scratch');
      }
    }

    function syncReferenceHint() {
      if (!imagesTabHint || !referenceInput) {
        return;
      }
      var file = referenceInput.files && referenceInput.files[0];
      if (file) {
        imagesTabHint.textContent = file.name;
      } else if (referenceInput.value) {
        imagesTabHint.textContent = 'Current image kept from saved template';
      } else {
        imagesTabHint.textContent = 'No background image selected';
      }
    }

    function showLocalPreview(file) {
      if (!file || !previewWrap || !previewImg) {
        return;
      }
      var reader = new FileReader();
      reader.onload = function (ev) {
        previewImg.src = ev.target.result;
        previewWrap.classList.remove('d-none');
      };
      reader.readAsDataURL(file);
    }

    modeInputs.forEach(function (input) {
      input.addEventListener('change', syncModePanels);
    });

    if (pageSizeSelect) {
      pageSizeSelect.addEventListener('change', function () {
        syncCustomSizeFields(pageSizeSelect);
      });
    }

    if (referenceInput) {
      referenceInput.addEventListener('change', function () {
        var file = referenceInput.files && referenceInput.files[0];
        syncReferenceHint();
        if (file) {
          showLocalPreview(file);
        }
      });
    }

    if (generateBtn) {
      generateBtn.addEventListener('click', async function () {
        var file = referenceInput && referenceInput.files && referenceInput.files[0];
        if (!file) {
          showToast('Choose a clear reference certificate image first (PNG, JPG, or WEBP).', 'error');
          return;
        }
        generateBtn.disabled = true;
        if (generateStatus) {
          generateStatus.textContent = 'Analyzing image…';
        }
        try {
          var body = new FormData();
          body.append('reference_image', file);
          var csrf = getCookie('csrftoken');
          var response = await fetch(analyzeUrl, {
            method: 'POST',
            body: body,
            headers: csrf ? { 'X-CSRFToken': csrf } : {},
            credentials: 'same-origin',
          });
          var payload = await response.json();
          if (!payload.success) {
            throw new Error(payload.message || 'Could not generate a template from this image.');
          }
          applyAnalysis(payload.data || {});
          if (backgroundMode && !payload.data.design) {
            backgroundMode.value = 'image';
          }
          if (useReferenceBg) {
            useReferenceBg.checked = true;
          }
          if (generatedHint) {
            generatedHint.classList.remove('d-none');
          }
          showToast(payload.message || 'Template generated from image.', 'success');
          if (generateStatus) {
            generateStatus.textContent = 'Ready — edit tabs, preview, or save.';
          }
        } catch (err) {
          showToast(err.message || 'Could not generate template from this image.', 'error');
          if (generateStatus) {
            generateStatus.textContent = '';
          }
        } finally {
          generateBtn.disabled = false;
        }
      });
    }

    if (previewDraftBtn) {
      previewDraftBtn.addEventListener('click', async function () {
        previewDraftBtn.disabled = true;
        try {
          var formData = new FormData(form);
          formData.delete('save_certificate_template');
          var csrf = getCookie('csrftoken');
          var response = await fetch(previewDraftUrl, {
            method: 'POST',
            body: formData,
            headers: csrf ? { 'X-CSRFToken': csrf } : {},
            credentials: 'same-origin',
          });
          var contentType = response.headers.get('Content-Type') || '';
          if (contentType.indexOf('application/pdf') !== -1) {
            var blob = await response.blob();
            var blobUrl = URL.createObjectURL(blob);
            window.open(blobUrl, '_blank', 'noopener');
            showToast('Preview opened in a new tab.', 'success');
            return;
          }
          var payload = await response.json();
          throw new Error((payload && payload.message) || 'Could not preview this template.');
        } catch (err) {
          showToast(err.message || 'Preview failed. Check your template settings.', 'error');
        } finally {
          previewDraftBtn.disabled = false;
        }
      });
    }

    syncModePanels();
    syncCustomSizeFields(pageSizeSelect);
    syncReferenceHint();

    if (
      window.location.search.indexOf('cert_template=') !== -1 ||
      window.location.search.indexOf('new_template=') !== -1
    ) {
      var modalEl = document.getElementById('certificateTemplateModal');
      if (modalEl && window.bootstrap && window.bootstrap.Modal) {
        window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
      }
    }
  }

  document.addEventListener('DOMContentLoaded', initCertificateDesigner);
})();
