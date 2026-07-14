import arches from 'arches';
import { apiFetch, apiFetchJson, HttpMethod } from '@/bcap/api.ts';
import type {
    ArchesDraftData,
    DraftNode,
    InvestigationDraft,
    PatchedPermitApplication,
    PermitApplicationAdminTileWritable,
    PermitApplicationResponse,
    PermitProcessModuleTileWritable,
} from '@/bcap/types.ts';
import {
    type ChecklistStep,
    type PermitAliasedData,
    type ProcessRequirement,
} from '@/bcap/types.ts';
import { localized } from '@/bcap/util.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

export interface ResourceDraftResponse {
    id: string;
    data: ArchesDraftData;
}

export const fetchDraft = async (
    graphSlug: string,
    draftId: string,
): Promise<ResourceDraftResponse> => {
    return apiFetchJson<ResourceDraftResponse>(
        `${arches.urls.api_resource_draft(graphSlug)}/${draftId}`,
    );
};

// parentResourceId, when given, is stored as a top-level key in the draft blob
// (not in aliased_data, which is validated against the graph on submit) so the
// parent resource's page can filter its own drafts. The backend verifies the
// user can access that resource before saving. It is stripped at submit time.
export const createDraft = async (
    graphSlug: string,
    parentResourceId?: string,
): Promise<ResourceDraftResponse> => {
    const data: { parent_resource_id?: string } = {};
    if (parentResourceId) {
        data.parent_resource_id = parentResourceId;
    }
    return apiFetchJson<ResourceDraftResponse>(
        arches.urls.api_resource_draft(graphSlug),
        {
            method: HttpMethod.Post,
            body: { data },
        },
    );
};

// Graphs that have a draft-backed workflow on the external dashboard. Each
// draft response carries its own graph_slug, so the dashboard can label and
// resume it into the right module.
const DRAFT_GRAPHS = [
    GraphSlug.PermitApplication,
    GraphSlug.Investigation,
    GraphSlug.Inspection,
    GraphSlug.Alteration,
];

export const fetchDrafts = async () => {
    const perGraph = await Promise.all(
        DRAFT_GRAPHS.map(async (graphSlug) => {
            try {
                const response = await apiFetch(
                    arches.urls.api_resource_draft(graphSlug),
                );
                const data = await response.json();
                return data.results || data || [];
            } catch (error) {
                console.error(`Failed to load ${graphSlug} drafts:`, error);
                return [];
            }
        }),
    );
    return perGraph.flat();
};

export const deleteDraft = async (
    graphSlug: string,
    draftId: string,
): Promise<void> => {
    await apiFetch(`${arches.urls.api_resource_draft(graphSlug)}/${draftId}`, {
        method: HttpMethod.Delete,
    });
};

export const fetchMyProjects = async () => {
    try {
        const url = `${arches.urls.dashboard_external}?status=CREATED_BY_ME`;

        const response = await apiFetch(url);
        const data = await response.json();
        return data.results || data || [];
    } catch (error) {
        console.error('Failed to load submitted projects:', error);
        return [];
    }
};

export const submitApplication = async (
    draftId: string,
    payload: ArchesDraftData,
    graphSlug: string = GraphSlug.PermitApplication,
): Promise<PermitApplicationResponse> => {
    try {
        const submitUrl = arches.urls.permit_application_create;
        const cleanPayload = JSON.parse(
            JSON.stringify(payload),
        ) as ArchesDraftData;
        // dummy application ID for POST
        cleanPayload.application_identification ??= {};
        cleanPayload.application_identification.aliased_data ??= {};
        cleanPayload.application_identification.aliased_data.application_id = {
            node_value: {
                en: {
                    value: 'DUMMY-APP-0000',
                    direction: 'ltr',
                },
            },
        } as unknown as DraftNode;

        const finalResource = await apiFetchJson<PermitApplicationResponse>(
            submitUrl,
            {
                method: HttpMethod.Post,
                body: {
                    draft_id: draftId,
                    aliased_data: cleanPayload,
                },
            },
        );
        console.log('Final resource created successfully!', finalResource);

        // Delete the draft after successful submission
        const deleteUrl = `${arches.urls.api_resource_draft(graphSlug)}/${draftId}`;
        await apiFetch(deleteUrl, { method: HttpMethod.Delete });

        return finalResource;
    } catch (error) {
        console.error('Submission API failed:', error);
        throw error;
    }
};

// Submit a permit module: the route creates the module's host resource from the
// payload, clones the module's process requirements onto the permit, links the
// workflow requirement to the host, and returns the created host resource. Pass
// a draftId to submit from a draft (deleted after); omit it for a staff
// quick-add that sends a placeholder payload directly.
export const submitModule = async (
    permitId: string,
    draftId: string | undefined,
    moduleSlug: GraphSlug,
    payload: ArchesDraftData,
): Promise<PermitApplicationResponse> => {
    try {
        // parent_resource_id is draft-only bookkeeping, not a graph alias, so
        // drop it before the serializer validates the body against the graph.
        const aliasedData = { ...payload };
        delete aliasedData.parent_resource_id;
        const url = arches.urls.seed_process_requirements(permitId, moduleSlug);
        const result = await apiFetchJson<PermitApplicationResponse>(url, {
            method: HttpMethod.Post,
            body: { aliased_data: aliasedData },
        });
        if (draftId) {
            await deleteDraft(moduleSlug, draftId);
        }
        return result;
    } catch (error) {
        console.error('Module submission API failed:', error);
        throw error;
    }
};

