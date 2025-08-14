(function () {
    if (window.__BCAP_DEFERRAL__) return;

    let _resolve;
    const p = new Promise((resolve) => (_resolve = resolve));
    window.__BCAP_DEFERRAL__ = p;

    function resolveNow() {
        try {
            _resolve();
        } catch {}
    }

    if (window.__BCAP_VITE_READY_FIRED__) resolveNow();
    else
        document.addEventListener("__BCAP_VITE_READY__", resolveNow, {
            once: true,
        });

    const timeout = window.BCAP_DEFERRAL_TIMEOUT_MS || 0;
    if (timeout > 0) setTimeout(resolveNow, timeout);

    // If KO is already present and not wrapped (e.g. bridge loaded way earlier), wrap it now.
    try {
        const ko = window.ko;
        if (ko && ko.applyBindings && !ko.applyBindings.__bcapWrapped) {
            const orig = ko.applyBindings.bind(ko);
            const wrapped = function () {
                return Promise.resolve(window.__BCAP_DEFERRAL__).then(() =>
                    orig.apply(null, arguments),
                );
            };
            wrapped.__bcapWrapped = true;
            ko.applyBindings = wrapped;
        }
    } catch {}
})();
