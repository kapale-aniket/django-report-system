(function () {
  'use strict';
  var form = document.getElementById('reportSubmitForm');
  if (!form) return;
  var key = 'report_submit_draft';
  try {
    var raw = localStorage.getItem(key);
    if (raw) {
      var data = JSON.parse(raw);
      var title = form.querySelector('[name="title"]');
      var tags = form.querySelector('[name="tags"]');
      var year = form.querySelector('[name="academic_year"]');
      if (title && data.title) title.value = data.title;
      if (tags && data.tags) tags.value = data.tags;
      if (year && data.academic_year) year.value = data.academic_year;
    }
  } catch (e) {}
  form.addEventListener('input', function () {
    var title = form.querySelector('[name="title"]');
    var tags = form.querySelector('[name="tags"]');
    var year = form.querySelector('[name="academic_year"]');
    try {
      localStorage.setItem(
        key,
        JSON.stringify({
          title: title ? title.value : '',
          tags: tags ? tags.value : '',
          academic_year: year ? year.value : '',
        })
      );
    } catch (e) {}
  });
  form.addEventListener('submit', function () {
    try {
      localStorage.removeItem(key);
    } catch (e) {}
  });
})();
