import DOMPurify from 'dompurify';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import type { PermitAliasedData } from '@/bcap/types.ts';
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

export const localized = (value: string) => ({
    en: { value, direction: 'ltr' as const },
});

// The raw editable value of a string node (its node_value), for populating edit
// forms; falls back to display_value, then ''.
export const readString = (node: unknown): string => {
    const value = node as {
        node_value?: { en?: { value?: string | null } } | null;
        display_value?: string | null;
    } | null;
    return value?.node_value?.en?.value ?? value?.display_value ?? '';
};
