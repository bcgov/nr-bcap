import arches from 'arches';
import { apiFetch, apiFetchJson, HttpMethod } from '@/bcap/api.ts';
import { localized, formatTimestamp } from '@/bcap/util.ts';
import type {
    MessageThread,
    ArchesDraftData,
    DraftNode,
    FormattedMessage,
    InvestigationDraft,
    NewBcapMessage,
    PermitAliasedData,
} from '@/bcap/types.ts';
import type {
    BcapMessage,
    BcapMessageWritable,
    ChecklistStep,
    DraftRecord,
    PatchedBcapMessagePatchWritable,
    PatchedPermitApplicationWritable,
    PermitApplication,
    PermitApplicationApplicationAdminTileWritable,
    PermitApplicationProcessModuleTileWritable,
    ProcessRequirement,
    ModuleUnread,
} from '@/bcap/client/types.gen.ts';
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
                    arches.urls.api_workflow_draft(graphSlug),
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
    await apiFetch(`${arches.urls.api_workflow_draft(graphSlug)}/${draftId}`, {
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
        } as unknown as DraftNode;

        const finalResource = await apiFetchJson<PermitApplication>(submitUrl, {
            method: HttpMethod.Post,
            body: {
                draft_id: draftId,
                aliased_data: cleanPayload,
            },
        });

        // Delete the draft after successful submission
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
// a draftId to submit from a draft (deleted after); omit it for a staff
// quick-add that sends a placeholder payload directly.
export const submitModule = async (
    permitId: string,
    draftId: string | undefined,
    moduleSlug: GraphSlug,
    payload: ArchesDraftData,
): Promise<PermitApplication> => {
    try {
        const url = arches.urls.seed_process_requirements(permitId, moduleSlug);
        const result = await apiFetchJson<PermitApplication>(url, {
            method: HttpMethod.Post,
            body: { aliased_data: payload },
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

    const rawJson = await apiFetchJson<PermitApplication>(url);

    if (!rawJson || !rawJson.aliased_data) {
        console.warn('API payload did not contain aliased_data');
        return null;
    }

    return rawJson.aliased_data as PermitAliasedData;
};

export const fetchResourceData = async (
    graphSlug: string,
    resourceId: string,
): Promise<ArchesDraftData | null> => {
    const url = arches.urls.api_resource(graphSlug, resourceId);
    const rawJson = await apiFetchJson<PermitApplication>(url);
    return (rawJson?.aliased_data as unknown as ArchesDraftData) ?? null;
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
    applicationId,
    resourceId,
    threadId,
    topic,
    files,
}: NewBcapMessage) => {
    const aliasedData: NonNullable<BcapMessageWritable['aliased_data']> = {
        message_content: {
            aliased_data: {
                message_content: {
                    node_value: localized(messageText),
                },
                message_subject: {
                    node_value: localized(
                        topic ||
                            `Comment regarding Application ${applicationId}`,
                    ),
                },
                message_creation_date: { node_value: new Date().toISOString() },
                resource_context: {
                    node_value: [{ resourceId }],
                },
            },
        },
    };

    if (recipientId) {
        aliasedData.message_content!.aliased_data!.recipient = {
            node_value: [{ resourceId: recipientId }],
        };
    }

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
        const response = await apiFetch(arches.urls.bcap_message_list_create, {
            method: HttpMethod.Post,
            body: form,
        });
        return response.json() as Promise<BcapMessage>;
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
        const unreadCount =
            (root as { unread_count?: number }).unread_count ?? 0;
        return {
            id: root.resourceinstanceid ?? '',
            topic:
                subject?.display_value ||
                subject?.node_value?.en?.value ||
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
    const data = await apiFetchJson<
        Array<{ id: string; name?: string; email?: string; type?: string }>
    >(arches.urls.bcap_message_resource_contributors(resourceId));

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
