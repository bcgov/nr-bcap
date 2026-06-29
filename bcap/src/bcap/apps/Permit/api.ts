import arches from 'arches';
import { apiFetch } from '@/bcap/api.ts';
import type {
    ArchesDraftData,
    DraftNode,
    PermitApplicationResponse,
} from '@/bcap/types.ts';
import { type PermitAliasedData } from '@/bcap/types.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

export interface ResourceDraftResponse {
    id: string;
    data: ArchesDraftData;
}

export const fetchDraft = async (
    graphSlug: string,
    draftId: string,
): Promise<ResourceDraftResponse> => {
    const response = await apiFetch(
        `${arches.urls.api_resource_draft(graphSlug)}/${draftId}`,
    );
    return response.json();
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
    const response = await apiFetch(arches.urls.api_resource_draft(graphSlug), {
        method: 'POST',
        body: { data },
    });
    return response.json();
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
        method: 'DELETE',
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
    graphSlug: string = 'permit_application',
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

        const postResponse = await apiFetch(submitUrl, {
            method: 'POST',
            body: {
                draft_id: draftId,
                aliased_data: cleanPayload,
            },
        });

        const finalResource = await postResponse.json();
        console.log('Final resource created successfully!', finalResource);

        // Delete the draft after successful submission
        const deleteUrl = `${arches.urls.api_resource_draft(graphSlug)}/${draftId}`;
        await apiFetch(deleteUrl, { method: 'DELETE' });

        return finalResource;
    } catch (error) {
        console.error('Submission API failed:', error);
        throw error;
    }
};

// TODO: temporary. Investigation submission posts the raw draft straight to the
// generated investigation collection endpoint. We still need a real route that
// builds out our modules and associates them together easily, wiring
// Permit Application -> process requirements -> Investigation via the process
// requirement templates.
export const submitInvestigation = async (
    draftId: string,
    payload: ArchesDraftData,
): Promise<PermitApplicationResponse> => {
    try {
        // parent_resource_id is draft-only bookkeeping, not a graph alias, so
        // drop it before the create view validates the body against the graph.
        const aliasedData = { ...payload };
        delete aliasedData.parent_resource_id;
        const response = await apiFetch(arches.urls.api_investigation, {
            method: 'POST',
            body: { draft_id: draftId, aliased_data: aliasedData },
        });
        const finalResource = await response.json();
        await deleteDraft('investigation', draftId);
        return finalResource;
    } catch (error) {
        console.error('Investigation submission API failed:', error);
        throw error;
    }
};

export const fetchPermitDetails = async (
    permitId: string,
): Promise<PermitAliasedData | null | undefined> => {
    const url = arches.urls.api_resource('permit_application', permitId);

    const response = await apiFetch(url);
    const rawJson = await response.json();

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
    const url = arches.urls.api_resource('permit_application', permitId);

    await apiFetch(url, {
        method: 'PATCH',
        body: { aliased_data: { application_admin: adminPayload } },
    });
};
