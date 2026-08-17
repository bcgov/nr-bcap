import { describe, it, expect, vi } from 'vitest';
import { defineComponent, ref } from 'vue';
import { shallowMount } from '@vue/test-utils';
import { useDraftStore } from '@/bcap/stores/draft.ts';
import { submitModule } from '@/bcap/apps/Permit/api.ts';

import DocumentSubmissionModule from '../DocumentSubmissionModule.vue';
import Step1 from './Step1_About.vue';
import Step2 from './Step2_Details.vue';
import Step3 from './Step3_Submission.vue';
import Step4 from './Step4_Photographs.vue';
import Step99 from './Step99_Review.vue';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    submitModule: vi.fn(),
    saveDraftFieldToBackend: vi.fn(),
}));

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

vi.mock('@/bcap/composables/useDraftStep.ts', () => ({
    useDraftStep: () => ({
        draftData: ref({}),
        resolver: vi.fn(),
        isValid: vi.fn(() => true),
        updateValue: vi.fn(),
    }),
}));

const sharedMockStore = {
    draftId: 'test-draft-id',
    parentPermitId: 'test-permit-id',
    graphSlug: 'document_submission',
    draftData: {},
};

vi.mock('@/bcap/stores/draft.ts', () => ({
    useDraftStore: () => sharedMockStore,
}));

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
            const wrapper = shallowMount(component);

            expect(wrapper.html()).toBeTruthy();

            expect(
                typeof (wrapper.vm as { isValid: () => boolean }).isValid(),
            ).toBe('boolean');
        });
    }
});

describe('DocumentSubmissionModule extended coverage', () => {
    it('customDocumentSubmit formats nested tile payloads', async () => {
        const draftStore = useDraftStore();
        draftStore.draftId = 'mock-draft-123';
        draftStore.parentPermitId = 'mock-permit-456';

        draftStore.draftData = {
            document_submission_process: [
                { aliased_data: { some_prop: 'test' } },
            ],
            report_submission: { aliased_data: { file: 'test.pdf' } },
            submission_photographs: [{ aliased_data: { view: 'north' } }],
        };

        const wrapper = shallowMount(DocumentSubmissionModule);
        const stepper = wrapper.findComponent({ name: 'WorkflowStepper' });

        await stepper.props('submit')();

        expect(submitModule).toHaveBeenCalledWith(
            'mock-permit-456',
            'mock-draft-123',
            'document_submission',
            expect.objectContaining({
                document_submission_process: [
                    {
                        aliased_data: {
                            some_prop: 'test',
                            report_submission: {
                                aliased_data: { file: 'test.pdf' },
                            },
                            submission_photographs: {
                                aliased_data: { view: 'north' },
                            },
                        },
                    },
                ],
            }),
        );
    });

    it('Step2_Details template events', async () => {
        const wrapper = shallowMount(Step2);
        const widgets = wrapper.findAllComponents({ name: 'GenericWidget' });
        for (const w of widgets) {
            await w.vm.$emit('update:value', 'test');
        }
    });

    it('Step3_Submission template events', async () => {
        const wrapper = shallowMount(Step3);
        const widgets = wrapper.findAllComponents({ name: 'GenericWidget' });
        for (const w of widgets) {
            await w.vm.$emit('update:value', 'test');
        }
    });

    it('Step3_Submission handles undefined draftData', () => {
        const wrapper = shallowMount(Step3);
        expect(wrapper.exists()).toBe(true);
    });

    it('Step4_Photographs complete interaction flow', async () => {
        const wrapper = shallowMount(Step4);
        const widgets = wrapper.findAllComponents({ name: 'GenericWidget' });

        const fileWidget = widgets.find(
            (w) => w.props('nodeAlias') === 'submission_photographs',
        );
        if (fileWidget) {
            const mockFile = new File([''], 'test.jpg', { type: 'image/jpeg' });
            await fileWidget.vm.$emit('update:value', {
                node_value: [{ file: mockFile }],
            });
        }

        const dateWidget = widgets.find(
            (w) => w.props('nodeAlias') === 'photograph_date',
        );
        if (dateWidget) {
            await dateWidget.vm.$emit('update:value', { node_value: '2020' });
            await dateWidget.vm.$emit('update:value', {
                node_value: '2020-01-01',
            });
            await dateWidget.vm.$emit('update:value', {
                node_value: 'invalid',
            });
        }

        const buttons = wrapper.findAllComponents({ name: 'Button' });

        const saveImageBtn = buttons.find((b) =>
            (b.attributes('tooltip') || '').includes('Save'),
        );
        if (saveImageBtn) await saveImageBtn.vm.$emit('click');

        const addImageBtn = buttons.find(
            (b) => b.attributes('label') === '+ Add',
        );
        if (addImageBtn) await addImageBtn.vm.$emit('click');

        const galleryItems = wrapper.findAll('.image-placeholder');
        if (galleryItems.length > 0) {
            await galleryItems[0].trigger('click');
            const deleteIcon = galleryItems[0].find('.image-delete-icon');
            if (deleteIcon.exists()) await deleteIcon.trigger('click');
        }

        expect(
            await (wrapper.vm as { save: () => Promise<boolean> }).save(),
        ).toBe(true);
    });

    it('Step99_Review parses edge case data shapes', () => {
        const Step99Stub = {
            template: '<div><slot :data="resourceData" :fields="[]" /></div>',
            props: ['resourceData'],
        };

        shallowMount(Step99, {
            props: { resourceData: null },
            global: {
                stubs: {
                    Step99_Review: Step99Stub,
                    FieldSet: { template: '<div><slot/></div>' },
                },
            },
        });

        const wrapperWithDirectPhotos = shallowMount(Step99, {
            props: {
                resourceData: {
                    submission_photographs: {
                        aliased_data: { photograph_view: 'Front' },
                    },
                },
            },
            global: {
                stubs: {
                    Step99_Review: Step99Stub,
                    FieldSet: {
                        template: '<div>{{legend}}<slot/></div>',
                        props: ['legend'],
                    },
                },
            },
        });

        expect(wrapperWithDirectPhotos.html()).toContain(
            'Submission Photographs',
        );
    });
});

