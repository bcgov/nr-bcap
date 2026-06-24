import DOMPurify from 'dompurify';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';
import { z } from 'zod';
import type { ReviewField } from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';

export const sanitizeHtml = (html: string | undefined): string => {
    if (!html) return '';
    return DOMPurify.sanitize(html);
};

export const formatDateTime = (isoString: string | null): string | null => {
    if (!isoString) return null;

    const date = new Date(isoString);
    const dateStr = date.toLocaleDateString('en-CA');

    const timeStr = date
        .toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            second: '2-digit',
            hour12: true,
        })
        .toLowerCase()
        .replace('am', 'a.m.')
        .replace('pm', 'p.m.');

    return `${dateStr}, ${timeStr}`;
};

/** Resolve a key (inside aliased_data) to an AliasedNodeData */
function getNode(row: unknown, key: string): AliasedNodeData | null {
    if (!row || typeof row !== 'object') return null;

    const aliased = (row as Record<string, unknown>)?.['aliased_data'];
    if (!aliased || typeof aliased !== 'object') return null;

    const cur = (aliased as Record<string, unknown>)?.[key];
    if (!cur || typeof cur !== 'object') return null;

    const maybe = cur as Partial<AliasedNodeData>;
    return 'display_value' in maybe && 'node_value' in maybe
        ? (maybe as AliasedNodeData)
        : null;
}

export const getDisplayValue = (value: AliasedNodeData | null | undefined) => {
    return value?.node_value ? value.display_value : '';
};

export const getNodeDisplayValue = (row: unknown, path: string) => {
    return getDisplayValue(getNode(row, path));
};

export const isEmpty = (value: AliasedNodeData | null | undefined): boolean => {
    return !value?.node_value;
};

export function isAliasedNodeData(value: unknown): value is AliasedNodeData {
    if (!value || typeof value !== 'object') return false;
    const maybe = value as Partial<AliasedNodeData>;
    return (
        'display_value' in maybe && 'node_value' in maybe && 'details' in maybe
    );
}

export const currentDateValue = function () {
    const now = new Date().toISOString().split('T')[0];
    return {
        display_value: now,
        node_value: now,
        details: [] as never[],
    };
};

export const getCsrfToken = (): string => {
    return (
        document.cookie
            .split('; ')
            .find((row) => row.startsWith('csrftoken='))
            ?.split('=')[1] || ''
    );
};

export const saveFieldToBackend = async (
    draftId: string,
    graphSlug: string,
    fullDraftData: ArchesDraftData,
) => {
    try {
        const patchUrl = `/bcap/api/resource_draft/${graphSlug}/${draftId}`;

        const response = await fetch(patchUrl, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                data: fullDraftData,
            }),
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        console.log('Successfully auto-saved full draft data.');
    } catch (error) {
        console.error('Failed to auto-save draft data:', error);
    }
};

let globalTimeoutId: ReturnType<typeof setTimeout>;

export const updateDraftValue = (
    draftDataValue: ArchesDraftData | undefined,
    draftId: string | null | undefined,
    graphSlug: string,
    newValue: AliasedNodeData,
    attribute_name: string,
    node_group_alias: string | string[],
) => {
    if (!draftDataValue) return;

    const groups = Array.isArray(node_group_alias)
        ? node_group_alias
        : [node_group_alias];

    let currentLevel = draftDataValue as Record<string, unknown>;

    groups.forEach((group, index) => {
        const match = group.match(/^(.+)\[(\d+)\]$/);

        if (match) {
            const name = match[1];
            const arrIndex = parseInt(match[2], 10);

            if (!currentLevel[name]) currentLevel[name] = [];
            const arr = currentLevel[name] as Record<string, unknown>[];

            if (!arr[arrIndex]) arr[arrIndex] = { aliased_data: {} };

            if (index === groups.length - 1) {
                const target = arr[arrIndex].aliased_data as Record<
                    string,
                    unknown
                >;
                target[attribute_name] = newValue;
            } else {
                currentLevel = arr[arrIndex].aliased_data as Record<
                    string,
                    unknown
                >;
            }
        } else {
            if (!currentLevel[group])
                currentLevel[group] = { aliased_data: {} };
            const node = currentLevel[group] as {
                aliased_data: Record<string, unknown>;
            };

            if (index === groups.length - 1) {
                node.aliased_data[attribute_name] = newValue;
            } else {
                currentLevel = node.aliased_data;
            }
        }
    });

    clearTimeout(globalTimeoutId);

    globalTimeoutId = setTimeout(() => {
        if (draftId) {
            saveFieldToBackend(draftId, graphSlug, draftDataValue);
        }
    }, 1000);
};

