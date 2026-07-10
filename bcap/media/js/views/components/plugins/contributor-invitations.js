import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';
import { createRouter, createWebHistory } from 'vue-router';
import BCAPAdminApp from '@/bcap/apps/Admin/App.vue';
import { routes } from '@/bcap/apps/Admin/routes.ts';
import { BCGovPreset } from '@/bcap/primevue-bcgov-preset.ts';

import ko from 'knockout';
import contributorInvitationsTemplate from 'templates/views/components/plugins/contributor-invitations.htm';

const router = createRouter({
    history: createWebHistory(),
    routes,
});

ko.components.register('contributor-invitations', {
    viewModel: function () {
        // Arches auto-adds the dark class to <html> on OS dark unless a choice is
        // stored; store "off" so the app stays light-only.
        localStorage.setItem('arches.bcap-dark', 'false');
        createVueApplication(BCAPAdminApp, {
            theme: {
                preset: BCGovPreset,
                options: {
                    darkModeSelector: '.bcap-dark',
                    cssLayer: {
                        name: 'primevue',
                        order: 'theme, base, primevue',
                    },
                },
            },
        }).then((vueApp) => {
            vueApp.use(router);
            vueApp.mount('#contributor-invitations-mounting-point');
        });
    },
    template: contributorInvitationsTemplate,
});
