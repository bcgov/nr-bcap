import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';
import { createRouter, createWebHistory } from 'vue-router';
import { createPinia } from 'pinia';
import BCAPPermitApp from '@/bcap/apps/Permit/App.vue';
import { routes } from '@/bcap/apps/Permit/routes.ts';
import { BCGovPermitPreset } from '@/bcap/primevue-bcgov-preset.ts';

import ko from 'knockout';
import internalDashboardTemplate from 'templates/views/components/plugins/internal-permit-dashboard.htm';

const router = createRouter({
    history: createWebHistory(),
    routes,
});

ko.components.register('internal-permit-dashboard', {
    viewModel: function () {
        // Arches auto-adds the dark class to <html> on OS dark unless a choice is
        // stored; store "off" so the app stays light-only.
        localStorage.setItem('arches.bcap-dark', 'false');
        createVueApplication(BCAPPermitApp, {
            theme: {
                preset: BCGovPermitPreset,
                options: {
                    darkModeSelector: '.bcap-dark',
                    cssLayer: {
                        name: 'primevue',
                        order: 'theme, base, primevue',
                    },
                },
            },
        }).then((vueApp) => {
            vueApp.use(createPinia());
            vueApp.use(router);
            vueApp.mount('#internal-dashboard-mounting-point');
        });
    },
    template: internalDashboardTemplate,
});