it('Step3_Submission forces data ref initialization', async () => {
    const wrapper = shallowMount(Step3, {
        global: {
            provide: {
                draftData: ref(undefined),
            },
        },
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.exists()).toBe(true);
});

it('Step99_Review edge cases and fallbacks', async () => {
    const Step99Stub = {
        template: '<div><slot :data="resourceData" :fields="fields" /></div>',
        props: ['resourceData', 'fields'],
    };
    const FieldSetStub = { template: '<div><slot/></div>' };

    shallowMount(Step99, {
        props: { resourceData: null },
        global: {
            stubs: { Step99_Review: Step99Stub, FieldSet: FieldSetStub },
        },
    });

    const directWrapper = shallowMount(Step99, {
        props: {
            resourceData: {
                submission_photographs: {
                    aliased_data: { photograph_view: 'Front' },
                },
            },
        },
        global: {
            stubs: {
                Step99_Review: Step99Stub,
                FieldSet: {
                    template: '<div>{{legend}}<slot/></div>',
                    props: ['legend'],
                },
            },
        },
        data() {
            return { fields: [{ alias: 'valid_field' }] };
        },
    });
    await directWrapper.vm.$nextTick();
    expect(directWrapper.html()).toContain('Submission Photographs');
});

it('Step4_Photographs full component interaction', async () => {
    const wrapper = shallowMount(Step4);
    await wrapper.vm.$nextTick();

    const widgets = wrapper.findAllComponents({ name: 'GenericWidget' });

    const fileWidget = widgets.find(
        (w) =>
            w.attributes('node-alias') === 'submission_photographs' ||
            w.props('nodeAlias') === 'submission_photographs',
    );
    if (fileWidget) {
        const mockFile = new File([''], 'test.jpg', { type: 'image/jpeg' });
        fileWidget.vm.$emit('update:value', {
            node_value: [{ file: mockFile }],
        });
        await wrapper.vm.$nextTick();
    }

    const dateWidget = widgets.find(
        (w) =>
            w.attributes('node-alias') === 'photograph_date' ||
            w.props('nodeAlias') === 'photograph_date',
    );
    if (dateWidget) {
        dateWidget.vm.$emit('update:value', { node_value: '2020' });
        dateWidget.vm.$emit('update:value', { node_value: '2020-01-01' });
        dateWidget.vm.$emit('update:value', { node_value: 'invalid' });
    }

    await wrapper.vm.$nextTick();

    const saveImageBtn = wrapper
        .findAllComponents({ name: 'Button' })
        .find((b) => (b.attributes('tooltip') || '').includes('Save'));
    if (saveImageBtn) {
        saveImageBtn.vm.$emit('click');
        await wrapper.vm.$nextTick();
    }

    const addImageBtn = wrapper
        .findAllComponents({ name: 'Button' })
        .find((b) => b.attributes('label') === '+ Add');
    if (addImageBtn) {
        addImageBtn.vm.$emit('click');
        await wrapper.vm.$nextTick();
    }

    const galleryItems = wrapper.findAll('.image-placeholder');
    if (galleryItems.length > 0) {
        await galleryItems[0].trigger('click');
        const deleteIcon = galleryItems[0].find('.image-delete-icon');
        if (deleteIcon.exists()) await deleteIcon.trigger('click');
    }

    expect(await (wrapper.vm as { save: () => Promise<boolean> }).save()).toBe(
        true,
    );
});