// For base module review page
export const ArchesNode = z
    .object({
        display_value: z.string().nullish(),
    })
    .passthrough();

export const PermitPayloadSchema = z
    .object({
        aliased_data: z
            .object({
                application_identification: z
                    .object({
                        aliased_data: z
                            .object({
                                project_name: ArchesNode.nullish(),
                                application_id: ArchesNode.nullish(),
                                is_replacement: ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),
                application_contacts: z
                    .object({
                        aliased_data: z
                            .object({
                                application_proponent: ArchesNode.nullish(),
                                has_retained_archaeologist:
                                    ArchesNode.nullish(),
                                rationale_for_no_archaeologist:
                                    ArchesNode.nullish(),
                                application_archaeologist: ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),
                proposed_project: z
                    .object({
                        aliased_data: z
                            .object({
                                scope_of_work: ArchesNode.nullish(),
                                project_type: ArchesNode.nullish(),
                                project_description: ArchesNode.nullish(),
                                project_boundary: z.unknown().nullish(),
                                development_project_details: z
                                    .object({
                                        aliased_data: z
                                            .object({
                                                industrial_sector:
                                                    ArchesNode.nullish(),
                                                alteration_details:
                                                    ArchesNode.nullish(),
                                            })
                                            .passthrough()
                                            .nullish(),
                                    })
                                    .passthrough()
                                    .nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),
                archaeological_assessment_plan: z
                    .object({
                        aliased_data: z
                            .object({
                                section_1_overview: z
                                    .object({
                                        aliased_data: z
                                            .object({
                                                assessment_approach:
                                                    ArchesNode.nullish(),
                                            })
                                            .passthrough()
                                            .nullish(),
                                    })
                                    .passthrough()
                                    .nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),
                first_nation_consultation: z
                    .object({
                        aliased_data: z
                            .object({
                                fn_file_numbers: ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),
                application_admin: z
                    .object({
                        tileid: z.string().nullish(),
                        nodegroup: z.string().nullish(),
                        aliased_data: z
                            .object({
                                application_submission_date:
                                    ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),
                inspection: z.array(z.unknown()).nullish(),
                investigation: z.array(z.unknown()).nullish(),
            })
            .passthrough()
            .nullish(),
    })
    .passthrough();

export type PermitAliasedData = z.infer<
    typeof PermitPayloadSchema
>['aliased_data'];

export const getBasicInfoFields = (
    aliased: PermitAliasedData | null | undefined,
): ReviewField[] => {
    if (!aliased) return [];

    const ident = aliased.application_identification?.aliased_data;
    const contacts = aliased.application_contacts?.aliased_data;
    const project = aliased.proposed_project?.aliased_data;
    const devDetails = project?.development_project_details?.aliased_data;

    return [
        { label: 'Project Name', value: ident?.project_name?.display_value },
        {
            label: 'Application ID',
            value: ident?.application_id?.display_value,
        },
        {
            label: 'Application Proponent',
            value: contacts?.application_proponent?.display_value,
        },
        {
            label: 'Has Retained Archaeologist',
            value: contacts?.has_retained_archaeologist?.display_value,
        },
        {
            label: 'Rationale For No Archaeologist',
            value: contacts?.rationale_for_no_archaeologist?.display_value,
        },
        {
            label: 'Application Archaeologist',
            value: contacts?.application_archaeologist?.display_value,
        },
        { label: 'Project Type', value: project?.project_type?.display_value },
        {
            label: 'Project Description',
            value: project?.project_description?.display_value,
            type: 'html',
        },
        {
            label: 'Scope of Work',
            value: project?.scope_of_work?.display_value,
            type: 'html',
        },
        {
            label: 'Industrial Sector',
            value: devDetails?.industrial_sector?.display_value,
        },
        {
            label: 'Project Boundary',
            value: project?.project_boundary,
            type: 'map',
            nodeAlias: 'project_boundary',
        },
    ];
};
