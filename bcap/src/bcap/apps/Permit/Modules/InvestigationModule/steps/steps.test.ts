import { describe, it, expect, vi } from 'vitest';
import { defineComponent } from 'vue';
import { shallowMount } from '@vue/test-utils';

// The steps embed arches widgets that pull in heavy runtime deps we don't need
// for a render smoke test; stub them so shallowMount only exercises step markup.
vi.mock(
    '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue',
    () => ({
        default: defineComponent({
            name: 'GenericWidget',
            template: '<div />',
        }),
    }),
);
vi.mock('@/arches_component_lab/widgets/constants.ts', () => ({
    EDIT: 'edit',
    VIEW: 'view',
}));

import Step1 from './Step1_About.vue';
import Step2 from './Step2_Overview.vue';
import Step3 from './Step3_Personnel.vue';
import Step4 from './Step4_Methods.vue';
import Step5 from './Step5_Recordings.vue';
import Step6 from './Step6_Materials.vue';
import Step7 from './Step7_Remains.vue';
import Step8 from './Step8_Repository.vue';
import Step99 from './Step99_Review.vue';

const steps = {
    Step1,
    Step2,
    Step3,
    Step4,
    Step5,
    Step6,
    Step7,
    Step8,
    Step99,
};

describe('InvestigationModule steps', () => {
    for (const [name, component] of Object.entries(steps)) {
        it(`${name} renders and exposes isValid()`, () => {
            const wrapper = shallowMount(component);
            expect(wrapper.html()).toBeTruthy();
            // Every step exposes isValid() for the stepper navigation. With no
            // draft injected it just returns a boolean without throwing.
            expect(
                typeof (wrapper.vm as { isValid: () => boolean }).isValid(),
            ).toBe('boolean');
        });
    }
});
