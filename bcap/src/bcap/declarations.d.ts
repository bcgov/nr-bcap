// declare untyped modules that have been added to your project in `package.json`
// Module homepage on npmjs.com uses logos "TS" or "DT" to indicate if typed
import type { Preset } from '@primeuix/themes/types';
import type { App } from 'vue';

import('@/arches/declarations.d.ts');

export {};

declare global {
    interface Window {
        __BCAP_VITE_READY_FIRED__?: boolean;
        BCAP: BcapConfig;
    }

    interface BcapConfig {
        setPrimeVuePreset?: (preset: Preset) => void;
        PRIMEVUE_PRESET: Preset;
        vueKO: VueKO;
    }

    // Existing middleware signature you already use elsewhere
    type VueAppMiddleware = (app: App) => void;

    interface VueKO {
        // --- Existing function-form API ---
        register(middleware: VueAppMiddleware): void;
        use(middleware: VueAppMiddleware): void;

        // --- Additional object-form API (matches your entry code) ---
        register(opts: {
            name: string;
            createApp: unknown;
            services?: unknown[];
            component: unknown;
            source?: string;
        }): void;

        // Optional tuple form if you ever call: register("name", { ... })
        register(
            name: string,
            opts: {
                createApp: unknown;
                component: unknown;
                source?: string;
            },
        ): void;
    }
}
