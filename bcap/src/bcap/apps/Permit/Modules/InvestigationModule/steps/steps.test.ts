import { shallowMount } from '@vue/test-utils';

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
            // Every step exposes isValid() for the stepper navigation. With an
            // empty draft store it just returns a boolean without throwing.
            expect(
                typeof (wrapper.vm as { isValid: () => boolean }).isValid(),
            ).toBe('boolean');
        });
    }
});
