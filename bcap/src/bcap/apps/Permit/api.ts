import arches from 'arches';
import { apiFetch, apiFetchJson, HttpMethod } from '@/bcap/api.ts';
import { localized, formatTimestamp, dropFiles } from '@/bcap/util.ts';
import type {
    DashboardStatus,
    MessageThread,
    ArchesDraftData,
    DraftNode,
    FormattedMessage,
    NewBcapMessage,
    WorkflowDraft,
} from '@/bcap/types.ts';
export type { DashboardStatus };
import type {
    ApiContributorsAssignableListResponse,
    ApiDashboardExternalRetrieveData,
    ApiWorkflowDraftListAllData,
    BcapMessage,
    BcapMessageWritable,
    ChecklistStep,
    ContributorSummary,
    ExternalDashboardCard,
    ExternalDashboardPage,
    InternalDashboardCard,
    PatchedRequirementAssignee,
    DraftPayloadWritable,
    DraftRecord,
    PatchedBcapMessagePatchWritable,
    PatchedPermitApplicationWritable,
    PermitApplication,
    PermitApplicationResourceAliasedData,
    PermitApplicationApplicationAdminTileWritable,
    PermitApplicationProcessModuleTileWritable,
    ProcessRequirement,
    ModuleUnread,
} from '@/bcap/client/types.gen.ts';
import {
    zApiDashboardExternalRetrieveQuery,
    zInternalDashboardPage,
    zProcessRequirement,
} from '@/bcap/client/zod.gen.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

export const fetchDraft = async (
    graphSlug: string,
    draftId: string,
): Promise<DraftRecord> => {
    return apiFetchJson<DraftRecord>(
        `${arches.urls.api_workflow_draft(graphSlug)}/${draftId}`,
    );
};

// parentResourceId links the draft to a parent so its page can filter its own
// drafts. The backend checks access before saving.
export const createDraft = async (
    graphSlug: string,
    parentResourceId?: string,
): Promise<DraftRecord> => {
    return apiFetchJson<DraftRecord>(
        arches.urls.api_workflow_draft(graphSlug),
        {
            method: HttpMethod.Post,
            body: {
                data: {},
                ...(parentResourceId
                    ? { parent_resource_id: parentResourceId }
                    : {}),
            },
        },
    );
};

export const fetchDrafts = async (
    parentResourceId?: string,
): Promise<WorkflowDraft[]> => {
    let url = arches.urls.api_workflow_draft_all;
    if (parentResourceId) {
        const query: ApiWorkflowDraftListAllData['query'] = {
            parent: parentResourceId,
        };
        url += `?${new URLSearchParams(query as Record<string, string>)}`;
    }
    try {
        return await apiFetchJson<WorkflowDraft[]>(url);
    } catch (error) {
        console.error('Failed to load drafts:', error);
        return [];
    }
};

export const deleteDraft = async (
    graphSlug: string,
    draftId: string,
): Promise<void> => {
    await apiFetch(`${arches.urls.api_workflow_draft(graphSlug)}/${draftId}`, {
        method: HttpMethod.Delete,
    });
};

export const saveDraftFieldToBackend = async (
    draftId: string,
    graphSlug: string,
    fullDraftData: ArchesDraftData,
    currentStep?: string,
): Promise<void> => {
    const payload: { data: ArchesDraftData; current_step?: string } = {
        data: JSON.parse(JSON.stringify(fullDraftData, dropFiles)),
    };
    if (currentStep) payload.current_step = currentStep;
    try {
        await apiFetch(
            `${arches.urls.api_workflow_draft(graphSlug)}/${draftId}`,
            { method: HttpMethod.Patch, body: payload },
        );
    } catch (error) {
        console.error('Failed to auto-save draft data:', error);
    }
};

type ExternalDashboardStatus = NonNullable<
    ApiDashboardExternalRetrieveData['query']
>['status'];

export const dashboardScope =
    zApiDashboardExternalRetrieveQuery.shape.status.unwrap().enum;

export const fetchMyProjects = async () =>
    fetchExternalDashboardCards(dashboardScope.FILINGS_CREATED_BY_ME);
export const fetchCompanyProjects = async () =>
    fetchExternalDashboardCards(
        dashboardScope.FILINGS_BY_ASSOCIATED_ORGANIZATIONS,
    );
