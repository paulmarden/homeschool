/* Quiz scores and lesson status, kept in this browser's localStorage.

   Shape, under the key below:
     { "<unit-slug>/<lesson-slug>": {
         exit:    { right, total, status, at },
         starter: { right, total, status, at }
     } }
   status is "complete" when every question was answered, else "partial".

   Nothing here leaves the browser, and it is per-device: clearing site data
   clears it. The About page has a button to reset it deliberately. */
(function (global) {
  'use strict';

  var KEY = 'y8hub.progress.v1';

  function read() {
    try {
      return JSON.parse(localStorage.getItem(KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  function write(all) {
    try {
      localStorage.setItem(KEY, JSON.stringify(all));
      return true;
    } catch (e) {
      return false; /* private mode, or storage full -- marking still works */
    }
  }

  function record(lessonKey, quizId, right, answered, total) {
    if (!lessonKey) return;
    var all = read();
    var lesson = all[lessonKey] || (all[lessonKey] = {});
    lesson[quizId] = {
      right: right,
      total: total,
      status: answered >= total ? 'complete' : 'partial',
      at: new Date().toISOString()
    };
    write(all);
    paint();
  }

  function forLesson(lessonKey) {
    return read()[lessonKey] || null;
  }

  function clear() {
    try {
      localStorage.removeItem(KEY);
    } catch (e) { /* nothing to do */ }
    paint();
  }

  function shortDate(iso) {
    var d = new Date(iso);
    if (isNaN(d)) return '';
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  }

  /* A lesson counts as done when its exit quiz has been completed. */
  function isDone(entry) {
    return !!(entry && entry.exit && entry.exit.status === 'complete');
  }

  function paint() {
    var all = read();

    /* Lesson rows on a unit page. */
    document.querySelectorAll('.modrow[data-lesson]').forEach(function (row) {
      var entry = all[row.getAttribute('data-lesson')];
      var tag = row.querySelector('[data-lesson-score]');
      if (!tag) return;
      if (!entry || !entry.exit) {
        tag.hidden = true;
        row.classList.remove('is-done');
        return;
      }
      var e = entry.exit;
      tag.hidden = false;
      tag.textContent = 'Exit ' + e.right + '/' + e.total + ' · ' + shortDate(e.at);
      tag.classList.toggle('tag-accent', isDone(entry));
      tag.classList.toggle('tag-neutral', !isDone(entry));
      row.classList.toggle('is-done', isDone(entry));
    });

    /* "n of m lessons done" on a unit page. */
    document.querySelectorAll('.unitprog[data-unit]').forEach(function (el) {
      var slug = el.getAttribute('data-unit');
      var rows = document.querySelectorAll('.modrow[data-lesson]');
      var done = 0;
      rows.forEach(function (r) {
        if (isDone(all[r.getAttribute('data-lesson')])) done++;
      });
      if (!done) { el.hidden = true; return; }
      el.hidden = false;
      el.textContent = done + ' of ' + rows.length + ' done';
      void slug;
    });

    /* Per-unit counts on the subject page. */
    document.querySelectorAll('[data-unit-prog]').forEach(function (el) {
      var slug = el.getAttribute('data-unit');
      var done = 0;
      Object.keys(all).forEach(function (k) {
        if (k.indexOf(slug + '/') === 0 && isDone(all[k])) done++;
      });
      if (!done) { el.hidden = true; return; }
      el.hidden = false;
      el.textContent = ' · ' + done + ' done';
    });

    /* Status line under the quiz buttons on a lesson page. */
    document.querySelectorAll('[data-lesson-state]').forEach(function (el) {
      var host = el.closest('.col') || el.parentNode;
      var launch = host.querySelector('.quizlaunch[data-lesson]');
      var entry = launch && all[launch.getAttribute('data-lesson')];
      if (!entry) { el.hidden = true; return; }
      var bits = [];
      ['starter', 'exit'].forEach(function (id) {
        var e = entry[id];
        if (!e) return;
        bits.push((id === 'exit' ? 'Exit quiz' : 'Starter quiz') + ': ' +
          e.right + '/' + e.total +
          (e.status === 'complete' ? '' : ' (partial)') +
          ' · ' + shortDate(e.at));
      });
      if (!bits.length) { el.hidden = true; return; }
      el.hidden = false;
      el.textContent = bits.join('   —   ');
    });
  }

  global.Progress = {
    read: read, record: record, forLesson: forLesson, clear: clear, paint: paint
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', paint);
  } else {
    paint();
  }

  document.addEventListener('click', function (ev) {
    if (ev.target.closest('[data-clear-progress]')) {
      clear();
      var note = document.querySelector('[data-progress-note]');
      if (note) note.textContent = 'Saved progress cleared.';
    }
  });
})(window);
