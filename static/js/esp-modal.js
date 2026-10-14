/* ESP modal: open any link with [data-esp-modal] in a centered dialog
   instead of navigating away. Forms inside submit via fetch; a JSON
   {ok:true} closes the dialog and reloads the page, HTML re-renders
   the dialog body (e.g. validation errors). Dependency-free. */
(function () {
    'use strict';

    var SHELL_ID = 'esp-modal';
    var modalUrl = null;

    function shell() {
        var el = document.getElementById(SHELL_ID);
        if (el) return el;
        el = document.createElement('div');
        el.id = SHELL_ID;
        el.hidden = true;
        el.innerHTML =
            '<div class="esp-modal-backdrop" data-esp-modal-close></div>' +
            '<div class="esp-modal-dialog" role="dialog" aria-modal="true">' +
            '<div class="esp-modal-content"></div></div>';
        document.body.appendChild(el);
        return el;
    }

    function openModal(url) {
        var u = new URL(url, window.location.href);
        u.searchParams.set('modal', '1');
        modalUrl = u.toString();
        fetch(modalUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) {
                if (r.redirected) { window.location.href = url; return null; }
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.text();
            })
            .then(function (html) {
                if (html === null) return;
                var root = shell();
                root.querySelector('.esp-modal-content').innerHTML = html;
                root.hidden = false;
                document.body.classList.add('esp-modal-open');
            })
            .catch(function () { window.location.href = url; }); // fallback
    }

    function closeModal() {
        var root = document.getElementById(SHELL_ID);
        if (root) root.hidden = true;
        document.body.classList.remove('esp-modal-open');
        modalUrl = null;
    }

    document.addEventListener('click', function (e) {
        var opener = e.target.closest('a[data-esp-modal]');
        if (opener) {
            e.preventDefault();
            openModal(opener.getAttribute('href'));
            return;
        }
        if (e.target.closest('[data-esp-modal-close]')) {
            closeModal();
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeModal();
    });

    document.addEventListener('submit', function (e) {
        var form = e.target.closest
            ? e.target.closest('form[data-esp-modal-form]')
            : null;
        if (!form || !modalUrl) return;
        e.preventDefault();
        fetch(modalUrl, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: new FormData(form) // includes the CSRF hidden input
        })
            .then(function (r) {
                if (r.redirected) { window.location.href = r.url; return null; }
                var ct = r.headers.get('content-type') || '';
                if (ct.indexOf('application/json') !== -1) {
                    return r.json().then(function (d) { return { json: d }; });
                }
                return r.text().then(function (t) { return { html: t }; });
            })
            .then(function (res) {
                if (!res) return;
                if (res.json && res.json.ok) {
                    closeModal();
                    window.location.reload(); // show result + Django message
                } else if (res.html) {
                    document.querySelector(
                        '#' + SHELL_ID + ' .esp-modal-content'
                    ).innerHTML = res.html;
                }
            });
    });

    // Expose for debugging/tests.
    window.espModalClose = closeModal;
})();
