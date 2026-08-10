import { describe, it, expect, vi } from 'vitest';
import { defineComponent, ref } from 'vue';
import { shallowMount } from '@vue/test-utils';

// 1. Mock the heavy GenericWidget to avoid runtime deps during shallowMount[cite: 1]
vi.mock(
    '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue',
    () => ({
        default: defineComponent({
            name: 'GenericWidget',
            template: '<div />',
        }),
    }),
);

// 2. Mock widget constants[cite: 1]
vi.mock('@/arches_component_lab/widgets/constants.ts', () => ({
    EDIT: 'edit',
    VIEW: 'view',
}));

// 3. Mock useDraftStep composable utilized by Steps 2, 3, and 4[cite: 3, 4, 5]
vi.mock('@/bcap/composables/useDraftStep.ts', () => ({
    useDraftStep: () => ({
        draftData: ref({}), // Ensure draftData is a ref so draftData.value doesn't crash
        resolver: vi.fn(),
        isValid: vi.fn(() => true),
        updateValue: vi.fn(),
    }),
}));

// 4. Mock useDraftStore utilized by Step 4 for manual photo saves[cite: 5]
vi.mock('@/bcap/stores/draft.ts', () => ({
    useDraftStore: () => ({
        draftId: 'test-draft-id',
        parentPermitId: 'test-permit-id',
        graphSlug: 'document_submission',
        draftData: {},
    }),
}));

// 5. Import the Document Submission steps
import Step1 from './Step1_About.vue';
import Step2 from './Step2_Details.vue';
import Step3 from './Step3_Submission.vue';
import Step4 from './Step4_Photographs.vue';
import Step99 from './Step99_Review.vue';

const steps = {
    Step1,
    Step2,
    Step3,
    Step4,
    Step99,
};

describe('DocumentSubmissionModule steps', () => {
    for (const [name, component] of Object.entries(steps)) {
        it(`${name} renders and exposes isValid()`, () => {
            // Because we mocked the composable and store, shallowMount will succeed
            const wrapper = shallowMount(component);

            // Assert the component rendered successfully[cite: 1]
            expect(wrapper.html()).toBeTruthy();

            // Every step exposes isValid() for the stepper navigation[cite: 1]
            expect(
                typeof (wrapper.vm as { isValid: () => boolean }).isValid(),
            ).toBe('boolean');
        });
    }
});
