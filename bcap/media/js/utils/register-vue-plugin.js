import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';
import { createRouter, createWebHistory } from 'vue-router';
import { createPinia } from 'pinia';
import ko from 'knockout';
import { installErrorHandling } from '@/bcap/notify.ts';

// Registers an arches plugin page that mounts one of the BCAP Vue apps.
export default function registerVuePlugin(
    name,
    { component, routes, preset, mountPoint, template },
) {
    const router = createRouter({ history: createWebHistory(), routes });

    ko.components.register(name, {
        viewModel: function () {
            // Arches auto-adds the dark class to <html> on OS dark unless a choice is
            // stored; store "off" so the app stays light-only.
            localStorage.setItem('arches.bcap-dark', 'false');
            createVueApplication(component, {
                theme: {
                    preset,
                    options: {
                        darkModeSelector: '.bcap-dark',
                        cssLayer: {
                            name: 'primevue',
                            order: 'theme, base, primevue',
                        },
                    },
                },
            }).then((vueApp) => {
                installErrorHandling(vueApp);
                vueApp.use(createPinia());
                vueApp.use(router);
                vueApp.mount(mountPoint);
            });
        },
        template,
    });
}
