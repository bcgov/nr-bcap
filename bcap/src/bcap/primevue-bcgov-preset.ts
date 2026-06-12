import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';
import type { Preset } from '@primeuix/themes/types';

// Shared BC Gov PrimeVue theme for the BCAP plugin apps, so the preset is
// defined once instead of copy-pasted into each plugin entry point.
//
// - BCGovPreset:       the admin "Invite Contributor" app.
// - BCGovPermitPreset: the permit dashboard / workflow apps -- the same base
//   plus the extra components those richer forms render (card, checkbox,
//   fieldset, inputtext, radiobutton, stepper).

const semantic = {
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
};

const baseComponents = {
    button: {
        paddingX: '.75rem;',
        paddingY: '0.1rem;',
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
};

// PrimeVue's design-token types omit some tokens these presets set (e.g. button
// paddingX, card titleFontSize), so the configs are cast to Preset.
export const BCGovPreset = definePreset(Aura, {
    semantic,
    components: baseComponents,
} as unknown as Preset);

export const BCGovPermitPreset = definePreset(Aura, {
    semantic,
    components: {
        ...baseComponents,
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
} as unknown as Preset);
