(() => {
    const PENDING_REGS = [];
    const APP_MIDDLEWARE = []; // <- NEW: per-app middleware (e.g., install PrimeVue theme)

    function fireViteReady(reason) {
        if (window.__BCAP_VITE_READY_FIRED__) return;
        window.__BCAP_VITE_READY_FIRED__ = true;
        try {
            document.dispatchEvent(new Event("__BCAP_VITE_READY__"));
        } catch {}
        console.log(`[BCAP] __BCAP_VITE_READY__ fired (${reason})`);
    }

    function prefireFromGlobals() {
        const has_entrypoint =
            String(window.BCAP_HAS_VUE_ENTRYPOINTS) === "true";
        const use_vite = String(window.BCAP_USE_VITE).toLowerCase() === "true";
        if (!use_vite) return fireViteReady("Not using Vite");
        if (!has_entrypoint) return fireViteReady("No entrypoints");
    }

    // call this early in the file
    prefireFromGlobals();

    function toJS(ko, v) {
        if (!ko) return v;
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

                // NEW: run all middleware (e.g., install PrimeVue + theme) before mount
                try {
                    for (const fn of APP_MIDDLEWARE) {
                        try {
                            fn(app, { el, params, ko, name });
                        } catch (e) {
                            console.warn(
                                "[BCAP] vueKO.use middleware failed:",
                                e,
                            );
                        }
                    }
                } catch {}

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
        handler.__bcapInstalled = true;
        handler.__bcapSource = source;

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
        /**
         * Add middleware that receives (app, context) BEFORE each app mounts.
         * Use this to install PrimeVue with a global theme, etc.
         */
        use(fn) {
            if (typeof fn === "function") APP_MIDDLEWARE.push(fn);
            else console.warn("[BCAP] vueKO.use(fn) expects a function");
            return this;
        },
    };

    // Expose
    window.BCAP = window.BCAP || {};
    window.BCAP.vueKO = api;

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
