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
import Step2 from './Step2_Prelim.vue';
import Step3 from './Step3_Details1.vue';
import Step4 from './Step4_Personnel.vue';
import Step5 from './Step5_Methods.vue';
import Step6 from './Step6_Recordings.vue';
import Step7 from './Step7_MaterialCollection.vue';
import Step8 from './Step8_Remains.vue';
import Step9 from './Step9_Repository.vue';
import Step10 from './Step10_Permit_Deliverables.vue';
import Step11 from './Step11_Reports_Expectations.vue';
import Step12 from './Step12_Schedule_of_Deliverables.vue';
import Step13 from './Step13_References.vue';
import Step14 from './Step14_SignOff.vue';
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
    Step9,
    Step10,
    Step11,
    Step12,
    Step13,
    Step14,
    Step99,
};

describe('SubmitApplication steps', () => {
    for (const [name, component] of Object.entries(steps)) {
        it(`${name} renders and reports valid`, () => {
            const wrapper = shallowMount(component);
            expect(wrapper.html()).toBeTruthy();
            // Every step exposes isValid() for the stepper navigation.
            expect((wrapper.vm as { isValid: () => boolean }).isValid()).toBe(
                true,
            );
        });
    }
});
