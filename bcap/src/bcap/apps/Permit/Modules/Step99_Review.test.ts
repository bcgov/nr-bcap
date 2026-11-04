import { shallowMount } from '@vue/test-utils';
import Step99_Review from './Step99_Review.vue';
import { useDraftStore } from '@/bcap/stores/draft.ts';

// FieldSet and the summary are presentational; stub them so the test asserts the
// computed review fields rather than their rendering internals.
vi.mock('primevue/fieldset', () => ({
    default: { template: '<div><slot /></div>' },
}));
vi.mock('@/bcap/apps/Permit/Modules/ReviewSummary.vue', () => ({
    default: {
        name: 'GenericReviewSummary',
        props: ['fields'],
        template: '<div />',
        type: 'text',
    },
}));

type ReviewVm = { reviewFields: { label: string; value: unknown }[] };

describe('Step99_Review.vue (shared)', () => {
    it('walks the draft data into humanized review fields', () => {
        useDraftStore().loadDraft('d1', {
            submission_information: {
                aliased_data: {
                    investigation_identification: {
                        display_value: 'sdfgfsgsg',
                    },
                },
            },
        } as never);

        const wrapper = shallowMount(Step99_Review);
        const vm = wrapper.vm as unknown as ReviewVm;

        expect(vm.reviewFields).toEqual([
            {
                label: 'Investigation Identification',
                value: 'sdfgfsgsg',
                nodeAlias: 'investigation_identification',
                type: 'text',
            },
        ]);
    });

    it('recurses nested node groups', () => {
        useDraftStore().loadDraft('d1', {
            personnel: {
                aliased_data: {
                    field_director: {
                        aliased_data: {
                            director_name: { display_value: 'Ada' },
                        },
                    },
                },
            },
        } as never);

        const vm = shallowMount(Step99_Review).vm as unknown as ReviewVm;

        expect(vm.reviewFields).toEqual([
            {
                label: 'Director Name',
                value: 'Ada',
                nodeAlias: 'director_name',
                type: 'text',
            },
        ]);
    });

    it('reads resourceData (not the draft) in the submitted view', () => {
        useDraftStore().loadDraft('d1', {
            x: { aliased_data: { a: { display_value: 'from-draft' } } },
        } as never);

        const wrapper = shallowMount(Step99_Review, {
            props: {
                isSubmittedView: true,
                resourceData: {
                    y: {
                        aliased_data: { b: { display_value: 'from-resource' } },
                    },
                } as never,
            },
        });
        const vm = wrapper.vm as unknown as ReviewVm;

        expect(vm.reviewFields).toEqual([
            {
                label: 'B',
                value: 'from-resource',
                nodeAlias: 'b',
                type: 'text',
            },
        ]);
        expect(wrapper.find('.review-intro').text()).toContain(
            'successfully submitted',
        );
    });
});

it('detects HTML content and assigns the html type', () => {
    useDraftStore().loadDraft('d1', {
        report_details: {
            aliased_data: {
                report_recommendations: {
                    display_value: '<p>Rich text formatting</p>',
                },
                standard_notes: {
                    display_value: 'Just regular plain text',
                },
            },
        },
    } as never);

    const vm = shallowMount(Step99_Review).vm as unknown as ReviewVm;

    expect(vm.reviewFields).toEqual([
        {
            label: 'Report Recommendations',
            value: '<p>Rich text formatting</p>',
            nodeAlias: 'report_recommendations',
            type: 'html',
        },
        {
            label: 'Standard Notes',
            value: 'Just regular plain text',
            nodeAlias: 'standard_notes',
            type: 'text',
        },
    ]);
});
