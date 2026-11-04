import { mount } from '@vue/test-utils';
import DetailsSection8 from './DetailsSection8.vue';

const stubs = {
    DetailsSection: {
        template: '<div><slot name="sectionContent" /></div>',
    },
    StandardDataTable: true,
    EmptyState: true,
};

it('merges arch-site and mapped site-visit remarks into the general remarks table', () => {
    const wrapper = mount(DetailsSection8, {
        props: {
            data: {
                aliased_data: {
                    general_remark_information: [
                        {
                            tileid: 'arch',
                            aliased_data: {
                                general_remark_source: 'arch source',
                                general_remark_date: 'arch date',
                                general_remark: 'arch text',
                            },
                        },
                    ],
                },
            },
            siteVisitData: [
                {
                    aliased_data: {
                        remarks_and_recommendations: {
                            aliased_data: {
                                general_remark: [
                                    {
                                        tileid: 'sv1-a',
                                        aliased_data: {
                                            remark_source: 's1a',
                                            remark_date: 'd1a',
                                            remark: 'r1a',
                                        },
                                    },
                                    {
                                        tileid: 'sv1-b',
                                        aliased_data: {
                                            remark_source: 's1b',
                                            remark_date: 'd1b',
                                            remark: 'r1b',
                                        },
                                    },
                                ],
                            },
                        },
                    },
                },
                {
                    aliased_data: {
                        remarks_and_recommendations: {
                            aliased_data: {
                                general_remark: [
                                    {
                                        tileid: 'sv2-a',
                                        aliased_data: {
                                            remark_source: 's2a',
                                            remark_date: 'd2a',
                                            remark: 'r2a',
                                        },
                                    },
                                ],
                            },
                        },
                    },
                },
            ],
        },
        global: { stubs },
    });

    const table = wrapper.findAllComponents({ name: 'StandardDataTable' })[0];
    expect(table.props('tableData')).toEqual([
        {
            tileid: 'arch',
            aliased_data: {
                general_remark_source: 'arch source',
                general_remark_date: 'arch date',
                general_remark: 'arch text',
            },
        },
        {
            tileid: 'sv1-a',
            aliased_data: {
                general_remark_source: 's1a',
                general_remark_date: 'd1a',
                general_remark: 'r1a',
            },
        },
        {
            tileid: 'sv1-b',
            aliased_data: {
                general_remark_source: 's1b',
                general_remark_date: 'd1b',
                general_remark: 'r1b',
            },
        },
        {
            tileid: 'sv2-a',
            aliased_data: {
                general_remark_source: 's2a',
                general_remark_date: 'd2a',
                general_remark: 'r2a',
            },
        },
    ]);
});

describe('DetailsSection8 recommendations', () => {
    it('collects recommendation tiles from site visits', () => {
        const tile = {
            tileid: 'rec-1',
            aliased_data: {
                recorders_recommendation: {
                    display_value: 'Record it',
                    node_value: 'Record it',
                    details: [],
                },
                archaeology_branch_recommendation: {
                    display_value: 'Approve',
                    node_value: 'Approve',
                    details: [],
                },
            },
        };
        const wrapper = mount(DetailsSection8, {
            props: {
                data: undefined,
                siteVisitData: [
                    {
                        aliased_data: {
                            remarks_and_recommendations: {
                                aliased_data: { recommendation: [tile] },
                            },
                        },
                    },
                ],
            },
            global: { stubs },
        });

        // No general remarks data, so index 0 is the Recommendations table.
        const tables = wrapper.findAllComponents({ name: 'StandardDataTable' });
        expect(tables[0].props('tableData')[0].tileid).toBe('rec-1');
    });

    it('merges recommendation tiles from multiple site visits', () => {
        const t1 = { tileid: 'rec-sv1', aliased_data: {} };
        const t2 = { tileid: 'rec-sv2', aliased_data: {} };
        const wrapper = mount(DetailsSection8, {
            props: {
                data: undefined,
                siteVisitData: [
                    {
                        aliased_data: {
                            remarks_and_recommendations: {
                                aliased_data: { recommendation: [t1] },
                            },
                        },
                    },
                    {
                        aliased_data: {
                            remarks_and_recommendations: {
                                aliased_data: { recommendation: [t2] },
                            },
                        },
                    },
                ],
            },
            global: { stubs },
        });

        const tableData = wrapper
            .findAllComponents({ name: 'StandardDataTable' })[0]
            .props('tableData');
        expect(tableData.map((r: { tileid: string }) => r.tileid)).toEqual([
            'rec-sv1',
            'rec-sv2',
        ]);
    });

    it('does not render the recommendations table when no site visits have recommendations', () => {
        const wrapper = mount(DetailsSection8, {
            props: {
                data: undefined,
                siteVisitData: [
                    {
                        aliased_data: {
                            remarks_and_recommendations: {
                                aliased_data: { general_remark: [] },
                            },
                        },
                    },
                ],
            },
            global: { stubs },
        });

        // No recommendations → the recommendations table should not be visible.
        const tables = wrapper.findAllComponents({ name: 'StandardDataTable' });
        tables.forEach((t) => {
            const cols: { field: string }[] =
                t.props('columnDefinitions') ?? [];
            expect(
                cols.some((c) => c.field === 'recorders_recommendation'),
            ).toBe(false);
        });
    });
});
