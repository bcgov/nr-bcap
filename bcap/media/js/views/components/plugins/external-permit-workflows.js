import createVueApplication from 'arches/arches/app/media/js/utils/create-vue-application';
import { createRouter, createWebHistory } from 'vue-router';
import BCAPPermitApp from '@/bcap/apps/Permit/App.vue';
import { routes } from '@/bcap/apps/Permit/routes.ts';
import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

import ko from 'knockout';
import defaultInitWorkflowTemplate from 'templates/views/components/plugins/external-permit-workflows.htm';

const router = createRouter({
    history: createWebHistory(),
    routes,
});

const BCGovPreset = definePreset(Aura, {
    semantic: {
        primary: {
            50: '{blue.50}',
            100: '{blue.100}',
            200: '{blue.200}',
            300: '{blue.300}',
            400: '{blue.400}',
            500: '{blue.500}',
            600: '{blue.600}',
            700: '{blue.700}',
            800: '{blue.800}',
            900: '{blue.900}',
            950: '{blue.950}',
        },
        colorScheme: {
            light: {
                color: '{gray.50}',
                formField: {
                    hoverBorderColor: '{primary.color}',
                },
            },
            dark: {
                formField: {
                    hoverBorderColor: '{primary.color}',
                },
            },
        },
        list: {
            option: {
                padding: '0.2rem 0.75rem',
            },
        },
    },
    components: {
        button: {
            paddingX: '.75rem;',
            paddingY: '0.1rem;',
        },
        card: {
            titleFontSize: '1.0rem',
        },
        checkbox: {
            root: {
                width: '1.75rem',
                height: '1.75rem',
            },
        },
        radiobutton: {
            root: {
                sm: {
                    width: '1.75rem',
                    height: '1.75rem',
                },
            },
        },
        fieldset: {
            colorScheme: {
                light: {
                    background: '{grey.50}',
                    legendBackground: '{grey.50}',
                },
                dark: {
                    background: '{grey.900}',
                    legendBackground: '{grey.900}',
                },
            },
            legendFontSize: '2.0rem',
        },
        inputtext: {
            paddingX: '0.2rem',
            paddingY: '0.2rem',
        },
        select: {
            root: {
                paddingX: '1.0rem',
                paddingY: '0.5rem',
            },
            option: {
                fontSize: '1.4rem',
                paddingY: '0.2rem',
                padding: '0.2rem 0.2rem',
                list: {
                    padding: '0.2rem 0.2rem',
                },
            },
        },
        panel: {
            contentPadding: '1.0rem',
            colorScheme: {
                light: {
                    background: '{grey.50}',
                },
                dark: {
                    background: '#222',
                },
            },
        },
        stepper: {
            stepNumber: {
                size: '2.8rem',
                fontSize: '1.8rem',
            },
            steppanel: {
                background: '{grey.50}',
            },
        },
    },
});

ko.components.register('external-permit-workflows', {
    viewModel: function () {
        createVueApplication(BCAPPermitApp, {
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
            vueApp.mount('#bcap-mounting-point');
        });
    },
    template: defaultInitWorkflowTemplate,
});
