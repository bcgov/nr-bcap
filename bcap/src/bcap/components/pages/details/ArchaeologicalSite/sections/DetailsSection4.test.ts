import { mount } from '@vue/test-utils';
import DetailsSection4 from './DetailsSection4.vue';

const stubs = {
    DetailsSection: {
        template: '<div><slot name="sectionContent" /></div>',
    },
    StandardDataTable: true,
    EmptyState: true,
};

// Helper: mount with only biogeography-relevant props set, everything else
// absent so that no other StandardDataTable renders and index 0 is unambiguous.
function mountWithBiogeography(
    siteVisitData: unknown[],
    siteBiogeography: unknown[] = [],
    hriaData: unknown = undefined,
) {
    return mount(DetailsSection4, {
        props: {
            data: siteBiogeography.length
                ? { biogeography: siteBiogeography }
                : undefined,
            siteVisitData,
            hriaData,
        },
        global: { stubs },
    });
}

describe('DetailsSection4 biogeography source', () => {
    it('collects tiles from site_visit_location biogeography', () => {
        const tile = {
            tileid: 'bio-sv-1',
            aliased_data: { biogeography_type: 'Terrestrial' },
        };
        const wrapper = mountWithBiogeography([
            {
                aliased_data: {
                    site_visit_location: [
                        { aliased_data: { biogeography: [tile] } },
                    ],
                },
            },
        ]);

        const tables = wrapper.findAllComponents({ name: 'StandardDataTable' });
        expect(tables).toHaveLength(1);
        expect(tables[0].props('tableData')[0].tileid).toBe('bio-sv-1');
    });

    it('collects tiles from site data biogeography', () => {
        const tile = {
            tileid: 'bio-site-1',
            aliased_data: { biogeography_type: 'Aquatic' },
        };
        const wrapper = mountWithBiogeography([], [tile]);

        const tables = wrapper.findAllComponents({ name: 'StandardDataTable' });
        expect(tables).toHaveLength(1);
        expect(tables[0].props('tableData')[0].tileid).toBe('bio-site-1');
    });

    it('combines visit and site biogeography, visit tiles first', () => {
        const visitTile = { tileid: 'bio-visit', aliased_data: {} };
        const siteTile = { tileid: 'bio-site', aliased_data: {} };
        const wrapper = mountWithBiogeography(
            [
                {
                    aliased_data: {
                        site_visit_location: [
                            { aliased_data: { biogeography: [visitTile] } },
                        ],
                    },
                },
            ],
            [siteTile],
        );

        const tableData = wrapper
            .findAllComponents({ name: 'StandardDataTable' })[0]
            .props('tableData');
        expect(tableData).toHaveLength(2);
        expect(tableData[0].tileid).toBe('bio-visit');
        expect(tableData[1].tileid).toBe('bio-site');
    });

    it('flattens biogeography across multiple site visits and multiple locations', () => {
        const t1 = { tileid: 'sv1-loc1', aliased_data: {} };
        const t2 = { tileid: 'sv1-loc2', aliased_data: {} };
        const t3 = { tileid: 'sv2-loc1', aliased_data: {} };
        const wrapper = mountWithBiogeography([
            {
                aliased_data: {
                    site_visit_location: [
                        { aliased_data: { biogeography: [t1] } },
                        { aliased_data: { biogeography: [t2] } },
                    ],
                },
            },
            {
                aliased_data: {
                    site_visit_location: [
                        { aliased_data: { biogeography: [t3] } },
                    ],
                },
            },
        ]);

        const tableData = wrapper
            .findAllComponents({ name: 'StandardDataTable' })[0]
            .props('tableData');
        expect(tableData.map((r: { tileid: string }) => r.tileid)).toEqual([
            'sv1-loc1',
            'sv1-loc2',
            'sv2-loc1',
        ]);
    });

    it('renders no biogeography table when all sources are empty', () => {
        const wrapper = mountWithBiogeography([]);
        expect(
            wrapper.findAllComponents({ name: 'StandardDataTable' }),
        ).toHaveLength(0);
    });
});

describe('DetailsSection4 discontinued biogeography (HRIA)', () => {
    it('shows the discontinued table when hriaData has biogeography', () => {
        const hriaBio = { aliased_data: { biogeography_type: 'legacy' } };
        const wrapper = mountWithBiogeography([], [], {
            aliased_data: { biogeography: hriaBio },
        });

        const tables = wrapper.findAllComponents({ name: 'StandardDataTable' });
        expect(tables).toHaveLength(1);
        // The template wraps the value in an array and filters falsy values.
        expect(tables[0].props('tableData')).toEqual([hriaBio]);
    });

    it('does not show the discontinued table when hriaData has no biogeography', () => {
        const wrapper = mountWithBiogeography([], [], {
            aliased_data: {},
        });

        expect(
            wrapper.findAllComponents({ name: 'StandardDataTable' }),
        ).toHaveLength(0);
    });

    it('shows both live and discontinued tables when both sources have data', () => {
        const liveTile = { tileid: 'live', aliased_data: {} };
        const hriaBio = { aliased_data: { biogeography_type: 'legacy' } };
        const wrapper = mountWithBiogeography([], [liveTile], {
            aliased_data: { biogeography: hriaBio },
        });

        const tables = wrapper.findAllComponents({ name: 'StandardDataTable' });
        expect(tables).toHaveLength(2);
    });
});
