import { ref, onMounted, onBeforeUnmount } from "vue";

type ThemeDebugInfo = {
    // High-level signals
    isDark: boolean | null;
    dataThemeHtml: string | null;
    dataThemeBody: string | null;

    // PrimeVue hints (if you use PrimeVue themes)
    primeTheme: string | null; // e.g. "lara-dark-teal"
    primeThemeHref: string | null; // full URL to the theme stylesheet

    // Snapshot of useful CSS variables
    cssVars: Record<string, string>;
};

type Options = {
    /** Extra CSS vars to probe in addition to the defaults */
    varNames?: string[];
    /** Log to console on mount & on changes */
    log?: boolean;
};

const DEFAULT_VARS = [
    // PrimeVue tokenized themes
    "--p-text-color",
    "--p-surface-0",
    "--p-surface-900",
    "--p-primary-500",
    // Common legacy or other libs
    "--primary-color",
    "--color-primary",
    "--text-color",
    "--background-color",
];

export function useThemeDebug(options: Options = {}) {
    const { varNames = [], log = false } = options;

    const info: Ref<ThemeDebugInfo> = ref({
        isDark: null,
        dataThemeHtml: null,
        dataThemeBody: null,
        primeTheme: null,
        primeThemeHref: null,
        cssVars: {},
    });

    let attrObserver: MutationObserver | null = null;
    let headObserver: MutationObserver | null = null;

    const readCssVars = () => {
        const html = document.documentElement;
        const cs = getComputedStyle(html);
        const names = Array.from(new Set([...DEFAULT_VARS, ...varNames]));
        const out: Record<string, string> = {};
        for (const name of names) {
            const v = cs.getPropertyValue(name)?.trim();
            if (v) out[name] = v;
        }
        return out;
    };

    const findPrimeVueTheme = (): {
        name: string | null;
        href: string | null;
    } => {
        // Look for a <link rel="stylesheet"> that points at primevue/resources/themes/<name>/*.css
        const links = Array.from(
            document.querySelectorAll(
                'link[rel="stylesheet"], link[as="style"]',
            ),
        ) as HTMLLinkElement[];

        for (const link of links) {
            const href = link.href || "";
            const m = href.match(
                /primevue\/resources\/themes\/([^/]+)\/[^/]+\.css/i,
            );
            if (m) return { name: m[1], href };
        }

        // Fallback: scan styleSheets list (href is safe to read without touching cssRules)
        for (const sheet of Array.from(document.styleSheets)) {
            const href = (sheet as CSSStyleSheet).href || "";
            const m = href.match(
                /primevue\/resources\/themes\/([^/]+)\/[^/]+\.css/i,
            );
            if (m) return { name: m[1], href };
        }

        return { name: null, href: null };
    };

    const snapshot = () => {
        const html = document.documentElement;
        const body = document.body;

        const isDark = html.classList.contains("dark"); // Tailwind & many setups
        const dataThemeHtml = html.getAttribute("data-theme");
        const dataThemeBody = body?.getAttribute("data-theme") || null;

        const { name: primeTheme, href: primeThemeHref } = findPrimeVueTheme();
        const cssVars = readCssVars();

        const next: ThemeDebugInfo = {
            isDark,
            dataThemeHtml: dataThemeHtml ?? null,
            dataThemeBody,
            primeTheme,
            primeThemeHref,
            cssVars,
        };

        info.value = next;
        if (log) {
            // friendly logs

            console.table({
                isDark,
                dataThemeHtml: next.dataThemeHtml,
                dataThemeBody: next.dataThemeBody,
                primeTheme: next.primeTheme,
            });

            console.log("theme css vars →", next.cssVars);
        }
    };

    const refresh = () => snapshot();

    const startObservers = () => {
        // Watch class/data-theme flips on <html> and <body>
        attrObserver = new MutationObserver(() => snapshot());
        attrObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["class", "data-theme"],
        });
        if (document.body) {
            attrObserver.observe(document.body, {
                attributes: true,
                attributeFilter: ["class", "data-theme"],
            });
        }

        // Watch for theme <link> swaps (e.g., switching PrimeVue theme at runtime)
        headObserver = new MutationObserver(() => snapshot());
        headObserver.observe(document.head, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["href", "rel", "as"],
        });
    };

    const stop = () => {
        attrObserver?.disconnect();
        headObserver?.disconnect();
        attrObserver = null;
        headObserver = null;
    };

    onMounted(() => {
        if (typeof window === "undefined") return;
        snapshot();
        startObservers();
        // Optional global handle in dev consoles
        (window as any).__themeDebug = info;
    });

    onBeforeUnmount(() => {
        stop();
    });

    return { info, refresh, stop };
}
