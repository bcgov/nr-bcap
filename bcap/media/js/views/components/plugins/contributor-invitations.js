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
        createVueApplication(BCAPAdminApp, {
            theme: {
                preset: BCGovPreset,
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
            vueApp.mount('#contributor-invitations-mounting-point');
        });
    },
    template: contributorInvitationsTemplate,
});
