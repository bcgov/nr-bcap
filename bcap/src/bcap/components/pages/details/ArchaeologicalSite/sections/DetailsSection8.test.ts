import { it, expect } from 'vitest';
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
                                        tileid: 'sv',
                                        aliased_data: {
                                            remark_source: 's',
                                            remark_date: 'd',
                                            remark: 'r',
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
            tileid: 'sv',
            aliased_data: {
                general_remark_source: 's',
                general_remark_date: 'd',
                general_remark: 'r',
            },
        },
    ]);
});
