// A loaded requirement resource, in the shape the detail-fetch reads. Carries
// the union of what the row-building and component tests read; a caller that
// ignores a field just leaves it at its default.
export const requirementDetail = (opts: {
    name?: string;
    type?: string;
    satisfied?: boolean;
    internal?: boolean;
    host?: string;
}) => ({
    aliased_data: {
        requirement_identification: {
            aliased_data: {
                requirement_name: { display_value: opts.name ?? '' },
                is_template_requirement: {
                    aliased_data: {
                        process_requirement_type: {
                            display_value: opts.type ?? 'Standard',
                        },
                        is_internal_requirement: {
                            node_value: opts.internal ?? false,
                        },
                    },
                },
            },
        },
        sub_requirement_assessment_n1: {
            aliased_data: {
                requirement_status: { node_value: opts.satisfied ?? false },
            },
        },
        requirement_data: {
            aliased_data: {
                submission_data: {
                    aliased_data: {
                        submission_data: {
                            node_value: opts.host
                                ? [{ resourceId: opts.host }]
                                : undefined,
                        },
                    },
                },
            },
        },
    },
});
