(function () {
  'use strict';

  var ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
  var MAX_PHOTO_BYTES = 2 * 1024 * 1024;
  var CROPPED_PHOTO_SIZE = 512;

  var profilePhotoCropper = null;

  function toast(msg, type) {
    if (window.ReportFlowAPI && window.ReportFlowAPI.showToast) {
      window.ReportFlowAPI.showToast(msg, type || 'info');
    }
  }

  function setButtonLoading(button, loading) {
    if (window.ReportFlowLoader) {
      window.ReportFlowLoader.setButtonLoading(button, loading);
    }
  }

  function initialsFromProfile(data) {
    var name = ((data.first_name || '') + ' ' + (data.last_name || '')).trim();
    if (name) {
      return name.split(/\s+/).slice(0, 2).map(function (p) { return p.charAt(0); }).join('').toUpperCase();
    }
    return (data.username || 'U').slice(0, 2).toUpperCase();
  }

  function setPhotoPreview(url, fallbackText) {
    var preview = document.getElementById('profilePhotoPreview');
    var fallback = document.getElementById('profilePhotoFallback');
    if (!preview || !fallback) return;
    if (url) {
      preview.src = url;
      preview.classList.remove('d-none');
      fallback.classList.add('d-none');
    } else {
      preview.src = '';
      preview.classList.add('d-none');
      fallback.textContent = fallbackText || 'U';
      fallback.classList.remove('d-none');
    }
  }

  function fillProfileForm(data) {
    document.getElementById('profileUsername').value = data.username || '';
    document.getElementById('profileEmail').value = data.email || '';
    document.getElementById('profileFirstName').value = data.first_name || '';
    document.getElementById('profileLastName').value = data.last_name || '';
    setPhotoPreview(data.profile_photo || '', initialsFromProfile(data));
  }

  function updateNavAvatars(url, fallbackText) {
    document.querySelectorAll('.app-user-avatar[data-rf-nav-avatar]').forEach(function (node) {
      if (url) {
        if (node.tagName === 'IMG') {
          node.src = url;
        } else {
          var img = document.createElement('img');
          img.src = url;
          img.alt = '';
          img.className = node.className + ' app-user-avatar--photo';
          img.setAttribute('data-rf-nav-avatar', '1');
          node.replaceWith(img);
        }
      } else if (node.tagName !== 'IMG') {
        node.textContent = fallbackText;
      }
    });
  }

  function destroyPhotoCropper() {
    if (profilePhotoCropper) {
      profilePhotoCropper.destroy();
      profilePhotoCropper = null;
    }
  }

  function showPhotoCropPanel(show) {
    var display = document.getElementById('profilePhotoDisplay');
    var cropPanel = document.getElementById('profilePhotoCropPanel');
    if (display) display.classList.toggle('d-none', show);
    if (cropPanel) cropPanel.classList.toggle('d-none', !show);
  }

  function resetPhotoFileInput() {
    var photoInput = document.getElementById('profilePhotoInput');
    if (photoInput) photoInput.value = '';
  }

  function clearPendingProfilePhoto() {
    resetPhotoFileInput();
  }

  function cancelPhotoCrop() {
    destroyPhotoCropper();
    var cropImage = document.getElementById('profilePhotoCropImage');
    if (cropImage) cropImage.src = '';
    resetPhotoFileInput();
    showPhotoCropPanel(false);
  }

  function validateSelectedPhotoFile(file) {
    if (!file) {
      return 'No photo selected.';
    }
    if (ALLOWED_PHOTO_TYPES.indexOf(file.type) === -1) {
      return 'Photo must be JPG, PNG, WEBP, or GIF.';
    }
    if (file.size > MAX_PHOTO_BYTES) {
      return 'Photo must be 2 MB or smaller.';
    }
    return '';
  }

  function canvasToPhotoFile(canvas, quality, callback) {
    canvas.toBlob(function (blob) {
      if (!blob) {
        callback(null);
        return;
      }
      if (blob.size <= MAX_PHOTO_BYTES || quality <= 0.5) {
        callback(new File([blob], 'profile-photo.jpg', { type: 'image/jpeg' }));
        return;
      }
      canvasToPhotoFile(canvas, Math.max(0.5, quality - 0.08), callback);
    }, 'image/jpeg', quality);
  }

  function applyCroppedPhoto() {
    if (!profilePhotoCropper) {
      toast('Could not crop this photo. Try another image.', 'error');
      return;
    }

    var croppedCanvas = profilePhotoCropper.getCroppedCanvas({
      width: CROPPED_PHOTO_SIZE,
      height: CROPPED_PHOTO_SIZE,
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high',
    });

    if (!croppedCanvas) {
      toast('Could not crop this photo. Try another image.', 'error');
      return;
    }

    canvasToPhotoFile(croppedCanvas, 0.92, function (croppedFile) {
      if (!croppedFile) {
        toast('Could not prepare cropped photo.', 'error');
        return;
      }
      if (croppedFile.size > MAX_PHOTO_BYTES) {
        toast('Cropped photo is still too large. Try a smaller source image.', 'error');
        return;
      }

      setPhotoPreview(croppedCanvas.toDataURL('image/jpeg', 0.92), '');
      destroyPhotoCropper();
      showPhotoCropPanel(false);
      uploadProfilePhoto(croppedFile);
    });
  }

  async function uploadProfilePhoto(photoFile) {
    if (!window.ReportFlowAPI || !photoFile) return;
    try {
      var photoFormData = new FormData();
      photoFormData.append('profile_photo', photoFile);
      var result = await window.ReportFlowAPI.apiFetch('/api/v1/auth/profile/photo/', {
        method: 'POST',
        body: photoFormData,
      });
      var data = result.data || {};
      fillProfileForm(data);
      updateNavAvatars(data.profile_photo || '', initialsFromProfile(data));
      clearPendingProfilePhoto();
      toast(result.message || 'Profile photo updated', 'success');
    } catch (err) {
      setPhotoPreview('', initialsFromProfile({
        username: document.getElementById('profileUsername').value,
        first_name: document.getElementById('profileFirstName').value,
        last_name: document.getElementById('profileLastName').value,
      }));
      toast(window.ReportFlowAPI.formatApiError(err, 'Could not upload profile photo'), 'error');
    }
  }

  function openPhotoCropper(file) {
    var validationError = validateSelectedPhotoFile(file);
    if (validationError) {
      toast(validationError, 'error');
      resetPhotoFileInput();
      return;
    }

    if (typeof Cropper !== 'function') {
      toast('Photo cropper failed to load. Refresh the page and try again.', 'error');
      resetPhotoFileInput();
      return;
    }

    var cropImage = document.getElementById('profilePhotoCropImage');
    if (!cropImage) return;

    destroyPhotoCropper();

    var reader = new FileReader();
    reader.onload = function (event) {
      cropImage.src = event.target.result;
      showPhotoCropPanel(true);

      cropImage.onload = function () {
        destroyPhotoCropper();
        profilePhotoCropper = new Cropper(cropImage, {
          aspectRatio: 1,
          viewMode: 1,
          dragMode: 'move',
          autoCropArea: 1,
          responsive: true,
          background: false,
          guides: true,
          center: true,
          highlight: false,
        });
      };
    };
    reader.onerror = function () {
      toast('Could not read the selected photo.', 'error');
      resetPhotoFileInput();
    };
    reader.readAsDataURL(file);
  }

  async function loadProfile() {
    if (!window.ReportFlowAPI) return;
    clearPendingProfilePhoto();
    cancelPhotoCrop();
    var result = await window.ReportFlowAPI.apiFetch('/api/v1/auth/profile/', {
      loaderMessage: 'Loading profile…',
      loaderImmediate: true,
    });
    fillProfileForm(result.data || {});
  }

  async function saveProfile(ev) {
    ev.preventDefault();
    if (!window.ReportFlowAPI) return;
    var submitBtn = ev.target.querySelector('[type="submit"]');
    setButtonLoading(submitBtn, true);
    try {
      var payload = {
        username: document.getElementById('profileUsername').value.trim(),
        email: document.getElementById('profileEmail').value.trim(),
        first_name: document.getElementById('profileFirstName').value.trim(),
        last_name: document.getElementById('profileLastName').value.trim(),
      };
      var result = await window.ReportFlowAPI.apiFetch('/api/v1/auth/profile/', {
        method: 'PATCH',
        body: JSON.stringify(payload),
        loaderMessage: 'Saving profile…',
        loaderImmediate: true,
      });
      var data = result.data || {};
      fillProfileForm(data);
      updateNavAvatars(data.profile_photo || '', initialsFromProfile(data));
      toast(result.message || 'Profile updated', 'success');
    } catch (err) {
      toast(window.ReportFlowAPI.formatApiError(err, 'Could not update profile'), 'error');
    } finally {
      setButtonLoading(submitBtn, false);
    }
  }

  async function savePassword(ev) {
    ev.preventDefault();
    if (!window.ReportFlowAPI) return;
    var newPassword = document.getElementById('profileNewPassword').value;
    var confirmPassword = document.getElementById('profileConfirmPassword').value;
    if (newPassword !== confirmPassword) {
      toast('New passwords do not match', 'error');
      return;
    }
    var submitBtn = ev.target.querySelector('[type="submit"]');
    setButtonLoading(submitBtn, true);
    try {
      var result = await window.ReportFlowAPI.apiFetch('/api/v1/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify({
          old_password: document.getElementById('profileOldPassword').value,
          new_password: newPassword,
        }),
        loaderMessage: 'Updating password…',
        loaderImmediate: true,
      });
      document.getElementById('profilePasswordForm').reset();
      toast(result.message || 'Password updated', 'success');
    } catch (err) {
      toast(window.ReportFlowAPI.formatApiError(err, 'Could not change password'), 'error');
    } finally {
      setButtonLoading(submitBtn, false);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var modal = document.getElementById('profileModal');
    if (!modal) return;

    modal.addEventListener('show.bs.modal', function () {
      loadProfile().catch(function (err) {
        toast(window.ReportFlowAPI.formatApiError(err, 'Could not load profile'), 'error');
      });
    });

    modal.addEventListener('hidden.bs.modal', function () {
      cancelPhotoCrop();
      clearPendingProfilePhoto();
    });

    var photoInput = document.getElementById('profilePhotoInput');
    if (photoInput) {
      photoInput.addEventListener('change', function () {
        var selectedFile = photoInput.files && photoInput.files[0];
        if (!selectedFile) return;
        openPhotoCropper(selectedFile);
      });
    }

    var cropCancelButton = document.getElementById('profilePhotoCropCancel');
    if (cropCancelButton) {
      cropCancelButton.addEventListener('click', cancelPhotoCrop);
    }

    var cropApplyButton = document.getElementById('profilePhotoCropApply');
    if (cropApplyButton) {
      cropApplyButton.addEventListener('click', applyCroppedPhoto);
    }

    var detailsForm = document.getElementById('profileDetailsForm');
    if (detailsForm) detailsForm.addEventListener('submit', saveProfile);

    var passwordForm = document.getElementById('profilePasswordForm');
    if (passwordForm) passwordForm.addEventListener('submit', savePassword);
  });
})();
