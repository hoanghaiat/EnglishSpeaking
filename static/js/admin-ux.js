/* ESP admin UX helpers (loaded on every admin page):
   1. Center Django's related-object popups (the "+" add buttons next to
      foreign-key selects) instead of opening them at the top-left corner.
   2. Slim top loading bar so page transitions feel intentional, not jerky. */
(function () {
    'use strict';

    /* ---------- 1. Centered popups ---------- */
    /* ESP: center admin popups */
    var origOpen = window.open;
    window.open = function (url, name, features) {
        if (typeof url === 'string' && /[?&](_popup=1|_to_field=)/.test(url)) {
            var w = 1000, h = 640;
            var left = Math.round(window.screenX + (window.outerWidth - w) / 2);
            var top = Math.round(window.screenY + (window.outerHeight - h) / 2);
            features = 'height=' + h + ',width=' + w +
                ',left=' + Math.max(0, left) + ',top=' + Math.max(0, top) +
                ',resizable=yes,scrollbars=yes';
        }
        return origOpen.call(window, url, name, features);
    };

    /* ---------- 2. Top loading bar ---------- */
    var bar = document.createElement('div');
    bar.id = 'esp-loadbar';
    function ensureBar() {
        if (!document.getElementById('esp-loadbar')) {
            document.body.appendChild(bar);
        }
    }
    function startBar() {
        ensureBar();
        bar.classList.remove('on');
        // force reflow so the animation restarts cleanly
        void bar.offsetWidth;
        bar.classList.add('on');
    }
    document.addEventListener('DOMContentLoaded', ensureBar);
    document.addEventListener('click', function (e) {
        var a = e.target.closest ? e.target.closest('a[href]') : null;
        if (!a || a.hasAttribute('data-esp-modal')) return;
        var href = a.getAttribute('href');
        if (!href || href.charAt(0) === '#' || a.target === '_blank' ||
            a.hasAttribute('download')) return;
        if (/^(javascript|mailto|tel):/.test(href)) return;
        var url;
        try { url = new URL(href, window.location.href); }
        catch (err) { return; }
        if (url.origin !== window.location.origin) return;
        startBar();
    }, true);
    document.addEventListener('submit', function () { startBar(); });
    window.addEventListener('pageshow', function () {
        var b = document.getElementById('esp-loadbar');
        if (b) b.classList.remove('on');
    });
})();
