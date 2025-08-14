(() => {
    const PENDING_REGS = [];

    function toJS(ko, v) {
        if (!ko) return v;
        // Prefer KO's toJS if present; fall back to unwrapping or identity
        if (typeof ko.toJS === "function") return ko.toJS(v);
        try {
            return typeof v === "function" ? v() : v;
        } catch {
            return v;
        }
    }

    function wrapApplyBindingsLazily(ko) {
        if (!ko || ko.applyBindings?.__bcapWrapped) return;

        const orig = ko.applyBindings.bind(ko);
        const wrapped = function () {
            // Look up the deferral *at call-time* so it also works if ko-deferral loaded later
            const defer = window.__BCAP_DEFERRAL__;
            if (defer) {
                return Promise.resolve(defer).then(() =>
                    orig.apply(null, arguments),
                );
            }
            return orig.apply(null, arguments);
        };
        wrapped.__bcapWrapped = true;
        ko.applyBindings = wrapped;
    }

    function installBinding(ko, opts) {
        const {
            name = "vueComponent",
            createApp,
            component,
            allowVirtual = true,
            source = "unknown",
        } = opts || {};
        if (!ko || !createApp || !component || !name) {
            console.warn(
                "[BCAP] register() requires { name, createApp, component }",
            );
            return;
        }
        if (ko.bindingHandlers[name]?.__bcapInstalled) return;

        const handler = {
            init(el, valueAccessor, allBindings, vm, ctx) {
                const params =
                    typeof valueAccessor === "function"
                        ? valueAccessor()
                        : valueAccessor || {};
                const comp = params.component || component;
                const props = toJS(ko, params.props || {}) || {};
                const mount = document.createElement("div");
                mount.dataset.vue = comp?.name || name;
                el.appendChild(mount);
                const app = createApp(comp, props);
                app.mount(mount);
                try {
                    ko?.utils?.domNodeDisposal?.addDisposeCallback?.(el, () => {
                        try {
                            app.unmount();
                        } catch {}
                    });
                } catch {}
                return { controlsDescendantBindings: true };
            },
        };
        // tag + install
        handler.__bcapInstalled = true;
        handler.__bcapSource = source;

        // Install, then freeze so late bundles can’t clobber it
        Object.defineProperty(ko.bindingHandlers, name, {
            value: handler,
            writable: false,
            configurable: false,
            enumerable: true,
        });

        if (allowVirtual && ko.virtualElements) {
            ko.virtualElements.allowedBindings[name] = true;
        }
        console.log(`[BCAP] KO binding '${name}' installed (source=${source})`);
    }

    function onKOReady(ko) {
        while (PENDING_REGS.length) installBinding(ko, PENDING_REGS.shift());
        // Always wrap lazily; it’s harmless without a deferral and fixes race when deferral loads later
        wrapApplyBindingsLazily(ko);
    }

    // Public API
    const api = {
        /**
         * Register a KO binding that mounts a Vue component.
         *   opts = { name, createApp, component, allowVirtual? }
         */
        register(opts) {
            if (window.ko) installBinding(window.ko, opts);
            else PENDING_REGS.push(opts);
        },
    };

    // Expose
    window.BCAP = window.BCAP || {};
    window.BCAP.vueKO = api;

    // If KO is already there, finish setup; otherwise hook assignment
    if (window.ko) {
        onKOReady(window.ko);
    } else {
        Object.defineProperty(window, "ko", {
            configurable: true,
            get() {
                return this.__bcap_ko__;
            },
            set(v) {
                this.__bcap_ko__ = v;
                try {
                    onKOReady(v);
                } catch (e) {
                    console.warn("[BCAP] KO init failed", e);
                }
            },
        });
    }
})();
