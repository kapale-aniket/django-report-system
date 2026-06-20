/**
 * Certificate verification — decode QR codes from uploaded images/PDFs and verify.
 */
(function () {
  'use strict';

  const scanButton = document.getElementById('scanQrButton');
  const qrImageInput = document.getElementById('qrImageInput');
  const scanStatus = document.getElementById('scanStatus');
  const certificateCodeInput = document.getElementById('certificateCodeInput');
  const verifyForm = document.getElementById('certificateVerifyForm');

  if (!scanButton || !qrImageInput || typeof jsQR !== 'function') {
    return;
  }

  const verifyPagePath = verifyForm?.dataset.verifyUrl || '/certificates/verify/';
  const QR_OPTIONS = { inversionAttempts: 'attemptBoth' };
  const MAX_SCAN_DIMENSION = 2600;

  if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js';
  }

  function setScanStatus(message, type) {
    if (!scanStatus) {
      return;
    }
    scanStatus.textContent = message;
    scanStatus.className = 'cert-scan-status cert-scan-status--' + (type || 'info');
    scanStatus.hidden = !message;
  }

  function extractVerificationCode(qrPayload) {
    const trimmed = (qrPayload || '').trim();
    if (!trimmed) {
      return null;
    }

    try {
      const parsedUrl = new URL(trimmed, window.location.origin);
      const codeFromQuery = parsedUrl.searchParams.get('code');
      if (codeFromQuery) {
        return codeFromQuery.trim();
      }
    } catch (_error) {
      /* Not a URL — fall through to raw code handling. */
    }

    const codeMatch = trimmed.match(/[?&]code=([^&]+)/i);
    if (codeMatch) {
      return decodeURIComponent(codeMatch[1]).trim();
    }

    if (/^[A-Za-z0-9_-]{8,}$/.test(trimmed)) {
      return trimmed;
    }

    return null;
  }

  function isPdfFile(file) {
    if (file.type === 'application/pdf') {
      return true;
    }
    return (file.name || '').toLowerCase().endsWith('.pdf');
  }

  function isImageFile(file) {
    return file.type.startsWith('image/');
  }

  function isAcceptedScanFile(file) {
    return isImageFile(file) || isPdfFile(file);
  }

  function loadImageFromFile(imageFile) {
    return new Promise(function (resolve, reject) {
      const fileReader = new FileReader();
      fileReader.onload = function (loadEvent) {
        const imageElement = new Image();
        imageElement.onload = function () {
          resolve(imageElement);
        };
        imageElement.onerror = function () {
          reject(new Error('Could not load the selected image.'));
        };
        imageElement.src = loadEvent.target.result;
      };
      fileReader.onerror = function () {
        reject(new Error('Could not read the selected file.'));
      };
      fileReader.readAsDataURL(imageFile);
    });
  }

  function drawToCanvas(source, maxDimension) {
    const width = source.width || source.naturalWidth;
    const height = source.height || source.naturalHeight;
    let targetWidth = width;
    let targetHeight = height;

    if (Math.max(targetWidth, targetHeight) > maxDimension) {
      const scale = maxDimension / Math.max(targetWidth, targetHeight);
      targetWidth = Math.floor(targetWidth * scale);
      targetHeight = Math.floor(targetHeight * scale);
    }

    const canvas = document.createElement('canvas');
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const canvasContext = canvas.getContext('2d', { willReadFrequently: true });
    canvasContext.drawImage(source, 0, 0, targetWidth, targetHeight);
    return canvas;
  }

  function resizeCanvas(sourceCanvas, scaleFactor) {
    const targetWidth = Math.max(1, Math.floor(sourceCanvas.width * scaleFactor));
    const targetHeight = Math.max(1, Math.floor(sourceCanvas.height * scaleFactor));
    const canvas = document.createElement('canvas');
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const canvasContext = canvas.getContext('2d', { willReadFrequently: true });
    canvasContext.drawImage(sourceCanvas, 0, 0, targetWidth, targetHeight);
    return canvas;
  }

  function scanCanvasRegions(canvas) {
    const canvasContext = canvas.getContext('2d', { willReadFrequently: true });
    const width = canvas.width;
    const height = canvas.height;
    const cornerWidth = Math.floor(width * 0.42);
    const cornerHeight = Math.floor(height * 0.42);

    const regions = [
      { x: width - cornerWidth, y: height - cornerHeight, w: cornerWidth, h: cornerHeight, label: 'bottom-right' },
      { x: 0, y: 0, w: width, h: height, label: 'full' },
      { x: width - cornerWidth, y: 0, w: cornerWidth, h: cornerHeight, label: 'top-right' },
      { x: 0, y: height - cornerHeight, w: cornerWidth, h: cornerHeight, label: 'bottom-left' },
      { x: 0, y: 0, w: cornerWidth, h: cornerHeight, label: 'top-left' },
    ];

    for (let regionIndex = 0; regionIndex < regions.length; regionIndex += 1) {
      const region = regions[regionIndex];
      const imageData = canvasContext.getImageData(region.x, region.y, region.w, region.h);
      const decoded = jsQR(imageData.data, imageData.width, imageData.height, QR_OPTIONS);
      if (decoded && decoded.data) {
        return decoded;
      }
    }

    return null;
  }

  function decodeQrFromCanvas(canvas) {
    const scaleFactors = [1, 1.35, 0.75, 1.6];
    for (let scaleIndex = 0; scaleIndex < scaleFactors.length; scaleIndex += 1) {
      const scaleFactor = scaleFactors[scaleIndex];
      const scanCanvas = scaleFactor === 1 ? canvas : resizeCanvas(canvas, scaleFactor);
      const decoded = scanCanvasRegions(scanCanvas);
      if (decoded) {
        return decoded;
      }
    }
    return null;
  }

  function decodeQrFromImage(imageElement) {
    const canvas = drawToCanvas(imageElement, MAX_SCAN_DIMENSION);
    return decodeQrFromCanvas(canvas);
  }

  async function renderPdfToCanvas(pdfFile, renderScale) {
    if (typeof pdfjsLib === 'undefined') {
      throw new Error('PDF scanning is not available in this browser. Enter the certificate ID manually.');
    }

    const pdfBytes = await pdfFile.arrayBuffer();
    const pdfDocument = await pdfjsLib.getDocument({ data: pdfBytes }).promise;
    const page = await pdfDocument.getPage(1);
    const viewport = page.getViewport({ scale: renderScale });
    const canvas = document.createElement('canvas');
    canvas.width = Math.floor(viewport.width);
    canvas.height = Math.floor(viewport.height);
    const canvasContext = canvas.getContext('2d', { willReadFrequently: true });
    await page.render({ canvasContext: canvasContext, viewport: viewport }).promise;
    return canvas;
  }

  async function fileToScanCanvas(file) {
    if (isPdfFile(file)) {
      const renderScales = [2.25, 3, 1.75];
      for (let scaleIndex = 0; scaleIndex < renderScales.length; scaleIndex += 1) {
        const canvas = await renderPdfToCanvas(file, renderScales[scaleIndex]);
        const normalized = drawToCanvas(canvas, MAX_SCAN_DIMENSION);
        const decoded = decodeQrFromCanvas(normalized);
        if (decoded) {
          return { canvas: normalized, decoded: decoded };
        }
      }
      return { canvas: await renderPdfToCanvas(file, 2.25), decoded: null };
    }

    const imageElement = await loadImageFromFile(file);
    const canvas = drawToCanvas(imageElement, MAX_SCAN_DIMENSION);
    return { canvas: canvas, decoded: decodeQrFromCanvas(canvas) };
  }

  function buildVerifyUrl(verificationCode) {
    const params = new URLSearchParams();
    params.set('code', verificationCode);
    const next = new URLSearchParams(window.location.search).get('next');
    if (next && next.startsWith('/') && !next.startsWith('//')) {
      params.set('next', next);
    }
    return verifyPagePath + '?' + params.toString();
  }

  function redirectToVerify(verificationCode) {
    if (certificateCodeInput) {
      certificateCodeInput.value = verificationCode;
    }
    setScanStatus('QR recognized — verifying certificate…', 'success');
    if (window.ReportFlowLoader) {
      window.ReportFlowLoader.show({
        message: 'Verifying certificate…',
        submessage: 'Please wait.',
        immediate: true,
        delay: 0,
      });
    }
    window.location.assign(buildVerifyUrl(verificationCode));
  }

  scanButton.addEventListener('click', function () {
    qrImageInput.click();
  });

  qrImageInput.addEventListener('change', async function () {
    const selectedFile = qrImageInput.files && qrImageInput.files[0];
    qrImageInput.value = '';

    if (!selectedFile) {
      return;
    }

    if (!isAcceptedScanFile(selectedFile)) {
      setScanStatus('Please upload an image (JPG, PNG) or PDF certificate file.', 'danger');
      return;
    }

    scanButton.disabled = true;
    if (window.ReportFlowLoader) {
      window.ReportFlowLoader.setButtonLoading(scanButton, true, 'Scanning…');
    }
    setScanStatus(
      isPdfFile(selectedFile) ? 'Reading PDF and scanning for QR code…' : 'Scanning image for QR code…',
      'info'
    );

    try {
      const scanResult = await fileToScanCanvas(selectedFile);
      const decodedQr = scanResult.decoded || decodeQrFromCanvas(scanResult.canvas);

      if (!decodedQr || !decodedQr.data) {
        setScanStatus(
          'No QR code found. Upload a clear photo or PDF of the full certificate — the QR is usually in the bottom-right corner.',
          'danger'
        );
        return;
      }

      const verificationCode = extractVerificationCode(decodedQr.data);
      if (!verificationCode) {
        setScanStatus('QR code found, but it is not a valid ReportFlow certificate link.', 'danger');
        return;
      }

      redirectToVerify(verificationCode);
    } catch (error) {
      setScanStatus(error.message || 'Could not scan this file. Please try again.', 'danger');
    } finally {
      if (window.ReportFlowLoader) {
        window.ReportFlowLoader.setButtonLoading(scanButton, false);
      } else {
        scanButton.disabled = false;
      }
    }
  });
})();
