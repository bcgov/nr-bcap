import arches from 'arches';
import { fetchRequirementDetails } from '@/bcap/apps/Permit/api.ts';
import type {
    ProcessRequirement,
    PermitApplicationProcessModuleTile,
} from '@/bcap/client/types.gen.ts';
import type { QueryParam } from '@/bcap/types.ts';

export interface RequirementItem {
    name: string;
    title: string;
    resourceId: string;
    type: string;
    ministryAssignee: string;
    ministryAssigneeId: string;
    satisfied: boolean | null;
    internal: boolean | null;
    href: string;
    hostResourceId: string;
}

export interface ModuleRow {
    tileid: string;
    name: string;
    moduleId: string;
    completedDate: string;
    isCompleted: boolean;
    order: number;
    requirements: RequirementItem[];
    hostResourceId: string;
}

// Status glyphs, defined once so the legend, module pills, and requirement rows
// stay in sync. The app loads only Font Awesome solid, so every class is solid.
export const STATUS_ICON = {
    future: 'fa-solid fa-circle-notch',
    inProgress: 'fa-solid fa-clock',
    complete: 'fa-solid fa-check',
    unknown: 'fa-solid fa-circle-notch',
} as const;

// Requirement types whose submission can be viewed.
const SUBMISSION_TYPES = ['workflow', 'document submission'];

export const hasSubmission = (type: string): boolean =>
    SUBMISSION_TYPES.includes(type.toLowerCase());

export const isChecklist = (type: string): boolean =>
    type.toLowerCase().includes('checklist');

export const checklistHref = (id: string): string =>
    `${arches.urls.plugin('internal-permit-dashboard')}/checklist?id=${id}`;

export const editChecklistHref = (id: string): string =>
    `${arches.urls.plugin('internal-permit-dashboard')}/EditChecklist?id=${id}`;

// The checklist pages open in their own tab, so they need the permit (and the
// staff flag) on the URL to breadcrumb back to it.
export const withPermitContext = (
    href: string,
    permitId: string,
    staff: QueryParam,
): string => `${href}&permit=${permitId}${staff ? `&staff=${staff}` : ''}`;

const hrefFor = (type: string, id: string): string => {
    if (!id) return '';
    return isChecklist(type) ? checklistHref(id) : `/bcap/resource/${id}`;
};

// resourceId -> type/satisfied/internal/host, so rows rebuilt after a reorder keep
// their type/link/status without a fetch-driven flash.
interface RequirementMeta {
    name: string;
    type: string;
    satisfied: boolean;
    internal: boolean;
    hostResourceId: string;
}
const detailCache = new Map<string, RequirementMeta>();

const requirementName = (requirement: ProcessRequirement): string =>
    requirement.aliased_data?.requirement_identification?.aliased_data
        ?.requirement_name?.display_value || '';

const requirementType = (requirement: ProcessRequirement): string =>
    requirement.aliased_data?.requirement_identification?.aliased_data
        ?.is_template_requirement?.aliased_data?.process_requirement_type
        ?.display_value || '';

const requirementSatisfied = (requirement: ProcessRequirement): boolean =>
    requirement.aliased_data?.sub_requirement_assessment_n1?.aliased_data
        ?.requirement_status?.node_value === true;

const requirementInternal = (requirement: ProcessRequirement): boolean =>
    requirement.aliased_data?.requirement_identification?.aliased_data
        ?.is_template_requirement?.aliased_data?.is_internal_requirement
        ?.node_value === true;

const requirementHost = (requirement: ProcessRequirement): string =>
    requirement.aliased_data?.requirement_data?.aliased_data?.submission_data
        ?.aliased_data?.submission_data?.node_value?.[0]?.resourceId ?? '';

const moduleHost = (requirements: RequirementItem[]): string =>
    requirements
        .map(
            (requirement) =>
                detailCache.get(requirement.resourceId)?.hostResourceId,
        )
        .find(Boolean) ?? '';

