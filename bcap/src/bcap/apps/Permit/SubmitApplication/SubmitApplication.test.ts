import { describe, it, expect, vi } from 'vitest';
import { defineComponent } from 'vue';
import { shallowMount } from '@vue/test-utils';

// Steps embed arches widgets with heavy runtime deps; stub for a render smoke test.
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

import SubmitApplication from './SubmitApplication.vue';

describe('SubmitApplication', () => {
    it('mounts the stepper workflow', () => {
        const wrapper = shallowMount(SubmitApplication);
        expect(wrapper.html()).toBeTruthy();
    });
});
