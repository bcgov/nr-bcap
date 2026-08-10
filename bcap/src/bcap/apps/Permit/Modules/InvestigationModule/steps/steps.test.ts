import { describe, it, expect, vi } from 'vitest';
import { mount, shallowMount } from '@vue/test-utils';
import { useDraftStore } from '@/bcap/stores/draft.ts';

import type { AliasedNodeData } from '@/arches_vue_components/types.ts';

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

    // Binding the wrong GenericWidget event still compiles and renders; the
    // edit just never reaches the draft store.
    it('routes a widget edit into the draft store via update:aliasedNodeData', () => {
        // shallowMount would stub <Form> and never render its slot, so the
        // widgets inside it would not exist to emit from.
        const passthrough = { template: '<div><slot /></div>' };
        const wrapper = mount(Step2, {
            global: { stubs: { Form: passthrough, FieldSet: passthrough } },
        });
        const store = useDraftStore();
        const updateValue = vi.spyOn(store, 'updateValue');

        const edit = {
            display_value: 'Field survey',
            node_value: 'Field survey',
            details: [],
        } as AliasedNodeData;
        wrapper
            .findComponent({ name: 'GenericWidget' })
            .vm.$emit('update:aliasedNodeData', edit);

        expect(updateValue).toHaveBeenCalledWith(
            edit,
            'investigation_identification',
            'investigation_identification',
        );
    });
});
