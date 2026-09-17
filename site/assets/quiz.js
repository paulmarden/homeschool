/* Quiz modals and live marking.

   Each quiz lives in a <dialog>; the page shows a button that opens it.
   Progressive enhancement: with JavaScript off the <dialog> stays closed but
   every question is still answerable on paper via its "Show answer"
   disclosure, and the buttons are inert rather than misleading.

   Scores go to localStorage through progress.js, which must load first. */
(function () {
  'use strict';

  /* Oak's accepted answers are written for a human marker, so compare loosely:
     case, surrounding space, trailing punctuation and the spelling of common
     maths symbols should not decide a right answer. */
  function normalise(s) {
    return String(s == null ? '' : s)
      .toLowerCase()
      .replace(/ /g, ' ')
      .replace(/[‘’]/g, "'")
      .replace(/[“”]/g, '"')
      .replace(/[−–—]/g, '-')
      .replace(/\s+/g, ' ')
      .replace(/[.,;:!?]+$/, '')
      .trim();
  }

  function parseAccept(el) {
    try {
      return JSON.parse(el.getAttribute('data-accept') || '[]');
    } catch (e) {
      return [];
    }
  }

  function setState(el, state) {
    el.classList.remove('is-right', 'is-wrong', 'is-missed');
    if (state) el.classList.add(state);
  }

  /* Keep the page from scrolling behind an open modal. Derived from whether any
     dialog is actually open, and called at every close site: the dialog `close`
     event is not reliably delivered everywhere this runs, and a missed remove
     would leave the page permanently unscrollable. */
  function syncScrollLock() {
    var anyOpen = Array.prototype.some.call(
      document.querySelectorAll('dialog[data-quiz]'),
      function (d) { return d.open; });
    document.body.classList.toggle('modal-open', anyOpen);
  }

  function closeDialog(dlg) {
    dlg.close();
    syncScrollLock();
  }

  function clearQuestion(q) {
    q.querySelectorAll('.opt').forEach(function (o) { setState(o, null); });
    q.querySelectorAll('input[type=radio], input[type=checkbox]').forEach(function (i) {
      i.checked = false;
    });
    q.querySelectorAll('input[type=text]').forEach(function (i) {
      i.value = '';
      setState(i, null);
    });
    q.querySelectorAll('select').forEach(function (s) {
      s.value = '';
      setState(s, null);
    });
  }

  /* Returns true / false for a marked question, or null when unanswered. */
  function markQuestion(q) {
    var type = q.getAttribute('data-qtype');

    if (type === 'multiple-choice') {
      var opts = Array.prototype.slice.call(q.querySelectorAll('.opt'));
      var answered = opts.some(function (o) { return o.querySelector('input').checked; });
      if (!answered) return null;
      var ok = true;
      opts.forEach(function (o) {
        var correct = o.getAttribute('data-correct') === '1';
        var picked = o.querySelector('input').checked;
        if (picked && correct) setState(o, 'is-right');
        else if (picked && !correct) { setState(o, 'is-wrong'); ok = false; }
        else if (!picked && correct) { setState(o, 'is-missed'); ok = false; }
        else setState(o, null);
      });
      return ok;
    }

    if (type === 'short-answer') {
      var input = q.querySelector('input[type=text]');
      if (!input || !normalise(input.value)) return null;
      var accept = parseAccept(input).map(normalise);
      var hit = accept.indexOf(normalise(input.value)) !== -1;
      setState(input, hit ? 'is-right' : 'is-wrong');
      return hit;
    }

    if (type === 'match' || type === 'order') {
      var selects = Array.prototype.slice.call(q.querySelectorAll('select'));
      if (!selects.length || !selects.some(function (s) { return s.value; })) return null;
      var all = true;
      selects.forEach(function (s) {
        var want = s.getAttribute('data-answer');
        if (want === null) want = s.getAttribute('data-position');
        if (!s.value) { setState(s, 'is-wrong'); all = false; return; }
        var hit = normalise(s.value) === normalise(want);
        setState(s, hit ? 'is-right' : 'is-wrong');
        if (!hit) all = false;
      });
      return all;
    }

    return null;
  }

  function wire(quiz) {
    var questions = Array.prototype.slice.call(quiz.querySelectorAll('.q'));
    var score = quiz.querySelector('[data-score]');
    var total = questions.length;
    var quizId = quiz.getAttribute('data-quiz');
    var lessonKey = quiz.getAttribute('data-lesson');

    function report(marked, right) {
      if (!score) return;
      score.textContent = marked
        ? right + ' of ' + marked + ' correct' +
          (marked < total ? ' (' + (total - marked) + ' not answered)' : '')
        : total + ' questions';
    }

    quiz.querySelector('[data-check]').addEventListener('click', function () {
      var marked = 0, right = 0;
      questions.forEach(function (q) {
        var r = markQuestion(q);
        if (r === null) return;
        marked++;
        if (r) right++;
      });
      report(marked, right);
      if (!marked) {
        if (score) score.textContent = 'Answer a question first';
        return;
      }
      if (window.Progress) window.Progress.record(lessonKey, quizId, right, marked, total);
    });

    quiz.querySelector('[data-reveal]').addEventListener('click', function () {
      quiz.querySelectorAll('details.qanswer').forEach(function (d) { d.open = true; });
    });

    quiz.querySelector('[data-reset]').addEventListener('click', function () {
      questions.forEach(clearQuestion);
      quiz.querySelectorAll('details.qanswer, details.qhint').forEach(function (d) {
        d.open = false;
      });
      report(0, 0);
    });

    /* Re-marking as soon as something changes would give the answer away, so
       only drop the stale verdict on that one question. */
    quiz.addEventListener('change', function (ev) {
      var q = ev.target.closest('.q');
      if (!q) return;
      q.querySelectorAll('.is-right, .is-wrong, .is-missed').forEach(function (el) {
        setState(el, null);
      });
    });

    quiz.querySelectorAll('[data-close]').forEach(function (btn) {
      btn.addEventListener('click', function () { closeDialog(quiz); });
    });

    /* Click outside the panel closes it, the way a backdrop should. */
    quiz.addEventListener('click', function (ev) {
      if (ev.target === quiz) closeDialog(quiz);
    });

    /* Escape closes a native dialog without going through our handlers. */
    quiz.addEventListener('cancel', function () { setTimeout(syncScrollLock, 0); });
    quiz.addEventListener('close', syncScrollLock);
  }

  document.querySelectorAll('dialog[data-quiz]').forEach(wire);

  document.querySelectorAll('[data-open]').forEach(function (btn) {
    var dlg = document.getElementById(btn.getAttribute('data-open'));
    if (!dlg || typeof dlg.showModal !== 'function') return;
    btn.addEventListener('click', function () {
      dlg.showModal();
      syncScrollLock();
      var first = dlg.querySelector('input, select, button');
      if (first) first.focus();
    });
  });
})();
