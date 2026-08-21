import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import { shallowMount, config, VueWrapper } from '@vue/test-utils';
import {
    submitModule,
    saveDraftFieldToBackend,
} from '@/bcap/apps/Permit/api.ts';

import DocumentSubmissionModule from '../DocumentSubmissionModule.vue';
import Step1 from './Step1_About.vue';
import Step2 from './Step2_Details.vue';
import Step3 from './Step3_Submission.vue';
import Step4 from './Step4_Photographs.vue';
import Step99 from './Step99_Review.vue';

import type {
    DocumentSubmissionDocumentSubmissionProcessAliasedData,
    DocumentSubmissionSubmissionPhotographsTile,
    DocumentSubmissionReportSubmissionTile,
} from '@/bcap/client/types.gen.ts';

type DeepPartial<T> = T extends object
    ? {
          [P in keyof T]?: DeepPartial<T[P]>;
      }
    : T;

config.global.renderStubDefaultSlot = true;

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    submitModule: vi.fn(),
    saveDraftFieldToBackend: vi.fn(),
}));

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

const { mockStoreState } = vi.hoisted(() => {
    const { reactive } = require('vue');
    return {
        mockStoreState: reactive({
            draftId: 'test-draft-id',
            parentPermitId: 'test-permit-id',
            graphSlug: 'document_submission',
            draftData:
                {} as DeepPartial<DocumentSubmissionDocumentSubmissionProcessAliasedData>,
        }),
    };
});

vi.mock('@/bcap/stores/draft.ts', () => ({
    useDraftStore: () => mockStoreState,
}));

const globalMountOptions = {
    global: {
        stubs: {
            FieldSet: { template: '<div><slot/></div>' },
            Fieldset: { template: '<div><slot/></div>' },
            Form: {
                template: '<form><slot/></form>',
                methods: { reset: () => {} },
            },
            LabelledInput: { template: '<div><slot/></div>' },
            MultiFileUploader: {
                name: 'MultiFileUploader',
                template: '<div class="mock-uploader"></div>',
                props: ['nodeAlias'],
            },
            GenericWidget: {
                name: 'GenericWidget',
                template: '<div class="mock-widget"></div>',
                props: ['nodeAlias'],
            },
        },
    },
};

const steps = { Step1, Step2, Step3, Step4, Step99 };

const findWidget = (
    wrapper: VueWrapper,
    alias: string,
): VueWrapper | undefined => {
    const widgets = wrapper.findAllComponents('.mock-widget');
    return widgets.find(
        (w: VueWrapper) =>
            w.props('nodeAlias') === alias ||
            w.attributes('node-alias') === alias,
    );
};

describe('DocumentSubmissionModule steps', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockStoreState.draftData = {};
    });

    for (const [name, component] of Object.entries(steps)) {
        it(`${name} renders and exposes isValid()`, () => {
            const wrapper = shallowMount(component, globalMountOptions);
            expect(wrapper.html()).toBeTruthy();
            expect(
                typeof (
                    wrapper.vm as unknown as { isValid: () => boolean }
                ).isValid(),
            ).toBe('boolean');
        });
    }
});

