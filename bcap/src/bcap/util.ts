import DOMPurify from 'dompurify';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import type {
    FileListAliasedNodeDataWritable,
    PermitApplicationResourceAliasedData,
} from '@/bcap/client/types.gen.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';
import type { ReviewField } from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';

export const sanitizeHtml = (html: string | undefined): string => {
    if (!html) return '';
    return DOMPurify.sanitize(html);
};

export const formatDate = (iso: string | null | undefined): string =>
    iso ? new Date(iso).toLocaleDateString() : '';

export const formatTimestamp = (iso: string | null | undefined): string =>
    new Date(iso ?? 0).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });

// Avatar initials. Names are stored "Last, First", so the parts are reversed to
// read the way a person is addressed.
export const initials = (name: string): string =>
    name
        .split(/[\s,.]+/)
        .filter(Boolean)
        .map((part) => part[0].toUpperCase())
        .slice(0, 2)
        .reverse()
        .join('');

export const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const downloadFile = async (
    url: string,
    name: string,
): Promise<void> => {
    try {
        const response = await fetch(url, { credentials: 'same-origin' });
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = name;
        // The anchor must be in the document for click() to trigger in Firefox.
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
    } catch (error) {
        console.error('Failed to download file:', error);
        window.open(url, '_blank');
    }
};

// A picked File only lives in memory until submit; it can't be stored.
export const dropFiles = (_key: string, value: unknown) =>
    value instanceof File ? undefined : value;

// One multipart part per file a file-list node is holding, keyed the way arches
// reads them back off the request. The tileid scopes the key so each tile claims
// only its own uploads, and is minted here when the tile has none yet.
export const fileParts = (
    tile: { tileid?: string | null },
    node: FileListAliasedNodeDataWritable | null | undefined,
): Array<[string, File]> =>
    (node?.node_value ?? []).flatMap((entry) => {
        if (!(entry.file instanceof File)) return [];
        tile.tileid ??= crypto.randomUUID();
        return [[`file-list_${tile.tileid}-${entry.node_id}`, entry.file]];
    });

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

export const getDisplayValue = (value: AliasedNodeData | null | undefined) => {
    return value?.node_value ? value.display_value : '';
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

export const getCsrfToken = (): string => {
    return (
        document.cookie
            .split('; ')
            .find((row) => row.startsWith('csrftoken='))
            ?.split('=')[1] || ''
    );
};

// Reads a permit's basic-info tiles by alias, so it takes either the generated
// resource shape (filing summary) or the loose draft shape (workflow review).
export const getBasicInfoFields = (
    aliased:
        | PermitApplicationResourceAliasedData
        | ArchesDraftData
        | null
        | undefined,
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
            label: 'Submission Type',
            value: ident?.filing_type?.display_value,
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