const requirementItems = (
    tile: PermitApplicationProcessModuleTile,
): RequirementItem[] =>
    (tile.aliased_data?.process_requirement || [])
        .map((child) => ({
            order:
                child.aliased_data?.process_requirement_order?.node_value ?? 0,
            name:
                child.aliased_data?.process_requirement?.display_value ||
                'Requirement',
            resourceId:
                child.aliased_data?.process_requirement?.node_value?.[0]
                    ?.resourceId || '',
            ministryAssignee:
                child.aliased_data?.ministry_assignee?.display_value || '',
            ministryAssigneeId:
                child.aliased_data?.ministry_assignee?.node_value?.[0]
                    ?.resourceId || '',
        }))
        .sort((a, b) => a.order - b.order)
        .map(({ name, resourceId, ministryAssignee, ministryAssigneeId }) => {
            // Seed name/type/status from the cache so a rebuild (e.g. after
            // reorder) doesn't flash empty while the fetch re-runs.
            const meta = detailCache.get(resourceId);
            const type = meta?.type ?? '';
            return {
                name,
                title: meta?.name || name,
                resourceId,
                type,
                ministryAssignee,
                ministryAssigneeId,
                satisfied: meta?.satisfied ?? null,
                internal: meta?.internal ?? null,
                href: hrefFor(type, resourceId),
                hostResourceId: meta?.hostResourceId ?? '',
            };
        });

export const toRow = (tile: PermitApplicationProcessModuleTile): ModuleRow => {
    const requirements = requirementItems(tile);
    return {
        tileid: tile.tileid ?? '',
        name:
            tile.aliased_data?.module_name?.display_value || 'Untitled module',
        moduleId:
            tile.aliased_data?.module_id?.display_value ||
            String(tile.aliased_data?.module_id?.node_value ?? ''),
        completedDate:
            tile.aliased_data?.module_completed_date?.display_value || '',
        isCompleted: Boolean(
            tile.aliased_data?.is_module_completed?.node_value,
        ),
        order: tile.aliased_data?.module_order?.node_value ?? 0,
        requirements,
        hostResourceId: moduleHost(requirements),
    };
};

// Rows with at least one requirement we haven't cached; the rest are already
// hydrated, so they neither fetch nor show a loader.
export const rowsNeedingDetails = (rows: ModuleRow[]): ModuleRow[] =>
    rows.filter((row) =>
        row.requirements.some(
            (requirement) =>
                requirement.resourceId &&
                !detailCache.has(requirement.resourceId),
        ),
    );

// Fetch the missing requirement details and fill the rows in place.
export const hydrateRows = async (rows: ModuleRow[]) => {
    const ids = [
        ...new Set(
            rows
                .flatMap((row) => row.requirements)
                .map((requirement) => requirement.resourceId)
                .filter((id) => id && !detailCache.has(id)),
        ),
    ];
    const details = await fetchRequirementDetails(ids);
    for (const [id, detail] of Object.entries(details)) {
        detailCache.set(id, {
            name: requirementName(detail),
            type: requirementType(detail),
            satisfied: requirementSatisfied(detail),
            internal: requirementInternal(detail),
            hostResourceId: requirementHost(detail),
        });
    }
    for (const row of rows) {
        for (const requirement of row.requirements) {
            const meta = detailCache.get(requirement.resourceId);
            if (meta === undefined) continue;
            requirement.title = meta.name || requirement.name;
            requirement.type = meta.type;
            requirement.href = hrefFor(meta.type, requirement.resourceId);
            requirement.satisfied = meta.satisfied;
            requirement.internal = meta.internal;
            requirement.hostResourceId = meta.hostResourceId;
        }
        row.hostResourceId = moduleHost(row.requirements);
    }
};

// Keeps the cached status in step with an optimistic row update.
export const cacheSatisfied = (resourceId: string, satisfied: boolean) => {
    const meta = detailCache.get(resourceId);
    if (meta) meta.satisfied = satisfied;
};

export const clearRequirementCache = () => detailCache.clear();