describe('DocumentSubmissionModule extended coverage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('customDocumentSubmit formats nested tile payloads', async () => {
        mockStoreState.draftId = 'mock-draft-123';
        mockStoreState.parentPermitId = 'mock-permit-456';

        const photo = (
            name: string,
        ): DeepPartial<DocumentSubmissionSubmissionPhotographsTile> => ({
            aliased_data: {
                submission_photographs: {
                    node_value: [
                        {
                            name,
                            node_id: 'n9',
                            file: new File([''], name) as unknown as {
                                objectURL?: string | null;
                            },
                        },
                    ],
                },
            },
        });

        mockStoreState.draftData = {
            submission_number: { node_value: 'S-1' },
            report_submission: {
                aliased_data: {
                    report_title: { node_value: { en: { value: 'a report' } } },
                },
            },
            submission_photographs: [photo('one.jpg'), photo('two.jpg')],
        } as DeepPartial<DocumentSubmissionDocumentSubmissionProcessAliasedData>;

        const wrapper = shallowMount(
            DocumentSubmissionModule,
            globalMountOptions,
        );

        const stepper = wrapper.findComponent({ name: 'WorkflowStepper' });
        await stepper.props('submit')();

        expect(submitModule).toHaveBeenCalled();
    });

    it('Step2_Details template events', async () => {
        const wrapper = shallowMount(Step2, globalMountOptions);

        const widgets = wrapper.findAllComponents('.mock-widget');
        for (const w of widgets) {
            await w.vm.$emit('update:value', 'test');
        }
    });

    it('Step3_Submission exhaustive logic and branch coverage', async () => {
        mockStoreState.draftId = 'test-draft-id';
        mockStoreState.draftData = {
            report_submission: { aliased_data: {} },
        } as DeepPartial<DocumentSubmissionDocumentSubmissionProcessAliasedData>;

        const wrapper = shallowMount(Step3, globalMountOptions);

        const uploader = wrapper.findComponent('.mock-uploader');
        expect(uploader.exists()).toBe(true);

        const titleWidget = findWidget(wrapper, 'report_title');
        const consultantWidget = findWidget(
            wrapper,
            'archaeological_consultant',
        );

        await titleWidget?.vm.$emit('update:value', {
            node_value: 'Test Title',
        });
        await consultantWidget?.vm.$emit('update:value', {
            node_value: [{ name: 'Consultant Inc.' }],
        });

        await uploader.vm.$emit('file-updated', {
            node_value: [{ name: 'report.pdf' }],
        });

        await uploader.vm.$emit('save-item');
        expect(saveDraftFieldToBackend).toHaveBeenCalled();

        await uploader.vm.$emit('select-item', 0);
        await uploader.vm.$emit('clear-pending');
        await uploader.vm.$emit('add-new');
        await uploader.vm.$emit('delete-item', 0);
    });

    it('Step4_Photographs exhaustive logic and branch coverage', async () => {
        mockStoreState.draftId = 'test-draft-id';
        mockStoreState.draftData = {
            submission_photographs: [],
        } as DeepPartial<DocumentSubmissionDocumentSubmissionProcessAliasedData>;

        const wrapper = shallowMount(Step4, globalMountOptions);

        const uploader = wrapper.findComponent('.mock-uploader');
        expect(uploader.exists()).toBe(true);

        const dateWidget = findWidget(wrapper, 'photograph_date');
        const viewWidget = findWidget(wrapper, 'photograph_view');
        const descWidget = findWidget(wrapper, 'photograph_description');

        await dateWidget?.vm.$emit('update:value', { node_value: '2023' });
        await dateWidget?.vm.$emit('update:value', {
            node_value: '2023-05-15',
        });
        await dateWidget?.vm.$emit('update:value', {
            node_value: 'invalid-string',
        });

        await viewWidget?.vm.$emit('update:value', { node_value: 'Front' });
        await descWidget?.vm.$emit('update:value', { node_value: 'Desc' });

        await uploader.vm.$emit('file-updated', {
            node_value: [{ name: 'photo.jpg' }],
        });

        await uploader.vm.$emit('save-item');
        expect(saveDraftFieldToBackend).toHaveBeenCalled();

        mockStoreState.draftData = {
            ...mockStoreState.draftData,
            submission_photographs: [
                {
                    aliased_data: {
                        photograph_view: {
                            node_value: { en: { value: 'Front' } },
                        },
                        photograph_description: {
                            node_value: { en: { value: 'Desc' } },
                        },
                    },
                },
            ],
        } as DeepPartial<DocumentSubmissionDocumentSubmissionProcessAliasedData>;

        await wrapper.vm.$nextTick();

        expect(
            (wrapper.vm as unknown as { isValid: () => boolean }).isValid(),
        ).toBe(true);

        await uploader.vm.$emit('select-item', 0);
        await uploader.vm.$emit('clear-pending');
        await uploader.vm.$emit('add-new');
        await uploader.vm.$emit('delete-item', 0);
    });

    it('Step99_Review parses edge case data shapes', () => {
        const Step99Stub = {
            template: '<div><slot :data="resourceData" :fields="[]" /></div>',
            props: ['resourceData'],
        };

        const directWrapper = shallowMount(Step99, {
            props: {
                resourceData: {
                    submission_photographs: {
                        aliased_data: { photograph_view: 'Front' },
                    },
                } as unknown,
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

        expect(directWrapper.html()).toContain('Submission Photographs');
    });
});
