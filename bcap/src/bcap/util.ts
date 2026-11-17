import DOMPurify from 'dompurify';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';
import type {
    BcapServiceRequestResourceAliasedData,
    FileListAliasedNodeData,
    FileListAliasedNodeDataWritable,
    GeojsonFeatureCollectionAliasedNodeData,
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
        timeZone: 'America/Vancouver',
        timeZoneName: 'short',
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

export const dropFiles = (_key: string, value: unknown) =>
    value instanceof File ? undefined : value;

// One multipart part per file a file-list node is holding, keyed the way arches
// reads them back off the request. The tileid scopes the key so each tile claims
// only its own uploads, and is minted here when the tile has none yet.
export const fileParts = (
    tile: { tileid?: string | null },
    node: FileListAliasedNodeDataWritable | null | undefined,
): Array<[string, File]> => {
    const parts: Array<[string, File]> = [];
    for (const entry of node?.node_value ?? []) {
        if (!(entry.file instanceof File)) continue;
        tile.tileid ??= crypto.randomUUID();
        parts.push([`file-list_${tile.tileid}-${entry.node_id}`, entry.file]);
    }
    return parts;
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

export const getDisplayValue = (
    value: { node_value?: unknown; display_value?: string } | null | undefined,
) => {
    return value?.node_value ? (value.display_value ?? '') : '';
};

export const isEmpty = (
    value: { node_value?: unknown } | null | undefined,
): boolean => {
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
            // A draft's boundary is the loose draft node, but the same geojson.
            value: project?.project_boundary as
                GeojsonFeatureCollectionAliasedNodeData | null | undefined,
            type: 'map',
            nodeAlias: 'project_boundary',
        },
    ];
};

const SR_PROPERTY_PRIVATE = 'Private Property';
const SR_PROPERTY_CROWN = 'Public (Crown) Land';

export const getServiceRequestInfoFields = (
    srData:
        | BcapServiceRequestResourceAliasedData
        | ArchesDraftData
        | null
        | undefined,
): ReviewField[] => {
    if (!srData) return [];
    const sr = srData as unknown as BcapServiceRequestResourceAliasedData;
    const ident = sr.service_request_identification?.aliased_data;
    const contacts = sr.service_request_contacts?.aliased_data;
    const project = sr.proposed_project?.aliased_data;
    const location = sr.service_request_location?.aliased_data;

    const propertyType = location?.property_type?.display_value ?? '';
    const isPrivate = propertyType === SR_PROPERTY_PRIVATE;
    const isCrownLand = propertyType === SR_PROPERTY_CROWN;
    // "Other" shows any fields that were entered, so it falls through to both.
    const isOther = !isPrivate && !isCrownLand && Boolean(propertyType);

    const fields: ReviewField[] = [
        {
            label: 'Service Request Type',
            value: ident?.service_request_type?.display_value,
        },
        { label: 'Project Name', value: project?.project_name?.display_value },
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
        { label: 'Property Type', value: propertyType || undefined },
    ];

    // Private or Other: show street address fields.
    if (isPrivate || isOther) {
        const addr = location?.bc_property_address?.[0]?.aliased_data;
        if (addr) {
            fields.push(
                {
                    label: 'Street Number',
                    value: addr.street_number?.display_value,
                },
                {
                    label: 'Street Name',
                    value: addr.street_name?.display_value,
                },
                { label: 'City', value: addr.city?.display_value },
                {
                    label: 'Postal Code',
                    value: addr.postal_code?.display_value,
                },
                {
                    label: 'Address Remarks',
                    value: addr.address_remarks?.display_value,
                },
            );
        }
    }

    // PIDs are stored as feature properties when parcels are added via the PID
    // lookup on the Details step. Extract unique values from the boundary.
    const boundaryFeatures =
        location?.service_request_boundary?.node_value?.features ?? [];
    const pids = [
        ...new Set(
            boundaryFeatures
                .map(
                    (f) =>
                        (f.properties?.['PID_FORMATTED'] ||
                            f.properties?.['PID']) as string | undefined,
                )
                .filter((pid): pid is string => Boolean(pid)),
        ),
    ];
    if (pids.length) {
        fields.push({ label: 'Parcel ID(s)', value: pids.join(', ') });
    }

    // Crown Land or Other: show tenure fields.
    if (isCrownLand || isOther) {
        const tenureData = location?.crown_land_tenure_type?.aliased_data;
        if (tenureData) {
            fields.push(
                {
                    label: 'Crown Land Tenure Type',
                    value: tenureData.crown_land_tenure_type?.display_value,
                },
                {
                    label: 'Tenure Description',
                    value: tenureData.tenure_description?.display_value,
                },
            );
            const survey =
                tenureData.crown_land_survey_information?.aliased_data;
            if (survey) {
                fields.push(
                    {
                        label: 'Districts',
                        value: survey.districts?.display_value,
                    },
                    {
                        label: 'Land Title',
                        value: survey.land_title?.display_value,
                    },
                    { label: 'PIN', value: survey.pin_n1?.display_value },
                );
            }
        }
    }

    fields.push({
        label: 'Service Request Boundary',
        value: location?.service_request_boundary as
            GeojsonFeatureCollectionAliasedNodeData | null | undefined,
        type: 'map',
        graphSlug: 'bcap_service_request',
        nodeAlias: 'service_request_boundary',
    });

    return fields;
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

// MultiFileUploader forwards the widget's bare node_value, so a file update
// arrives as the file array rather than the node it belongs to.
export const asFileNode = (
    value: AliasedNodeData | NonNullable<FileListAliasedNodeData['node_value']>,
): AliasedNodeData =>
    Array.isArray(value)
        ? { display_value: '', node_value: value, details: [] }
        : value;