export const fetchDraftCards = async () =>
    fetchExternalDashboardCards(dashboardScope.DRAFTS_CREATED_BY_ME);
export const fetchCompanyDraftCards = async () =>
    fetchExternalDashboardCards(
        dashboardScope.DRAFTS_BY_ASSOCIATED_ORGANIZATIONS,
    );

const fetchExternalDashboardCards = async (
    status: ExternalDashboardStatus,
): Promise<ExternalDashboardCard[]> => {
    try {
        const url = `${arches.urls.dashboard_external}?status=${status}`;

        const page = await apiFetchJson<ExternalDashboardPage>(url);
        return page.results || [];
    } catch (error) {
        console.error(`Failed to load ${status} dashboard cards:`, error);
        return [];
    }
};

export const getInternalDashboardData = async (
    status?: DashboardStatus,
    page: number = 1,
    limit: number = 100,
): Promise<InternalDashboardCard[]> => {
    try {
        // no status means all results -- omit the param entirely
        const statusParam = status ? `&status=${status}` : '';
        const apiUrl = `${arches.urls.dashboard}?limit=${limit}&page=${page}${statusParam}`;
        const result = zInternalDashboardPage.safeParse(
            await apiFetchJson(apiUrl),
        );
        if (!result.success) {
            console.warn(
                'InternalDashboardPage failed validation:',
                result.error,
            );
            return [];
        }
        return result.data.results ?? [];
    } catch (error) {
        console.error('Error fetching projects from backend:', error);
        return [];
    }
};

export const getProcessRequirementData = async (
    resource_id: string,
): Promise<ProcessRequirement> => {
    const json = await apiFetchJson<ProcessRequirement>(
        arches.urls.api_process_requirements(resource_id),
        {
            formatError: async (response) =>
                (await response.text()) || response.statusText,
        },
    );
    const result = zProcessRequirement.safeParse(json);
    if (!result.success) {
        console.warn('ProcessRequirement failed validation:', result.error);
    }
    return json;
};

