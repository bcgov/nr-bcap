// If you are on PrimeVue v4 use '@primevue/themes'.
// If your project uses the PrimeUIX monorepo, keep '@primeuix/themes'.
import { definePreset } from "@primeuix/themes";
import Aura from "@primeuix/themes/aura"; // base preset (light). Other options: Lara, Nora, etc.
import type { Preset } from "@primeuix/themes/types";
import type { App } from "vue";

import PrimeVue from "primevue/config";

declare global {
    interface Window {
        BCAP: BcapConfig;
    }
    interface BcapConfig {
        setPrimeVuePreset?: (preset: Preset) => void;
        PRIMEVUE_PRESET: Preset;
        vueKO: VueKO;
    }
    type VueAppMiddleware = (app: App) => void;
    interface VueKO {
        register: (middleware: VueAppMiddleware) => void;
        use: (middleware: VueAppMiddleware) => void;
    }
}

// Make your custom preset (optional; you can also pass Aura directly)
const BcapPreset = definePreset(Aura, {
    // Override only what you need
    semantic: {
        primary: {
            50: "{indigo.50}",
            100: "{indigo.100}",
            200: "{indigo.200}",
            300: "{indigo.300}",
            400: "{indigo.400}",
            500: "{indigo.500}", // main brand
            600: "{indigo.600}",
            700: "{indigo.700}",
            800: "{indigo.800}",
            900: "{indigo.900}",
        },
    },
});

// Register once with your KO↔Vue bridge so EVERY app gets PrimeVue + the preset.
window.BCAP?.vueKO?.use?.((app: App) => {
    app.use(PrimeVue, {
        theme: {
            preset: BcapPreset, // or Aura / Nora / Lara directly
            options: {
                darkModeSelector: ".theme-dark", // if you want to toggle by adding this class to <html>
            },
        },
    });
});

// (optional) runtime switch helper
window.BCAP = window.BCAP || {};
window.BCAP.setPrimeVuePreset = (preset: Preset) => {
    // Every newly created app will use the new preset automatically via the middleware above.
    window.BCAP.PRIMEVUE_PRESET = preset;
};
