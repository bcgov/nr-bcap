import { defineComponent } from 'vue';
import { shallowMount } from '@vue/test-utils';

// Heavy arches deps the sections pull in -- stub for a render smoke test.
vi.mock('@/bcgov_arches_common/components/SimpleMap/SimpleMap.vue', () => ({
    default: defineComponent({ name: 'SimpleMap', template: '<div />' }),
}));
vi.mock('@/arches_vue_components/widgets/constants.ts', () => ({
    VIEW: 'view',
    EDIT: 'edit',
}));
vi.mock('@/bcgov_arches_common/composables/useTileEditLog.ts', async () => {
    const { ref } = await import('vue');
    return {
        useTileEditLog: () => ({
            getEditLogForTile: () => null,
            formatEditLog: () => '',
            processedData: ref([]),
        }),
        useSingleTileEditLog: () => ({ processedData: ref(null) }),
    };
});
vi.mock('@/bcap/composables/useHierarchicalData.ts', async () => {
    const { ref } = await import('vue');
    return {
        useHierarchicalData: () => ({
            processedData: ref([]),
            isProcessing: ref(false),
        }),
    };
});

import DetailsSection2 from './DetailsSection2.vue';
import DetailsSection3 from './DetailsSection3.vue';
import DetailsSection4 from './DetailsSection4.vue';
import DetailsSection5 from './DetailsSection5.vue';
import DetailsSection6 from './DetailsSection6.vue';
import DetailsSection7 from './DetailsSection7.vue';
import DetailsSection9 from './DetailsSection9.vue';

// Minimal populated shapes -- enough to flip each section's "has data" branches
// that read props.data directly. Fields are optional-chained in the components,
// so a shallow shape exercises the populated render path.
const node = (v: string) => ({ display_value: v, node_value: v, details: [] });

const fixtures = [
    {
        name: 'DetailsSection2',
        component: DetailsSection2,
        data: {
            aliased_data: {
                authority: [{ aliased_data: {} }],
                site_names: [{ aliased_data: {} }],
                site_decision: { aliased_data: {} },
                site_alert: { aliased_data: {} },
            },
        },
        // These sections also declare required hria/child/site-visit props; pass
        // them present (empty/undefined) so Vue's required check is satisfied.
        extraProps: { hriaData: undefined, childSiteData: undefined },
    },
    {
        name: 'DetailsSection3',
        component: DetailsSection3,
        data: [
            {
                descriptors: {
                    en: { name: 'Visit 1', map_popup: '', description: '' },
                },
                aliased_data: {
                    site_visit_details: {
                        aliased_data: {
                            last_date_of_site_visit: node('2024-01-01'),
                        },
                    },
                },
            },
        ],
    },
    {
        name: 'DetailsSection4',
        component: DetailsSection4,
        data: {
            elevation: {
                aliased_data: { elevation_comments: [{ aliased_data: {} }] },
            },
        },
        extraProps: { siteVisitData: [], hriaData: undefined },
    },
    {
        name: 'DetailsSection5',
        component: DetailsSection5,
        data: { aliased_data: {} },
        extraProps: { hriaData: undefined },
    },
    {
        name: 'DetailsSection6',
        component: DetailsSection6,
        data: { aliased_data: { site_typology: [{ aliased_data: {} }] } },
    },
    {
        name: 'DetailsSection7',
        component: DetailsSection7,
        data: {
            aliased_data: { restricted_ancestral_remains_remark: node('x') },
        },
    },
    {
        name: 'DetailsSection9',
        component: DetailsSection9,
        data: {
            aliased_data: {
                publication_reference: [{ aliased_data: {} }],
                related_site_documents: [{ aliased_data: {} }],
                site_images: [{ aliased_data: {} }],
            },
        },
    },
];

describe('ArchaeologicalSite detail sections', () => {
    for (const { name, component, data, extraProps = {} } of fixtures) {
        it(`${name} renders the empty state with no data`, () => {
            const wrapper = shallowMount(component, {
                props: { data: undefined, ...extraProps },
            });
            expect(wrapper.html()).toBeTruthy();
        });

        it(`${name} renders the populated state with data`, () => {
            const wrapper = shallowMount(component, {
                props: { data, ...extraProps },
            });
            expect(wrapper.html()).toBeTruthy();
        });
    }
});
