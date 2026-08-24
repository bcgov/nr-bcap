import { mount } from '@vue/test-utils';
import DetailsSection8 from './DetailsSection8.vue';

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
        global: {
            stubs: {
                // Named slot — auto-stubs skip these, so pass it through.
                DetailsSection: {
                    template: '<div><slot name="sectionContent" /></div>',
                },
                StandardDataTable: true,
                EmptyState: true,
            },
        },
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
