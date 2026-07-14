import arches from 'arches';
import { apiFetch } from '@/bcap/api.ts';
import type {
    ArchesDraftData,
    DraftNode,
    InvestigationDraft,
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

// Submit a permit module: the route creates the module's host resource from the
// payload, clones the module's process requirements onto the permit, links the
// workflow requirement to the host, and returns the created host resource.
export const submitModule = async (
    permitId: string,
    draftId: string,
    moduleSlug: GraphSlug,
    payload: ArchesDraftData,
): Promise<PermitApplicationResponse> => {
    try {
        // parent_resource_id is draft-only bookkeeping, not a graph alias, so
        // drop it before the serializer validates the body against the graph.
        const aliasedData = { ...payload };
        delete aliasedData.parent_resource_id;
        const url = arches.urls.seed_process_requirements(permitId, moduleSlug);
        const response = await apiFetch(url, {
            method: 'POST',
            body: { aliased_data: aliasedData },
        });
        const result = await response.json();
        await deleteDraft(moduleSlug, draftId);
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

export const fetchPermitDetails = async (
    permitId: string,
): Promise<PermitAliasedData | null | undefined> => {
    const url = arches.urls.api_resource(GraphSlug.PermitApplication, permitId);

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
    const url = arches.urls.api_resource(GraphSlug.PermitApplication, permitId);

    await apiFetch(url, {
        method: 'PATCH',
        body: { aliased_data: { application_admin: adminPayload } },
    });
};

export const getCsrfToken = (): string => {
    let csrfToken = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === 'csrftoken=') {
                csrfToken = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return csrfToken || '';
};

interface BcapMessagePayload {
    aliased_data: {
        message_content: {
            aliased_data: {
                message_content: {
                    node_value: { en: { value: string; direction: string } };
                };
                message_subject: {
                    node_value: { en: { value: string; direction: string } };
                };
                message_creation_date: { node_value: string };
                resource_context: {
                    node_value: {
                        resourceId: string;
                        ontologyProperty: string;
                        resourceXresourceId: string;
                        inverseOntologyProperty: string;
                    };
                };
                recipient?: {
                    node_value: {
                        resourceId: string;
                        ontologyProperty: string;
                        resourceXresourceId: string;
                        inverseOntologyProperty: string;
                    };
                };
            };
        };
        related_source_message?: {
            aliased_data: {
                related_source_message: {
                    node_value: {
                        resourceId: string;
                        ontologyProperty: string;
                        resourceXresourceId: string;
                        inverseOntologyProperty: string;
                    };
                };
            };
        };
    };
}

export const createBcapMessage = async (
    messageText: string,
    recipientId: string,
    applicationId: string,
    permitResourceId: string,
    threadId?: string,
) => {
    const payload: BcapMessagePayload = {
        aliased_data: {
            message_content: {
                aliased_data: {
                    message_content: {
                        node_value: {
                            en: { value: messageText, direction: 'ltr' },
                        },
                    },
                    message_subject: {
                        node_value: {
                            en: {
                                value: `Comment regarding Application ${applicationId}`,
                                direction: 'ltr',
                            },
                        },
                    },
                    message_creation_date: {
                        node_value: new Date().toISOString(),
                    },
                    resource_context: {
                        node_value: {
                            resourceId: permitResourceId,
                            ontologyProperty: '',
                            resourceXresourceId: '',
                            inverseOntologyProperty: '',
                        },
                    },
                },
            },
        },
    };

    if (recipientId) {
        payload.aliased_data.message_content.aliased_data.recipient = {
            node_value: {
                resourceId: recipientId,
                ontologyProperty: '',
                resourceXresourceId: '',
                inverseOntologyProperty: '',
            },
        };
    }

    if (threadId) {
        payload.aliased_data.related_source_message = {
            aliased_data: {
                related_source_message: {
                    node_value: {
                        resourceId: threadId,
                        ontologyProperty: '',
                        resourceXresourceId: '',
                        inverseOntologyProperty: '',
                    },
                },
            },
        };
    }

    const response = await fetch(arches.urls.bcap_message_list_create, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFTOKEN': getCsrfToken(),
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Arches API Error:', errorData);
        throw new Error(`Failed to post message: ${response.statusText}`);
    }

    return await response.json();
};

export interface FormattedMessage {
    author: string;
    text: string;
    date: string;
}

interface RawThreadMessage {
    aliased_data?: {
        message_content?: {
            aliased_data?: {
                message_author?: { display_value?: string };
                message_content?: {
                    display_value?: string;
                    node_value?: { en?: { value?: string } };
                };
                message_creation_date?: { node_value?: string };
            };
        };
        message_response?: {
            aliased_data?: {
                response_author?: { display_value?: string };
                message_response?: {
                    display_value?: string;
                    node_value?: { en?: { value?: string } };
                };
                response_issued_date?: { node_value?: string };
            };
        };
    };
}

export const getMessagesForPermit = async (
    permitId: string,
): Promise<{ messages: FormattedMessage[]; threadId: string | null }> => {
    // Fetch threads
    const threadsResponse = await fetch(
        arches.urls.bcap_message_resource_threads(permitId),
        { headers: { accept: 'application/json' } },
    );

    if (!threadsResponse.ok) throw new Error('Failed to fetch threads');
    const threadsData = await threadsResponse.json();
    const threads = threadsData.results || threadsData || [];

    if (!threads || threads.length === 0) {
        return { messages: [], threadId: null };
    }

    const firstThread = threads[0];
    const threadId =
        typeof firstThread === 'string'
            ? firstThread
            : firstThread?.resourceinstanceid ||
              firstThread?.id ||
              firstThread?.thread_id;

    if (!threadId) {
        return { messages: [], threadId: null };
    }

    // Fetch messages
    const msgsResponse = await fetch(
        arches.urls.bcap_message_thread_messages(threadId),
        { headers: { accept: 'application/json' } },
    );

    if (!msgsResponse.ok) throw new Error('Failed to fetch messages');
    const msgsData = await msgsResponse.json();
    const rawMessages = msgsData.results || msgsData || [];

    const allMessages: Array<{ author: string; text: string; date: number }> =
        [];

    rawMessages.forEach((msg: RawThreadMessage) => {
        const coreData = msg.aliased_data?.message_content?.aliased_data;
        if (coreData) {
            const text =
                coreData.message_content?.node_value?.en?.value ||
                coreData.message_content?.display_value;
            if (text) {
                allMessages.push({
                    author: coreData.message_author?.display_value || 'Unknown',
                    text: text,
                    date: new Date(
                        coreData.message_creation_date?.node_value || 0,
                    ).getTime(),
                });
            }
        }

        // Grab the Reply (if it exists)
        const responseData = msg.aliased_data?.message_response?.aliased_data;
        if (responseData) {
            const respText =
                responseData.message_response?.node_value?.en?.value ||
                responseData.message_response?.display_value;
            if (respText) {
                allMessages.push({
                    author:
                        responseData.response_author?.display_value ||
                        'Unknown',
                    text: respText,
                    date: new Date(
                        responseData.response_issued_date?.node_value || 0,
                    ).getTime(),
                });
            }
        }
    });

    allMessages.sort((a, b) => a.date - b.date);

    // Format dates for the UI
    const formattedMessages = allMessages.map((m) => ({
        author: m.author,
        text: m.text,
        date: new Date(m.date).toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        }),
    }));

    return { messages: formattedMessages, threadId };
};