export const submitApplication = async (
    draftId: string,
    payload: ArchesDraftData,
    graphSlug: string = GraphSlug.PermitApplication,
): Promise<PermitApplication> => {
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
        } as DraftNode;

        const finalResource = await apiFetchJson<PermitApplication>(submitUrl, {
            method: HttpMethod.Post,
            body: {
                draft_id: draftId,
                aliased_data: cleanPayload,
            },
        });

        const deleteUrl = `${arches.urls.api_workflow_draft(graphSlug)}/${draftId}`;
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
// a draftId to submit from a draft, which is deleted once the module lands.
// Files the user picked ride along as multipart, with the payload as the "json"
// part; without them the payload goes as plain JSON.
export const submitModule = async (
    permitId: string,
    draftId: string | undefined,
    moduleSlug: GraphSlug,
    payload: DraftPayloadWritable['data'],
    files: Array<[string, File]> = [],
): Promise<PermitApplication> => {
    try {
        const url = arches.urls.seed_process_requirements(permitId, moduleSlug);
        const json = { aliased_data: payload };
        let body: FormData | typeof json = json;
        if (files.length) {
            body = new FormData();
            // MultiPartJSONParser reads the body from the part named "json";
            // the Files in it go as their own parts, rebound by filename.
            body.append('json', JSON.stringify(json, dropFiles));
            for (const [key, file] of files) {
                body.append(key, file);
            }
        }
        const result = await apiFetchJson<PermitApplication>(url, {
            method: HttpMethod.Post,
            body,
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
): Promise<PermitApplicationResourceAliasedData | null> => {
    const url = arches.urls.api_resource(GraphSlug.PermitApplication, permitId);

    const rawJson = await apiFetchJson<PermitApplication>(url);

    if (!rawJson || !rawJson.aliased_data) {
        console.warn('API payload did not contain aliased_data');
        return null;
    }

    return rawJson.aliased_data;
};

export const fetchResourceData = async (
    graphSlug: string,
    resourceId: string,
): Promise<ArchesDraftData | null> => {
    const url = arches.urls.api_resource(graphSlug, resourceId);
    const rawJson = await apiFetchJson<{ aliased_data?: ArchesDraftData }>(url);
    return rawJson?.aliased_data ?? null;
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
    ): PermitApplicationProcessModuleTileWritable => {
        const aliasedData: NonNullable<
            PermitApplicationProcessModuleTileWritable['aliased_data']
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

    const applicationAdmin: PermitApplicationApplicationAdminTileWritable = {
        aliased_data: { process_module: modules.map(toModuleTile) },
    };
    if (adminTileId) {
        applicationAdmin.tileid = adminTileId;
    }

    const body: PatchedPermitApplicationWritable = {
        aliased_data: { application_admin: applicationAdmin },
    };

    await apiFetch(url, { method: HttpMethod.Patch, body });
};

// Mark a submitted module completed/incomplete. The dedicated route flips the
// completion flag and stamps or clears the completed date server-side, touching
// only those nodes so the module's order/name/id are left intact.
export const setModuleCompleted = async (
    permitId: string,
    moduleTileId: string,
    completed: boolean,
): Promise<void> => {
    await apiFetch(arches.urls.permit_module(permitId, moduleTileId), {
        method: HttpMethod.Patch,
        body: { completed },
    });
};

// Mark a non-checklist requirement satisfied/unsatisfied. The dedicated route
// sets the assessment tile server-side, so the client just sends the flag.
export const setRequirementSatisfied = async (
    requirementResourceId: string,
    satisfied: boolean,
): Promise<void> => {
    await apiFetch(arches.urls.requirement_status(requirementResourceId), {
        method: HttpMethod.Patch,
        body: { satisfied },
    });
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

export const setRequirementAssignee = async (
    permitId: string,
    moduleTileId: string,
    requirementId: string,
    contributorId: string | null,
): Promise<void> => {
    const body: PatchedRequirementAssignee = { contributor_id: contributorId };
    await apiFetch(
        arches.urls.module_requirement(permitId, moduleTileId, requirementId),
        { method: HttpMethod.Patch, body },
    );
};

export const fetchAssignableContributors = async (): Promise<
    ContributorSummary[]
> =>
    (await apiFetchJson<ApiContributorsAssignableListResponse>(
        arches.urls.assignable_contributors,
    )) ?? [];

// Patch a process requirement's aliased data (the checklist page's save).
export const patchProcessRequirement = async (
    requirementId: string,
    aliasedData: ProcessRequirement['aliased_data'],
): Promise<void> => {
    await apiFetch(arches.urls.api_process_requirements(requirementId), {
        method: HttpMethod.Patch,
        body: { aliased_data: aliasedData },
    });
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

export const createBcapMessage = async ({
    messageText,
    recipientId,
    resourceId,
    threadId,
    topic,
    messageType,
    files,
}: NewBcapMessage) => {
    // A reply carries no subject, type or recipient: the service copies the
    // thread's onto it. The nodes are required by the generated writable type,
    // so they travel as null rather than being left out.
    const aliasedData: NonNullable<BcapMessageWritable['aliased_data']> = {
        message_content: {
            aliased_data: {
                message_content: {
                    node_value: localized(messageText),
                },
                message_creation_date: { node_value: new Date().toISOString() },
                resource_context: {
                    node_value: [{ resourceId }],
                },
                message_subject: topic
                    ? { node_value: localized(topic) }
                    : null,
                message_type: messageType?.length
                    ? { node_value: messageType }
                    : null,
                recipient: recipientId
                    ? { node_value: [{ resourceId: recipientId }] }
                    : null,
            },
        },
    };

    if (threadId) {
        aliasedData.related_source_message = {
            aliased_data: {
                related_source_message: {
                    node_value: [{ resourceId: threadId }],
                },
            },
        };
    }

    if (files?.length) {
        aliasedData.message_content!.aliased_data!.attachments = {
            node_value: files.map((file) => ({
                name: file.name,
                url: null,
                size: file.size,
            })),
        };
        // Multipart: the payload rides as a "json" part; each file under the
        // "attachments" key, matched to its node_value by name. The create view
        // resolves the alias to the file-list node so no node id lives here.
        const form = new FormData();
        form.append('json', JSON.stringify({ aliased_data: aliasedData }));
        for (const file of files) {
            form.append('attachments', file);
        }
        return apiFetchJson<BcapMessage>(arches.urls.bcap_message_list_create, {
            method: HttpMethod.Post,
            body: form,
        });
    }

    return apiFetchJson<BcapMessage>(arches.urls.bcap_message_list_create, {
        method: HttpMethod.Post,
        body: { aliased_data: aliasedData },
    });
};

export const setThreadArchived = async (messageId: string, archived: boolean) =>
    apiFetch(arches.urls.bcap_message_detail(messageId), {
        method: HttpMethod.Patch,
        body: { archived },
    });

// One root per thread with an annotated unread_count; messages load on click.
export const getThreadsForResource = async (
    resourceId: string,
    archived = false,
): Promise<MessageThread[]> => {
    const { results = [] } = await apiFetchJson<{ results: BcapMessage[] }>(
        `${arches.urls.bcap_message_resource_threads(resourceId)}?archived=${archived}`,
    );

    // Newest-first from the backend; keep that order.
    return results.map((root) => {
        const content = root.aliased_data?.message_content?.aliased_data;
        const subject = content?.message_subject;
        // Older threads carry the type inside the subject text and have no
        // message_type of their own, so an absent type just drops the prefix.
        const subjectText =
            subject?.display_value || subject?.node_value?.en?.value || '';
        const typeLabel = content?.message_type?.display_value || '';
        const unreadCount =
            (root as { unread_count?: number }).unread_count ?? 0;
        return {
            id: root.resourceinstanceid ?? '',
            topic:
                [typeLabel, subjectText].filter(Boolean).join(' - ') ||
                'General Question',
            startedBy: content?.message_author?.display_value || 'Unknown',
            // The threads endpoint annotates the whole thread's latest date;
            // fall back to the root's own date if it is ever absent.
            lastMessageDate:
                (root as { last_message_date?: string }).last_message_date ||
                content?.message_creation_date?.node_value ||
                '',
            hasUnread: unreadCount > 0,
            unreadCount,
        };
    });
};

export const getSubmissionModulesUnreadCounts = async (
    submissionId: string,
): Promise<ModuleUnread[]> => {
    return apiFetchJson<ModuleUnread[]>(
        arches.urls.bcap_message_module_unread(submissionId),
    );
};

// One thread's messages, oldest-first; is_unread is per-viewer.
export const getMessagesForThread = async (
    threadId: string,
): Promise<FormattedMessage[]> => {
    const { results = [] } = await apiFetchJson<{ results: BcapMessage[] }>(
        arches.urls.bcap_message_thread_messages(threadId),
    );

    return results
        .map((message) => {
            const content = message.aliased_data?.message_content?.aliased_data;
            return {
                id: message.resourceinstanceid ?? '',
                author: content?.message_author?.display_value || 'Unknown',
                text:
                    content?.message_content?.node_value?.en?.value ||
                    content?.message_content?.display_value ||
                    '',
                // ISO timestamps, so string order is chronological order.
                date: content?.message_creation_date?.node_value ?? '',
                isUnread: Boolean(
                    (message as { is_unread?: boolean }).is_unread,
                ),
                attachments: (content?.attachments?.node_value ?? [])
                    .filter((file) => file.url)
                    .map((file) => ({
                        name: file.name ?? 'attachment',
                        url: file.url as string,
                        size: file.size,
                    })),
            };
        })
        .filter((message) => message.text)
        .sort((a, b) => a.date.localeCompare(b.date))
        .map((message) => ({
            ...message,
            date: formatTimestamp(message.date),
        }));
};

// The contributors you can address a message to for a resource: its
// login-linked contributors (ministry assignees included), from the backend.
export const getContributorsForResources = async (
    resourceId: string,
): Promise<Array<{ label: string; value: string }>> => {
    const data = await apiFetchJson<ContributorSummary[]>(
        arches.urls.bcap_message_resource_contributors(resourceId),
    );

    return (data ?? []).map((item) => ({
        label: item.name || 'Unknown Contributor',
        value: item.id,
    }));
};

export const markMessageAsRead = async (messageId: string): Promise<void> => {
    // The route reads only the read date; the null siblings are required by the
    // generated writable type.
    const body: PatchedBcapMessagePatchWritable = {
        aliased_data: {
            message_content: {
                aliased_data: {
                    message_content: null,
                    resource_context: null,
                    message_subject: null,
                    message_type: null,
                    recipient: null,
                    message_read_date: {
                        node_value: new Date().toISOString(),
                    },
                },
            },
        },
    };

    await apiFetch(arches.urls.bcap_message_detail(messageId), {
        method: HttpMethod.Patch,
        body,
    });
};
