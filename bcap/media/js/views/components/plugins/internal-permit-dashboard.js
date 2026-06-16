import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';
import { createRouter, createWebHistory } from 'vue-router';
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
        createVueApplication(BCAPPermitApp, {
            theme: {
                preset: BCGovPermitPreset,
                options: {
                    darkModeSelector: 'system',
                    cssLayer: {
                        name: 'primevue',
                        order: 'theme, base, primevue',
                    },
                },
            },
        }).then((vueApp) => {
            vueApp.use(router);
            vueApp.mount('#internal-dashboard-mounting-point');
        });
    },
    template: internalDashboardTemplate,
});