// The module host resources (eg investigations) already created on a permit,
// shaped like drafts so the same list rendering works for both.
export const fetchPermitModules = async (
    permitId: string,
    moduleSlug: GraphSlug,
): Promise<InvestigationDraft[]> => {
    try {
        const url = arches.urls.seed_process_requirements(permitId, moduleSlug);
        const response = await apiFetch(url);
        const hosts = (await response.json()) ?? [];
        return hosts.map(
            (host: {
                resourceinstanceid?: string;
                aliased_data?: unknown;
            }) => ({
                id: host.resourceinstanceid,
                graph_slug: moduleSlug,
                data: host.aliased_data,
            }),
        ) as InvestigationDraft[];
    } catch (error) {
        console.error('Failed to load permit module hosts:', error);
        return [];
    }
};

export const fetchRequirementDetails = async (
    ids: string[],
): Promise<Record<string, ProcessRequirement>> => {
    const entries = await Promise.all(
        ids.map(async (id): Promise<[string, ProcessRequirement] | null> => {
            try {
                const url = arches.urls.api_resource(
                    GraphSlug.ProcessRequirement,
                    id,
                );
                const json = await apiFetchJson<ProcessRequirement>(url);
                return [id, json];
            } catch (error) {
                console.error('Failed to load requirement detail:', error);
                return null;
            }
        }),
    );
    return Object.fromEntries(entries.filter((entry) => entry !== null));
};

export const fetchPermitDetails = async (
    permitId: string,
): Promise<PermitAliasedData | null | undefined> => {
    const url = arches.urls.api_resource(GraphSlug.PermitApplication, permitId);

    const rawJson = await apiFetchJson<PermitApplicationResponse>(url);

    if (!rawJson || !rawJson.aliased_data) {
        console.warn('API payload did not contain aliased_data');
        return null;
    }

    return rawJson.aliased_data as PermitAliasedData;
};

export const patchPermitSubmissionDate = async (
    permitId: string,
    adminPayload: {
        tileid?: string;
        aliased_data: { application_submission_date: string };
    },
): Promise<void> => {
    const url = arches.urls.api_resource(GraphSlug.PermitApplication, permitId);

    await apiFetch(url, {
        method: HttpMethod.Patch,
        body: { aliased_data: { application_admin: adminPayload } },
    });
};

export interface ModuleOrderPatch {
    tileid: string;
    order: number;
    name: string;
    moduleId: string;
}

// Persist a drag-reordered module list: patch each tile's module_order and a
// matching sortorder (arches' native row order) under application_admin. Send
// module_name and module_id too so the partial write keeps them, else the tile
// fails card validation or the save hook mints a fresh id.
export const patchModuleOrder = async (
    permitId: string,
    adminTileId: string,
    modules: ModuleOrderPatch[],
): Promise<void> => {
    const url = arches.urls.api_resource(GraphSlug.PermitApplication, permitId);

    const toModuleTile = (
        module: ModuleOrderPatch,
    ): PermitProcessModuleTileWritable => {
        const aliasedData: NonNullable<
            PermitProcessModuleTileWritable['aliased_data']
        > = {
            module_order: { node_value: module.order },
            module_name: { node_value: localized(module.name) },
        };
        // A blank tile has no id yet; send it only when present so the save hook
        // does not mint a fresh one.
        if (module.moduleId) {
            aliasedData.module_id = { node_value: module.moduleId };
        }
        return {
            tileid: module.tileid,
            sortorder: module.order,
            aliased_data: aliasedData,
        };
    };

    const applicationAdmin: PermitApplicationAdminTileWritable = {
        aliased_data: { process_module: modules.map(toModuleTile) },
    };
    if (adminTileId) {
        applicationAdmin.tileid = adminTileId;
    }

    const body: PatchedPermitApplication = {
        aliased_data: { application_admin: applicationAdmin },
    };

    await apiFetch(url, { method: HttpMethod.Patch, body });
};

export const removeModuleAndRequirements = async (
    permitId: string,
    moduleTileId: string,
): Promise<void> => {
    await apiFetch(arches.urls.permit_module(permitId, moduleTileId), {
        method: HttpMethod.Delete,
    });
};

export const reorderModuleRequirements = async (
    permitId: string,
    moduleTileId: string,
    requirementIds: string[],
): Promise<void> => {
    await apiFetch(arches.urls.module_requirements(permitId, moduleTileId), {
        method: HttpMethod.Patch,
        body: { order: requirementIds },
    });
};

export const addBlankRequirement = async (
    permitId: string,
    moduleTileId: string,
    name?: string,
): Promise<void> => {
    await apiFetch(arches.urls.module_requirements(permitId, moduleTileId), {
        method: HttpMethod.Post,
        body: name ? { name } : {},
    });
};

export const removeRequirement = async (
    permitId: string,
    moduleTileId: string,
    requirementId: string,
): Promise<void> => {
    await apiFetch(
        arches.urls.module_requirement(permitId, moduleTileId, requirementId),
        { method: HttpMethod.Delete },
    );
};

// Save a requirement's checklist: its name and the full ordered step list. The
// backend reconciles creates, edits, deletes, and reorders, so just send the
// current steps.
export const saveChecklist = async (
    requirementId: string,
    name: string,
    steps: ChecklistStep[],
): Promise<void> => {
    await apiFetch(arches.urls.requirement_checklist(requirementId), {
        method: HttpMethod.Patch,
        body: { name, steps },
    });
};
