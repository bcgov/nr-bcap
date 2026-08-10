import { describe, it, expect, vi } from 'vitest';
import { mount, shallowMount } from '@vue/test-utils';
import { useDraftStore } from '@/bcap/stores/draft.ts';

import type { AliasedNodeData } from '@/arches_vue_components/types.ts';

import Step1 from './Step1_About.vue';
import Step2 from './Step2_Prelim.vue';
import Step3 from './Step3_Contacts.vue';
import Step4 from './Step4_Details.vue';
import Step99 from './Step99_Review.vue';

const steps = { Step1, Step2, Step3, Step4, Step99 };

// shallowMount would stub <Form> and never render its slot, so the widgets
// inside it would not exist to emit from.
const passthrough = { template: '<div><slot /></div>' };

const mountStep = (component: unknown) =>
    mount(component as never, {
        global: { stubs: { Form: passthrough, FieldSet: passthrough } },
    });

const edit = (value: string) =>
    ({
        display_value: value,
        node_value: value,
        details: [],
    }) as AliasedNodeData;

describe('BaseModule steps', () => {
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
    it('Step2 routes a widget edit into the draft store', () => {
        const wrapper = mountStep(Step2);
        const updateValue = vi.spyOn(useDraftStore(), 'updateValue');

        const filingType = edit('Investigation');
        wrapper
            .findComponent({ name: 'GenericWidget' })
            .vm.$emit('update:aliasedNodeData', filingType);

        expect(updateValue).toHaveBeenCalledWith(
            filingType,
            'filing_type',
            'application_identification',
        );
    });

    it('Step3 routes the boolean that gates the archaeologist field', () => {
        const wrapper = mountStep(Step3);
        const updateValue = vi.spyOn(useDraftStore(), 'updateValue');

        const retained = edit('Yes');
        // Proponent first, has_retained_archaeologist second; the two
        // conditional widgets are hidden with an empty draft.
        wrapper
            .findAllComponents({ name: 'GenericWidget' })[1]
            .vm.$emit('update:aliasedNodeData', retained);

        expect(updateValue).toHaveBeenCalledWith(
            retained,
            'has_retained_archaeologist',
            'application_contacts',
        );
    });

    it('Step4 routes the geojson boundary and the nested sector path', () => {
        const wrapper = mountStep(Step4);
        const updateValue = vi.spyOn(useDraftStore(), 'updateValue');
        const widgets = wrapper.findAllComponents({ name: 'GenericWidget' });

        const sector = edit('Forestry');
        widgets[0].vm.$emit('update:aliasedNodeData', sector);
        expect(updateValue).toHaveBeenCalledWith(sector, 'industrial_sector', [
            'proposed_project',
            'development_project_details',
        ]);

        const boundary = {
            display_value: '',
            node_value: { type: 'FeatureCollection', features: [] },
            details: [],
        } as unknown as AliasedNodeData;
        widgets[1].vm.$emit('update:aliasedNodeData', boundary);
        expect(updateValue).toHaveBeenCalledWith(
            boundary,
            'project_boundary',
            'proposed_project',
        );
    });
});
