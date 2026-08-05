import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    dashboardScope,
    fetchDraft,
    createDraft,
    fetchDrafts,
    fetchCompanyProjects,
    fetchDraftCards,
    fetchMyProjects,
    fetchAssignableContributors,
    patchProcessRequirement,
    setRequirementAssignee,
    submitApplication,
    submitModule,
    deleteDraft,
    getThreadsForResource,
    getMessagesForThread,
    setThreadArchived,
    markMessageAsRead,
} from './api';
import { GraphSlug } from './graphSlug.ts';

vi.mock('arches', () => ({
    default: {
        urls: {
            api_resource_blank: (graphSlug: string) =>
                `/mock/blank/${graphSlug}`,
            api_workflow_draft: (graphSlug: string) =>
                `/mock/draft/${graphSlug}`,
            api_workflow_draft_all: '/mock/drafts',
            permit_application_create: '/mock/create/permit_application',
            seed_process_requirements: (permitId: string, slug: string) =>
                `/mock/seed/${permitId}/${slug}`,
            dashboard_external: '/bcap/api/dashboard/external',
            api_resource: (graph: string, pk: string) =>
                `/bcap/api/resource/${graph}/${pk}`,
            bcap_message_resource_threads: (resourceId: string) =>
                `/mock/threads/${resourceId}`,
            bcap_message_thread_messages: (threadId: string) =>
                `/mock/thread/${threadId}`,
            bcap_message_detail: (messageId: string) =>
                `/mock/message/${messageId}`,
            module_requirement: (
                permitId: string,
                moduleTileId: string,
                requirementId: string,
            ) =>
                `/mock/${permitId}/module/${moduleTileId}/req/${requirementId}`,
            assignable_contributors: '/mock/contributors/assignable',
            api_process_requirements: (requirementId: string) =>
                `/mock/process_requirement/${requirementId}`,
        },
    },
}));

// apiFetch returns a Response-like object (callers read
// .json() themselves); apiFetchJson returns the parsed body directly. HttpMethod
// mirrors the real string enum so method assertions stay readable.
const { apiFetch, apiFetchJson } = vi.hoisted(() => ({
    apiFetch: vi.fn(),
    apiFetchJson: vi.fn(),
}));
vi.mock('@/bcap/api.ts', () => ({
    apiFetch,
    apiFetchJson,
    HttpMethod: {
        Get: 'GET',
        Post: 'POST',
        Patch: 'PATCH',
        Put: 'PUT',
        Delete: 'DELETE',
    },
}));

// Resolve apiFetch to a Response-like object whose json() yields body
function okResponse(body: unknown) {
    return { json: vi.fn().mockResolvedValue(body) };
}

describe('Permit API', () => {
    beforeEach(() => {
        apiFetch.mockReset();
        apiFetchJson.mockReset();
        // Hide expected console.errors from cluttering test output
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('fetchDrafts', () => {
        it('fetches every graph in one call', async () => {
            const drafts = [
                { id: 'permit-1', graph_slug: GraphSlug.PermitApplication },
                { id: 'investigation-1', graph_slug: GraphSlug.Investigation },
            ];
            apiFetchJson.mockResolvedValue(drafts);

            const result = await fetchDrafts();

            expect(apiFetchJson).toHaveBeenCalledWith('/mock/drafts');
            expect(result).toEqual(drafts);
        });

        it('narrows to one permit when given a parent', async () => {
            apiFetchJson.mockResolvedValue([]);

            await fetchDrafts('permit-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/drafts?parent=permit-1',
            );
        });

        it('returns nothing when the request fails', async () => {
            apiFetchJson.mockRejectedValue(new Error('Server Error'));

            const result = await fetchDrafts();

            expect(result).toEqual([]);
            expect(console.error).toHaveBeenCalled();
        });
    });

    describe('fetchDraft', () => {
        it('GETs the draft by graph and id', async () => {
            const draft = { id: 'draft-1', data: {} };
            apiFetchJson.mockResolvedValue(draft);

            const result = await fetchDraft('investigation', 'draft-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/draft/investigation/draft-1',
            );
            expect(result).toEqual(draft);
        });
    });

    describe('createDraft', () => {
        it('POSTs an empty draft for the graph', async () => {
            const draft = { id: 'draft-new', data: {} };
            apiFetchJson.mockResolvedValue(draft);

            const result = await createDraft('investigation');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/draft/investigation',
                {
                    method: 'POST',
                    body: { data: {} },
                },
            );
            expect(result).toEqual(draft);
        });

        it('sends the parent resource id alongside the blob when given', async () => {
            apiFetchJson.mockResolvedValue({ id: 'draft-new', data: {} });

            await createDraft('investigation', 'permit-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/draft/investigation',
                {
                    method: 'POST',
                    body: { data: {}, parent_resource_id: 'permit-1' },
                },
            );
        });
    });

    describe('fetchCompanyProjects', () => {
        it('asks for the associated-companies scope', async () => {
            apiFetchJson.mockResolvedValue({ results: [{ id: 'theirs' }] });

            const result = await fetchCompanyProjects();

            expect(apiFetchJson).toHaveBeenCalledWith(
                `/bcap/api/dashboard/external?status=${dashboardScope.FILINGS_BY_ASSOCIATED_ORGANIZATIONS}`,
            );
            expect(result).toEqual([{ id: 'theirs' }]);
        });
    });

    describe('fetchDraftCards', () => {
        it('asks the external dashboard for the drafts scope', async () => {
            apiFetchJson.mockResolvedValue({
                results: [{ id: 'draft-1', is_draft: true }],
            });

            const result = await fetchDraftCards();

            expect(apiFetchJson).toHaveBeenCalledWith(
                `/bcap/api/dashboard/external?status=${dashboardScope.DRAFTS_CREATED_BY_ME}`,
            );
            expect(result).toEqual([{ id: 'draft-1', is_draft: true }]);
        });
    });

    describe('setRequirementAssignee', () => {
        it('PATCHes the contributor onto the module requirement', async () => {
            apiFetch.mockResolvedValue(okResponse(null));

            await setRequirementAssignee(
                'permit-1',
                'module-tile-1',
                'req-1',
                'contributor-1',
            );

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/permit-1/module/module-tile-1/req/req-1',
                { method: 'PATCH', body: { contributor_id: 'contributor-1' } },
            );

            // A null contributor is how the assignment is cleared.
            await setRequirementAssignee(
                'permit-1',
                'module-tile-1',
                'req-1',
                null,
            );

            expect(apiFetch).toHaveBeenLastCalledWith(
                '/mock/permit-1/module/module-tile-1/req/req-1',
                { method: 'PATCH', body: { contributor_id: null } },
            );
        });
    });

    describe('fetchAssignableContributors', () => {
        it('returns the assignable list, or an empty one', async () => {
            const contributors = [{ id: 'c-1', name: 'Hopper, Grace' }];
            apiFetchJson.mockResolvedValue(contributors);

            expect(await fetchAssignableContributors()).toEqual(contributors);
            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/contributors/assignable',
            );

            apiFetchJson.mockResolvedValue(null);
            expect(await fetchAssignableContributors()).toEqual([]);
        });
    });

    describe('patchProcessRequirement', () => {
        it('PATCHes the aliased data under an aliased_data envelope', async () => {
            apiFetch.mockResolvedValue(okResponse(null));
            const aliasedData = { requirement_data: {} };

            await patchProcessRequirement('req-1', aliasedData as never);

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/process_requirement/req-1',
                { method: 'PATCH', body: { aliased_data: aliasedData } },
            );
        });
    });

    describe('fetchMyProjects', () => {
        it('returns the page results', async () => {
            apiFetchJson.mockResolvedValue({ results: [{ id: 'proj-1' }] });
            const result = await fetchMyProjects();
            expect(apiFetchJson).toHaveBeenCalledWith(
                `/bcap/api/dashboard/external?status=${dashboardScope.FILINGS_CREATED_BY_ME}`,
            );
            expect(result).toEqual([{ id: 'proj-1' }]);
        });

        it('returns empty array when the page carries no results', async () => {
            apiFetchJson.mockResolvedValue({ count: 0 });
            expect(await fetchMyProjects()).toEqual([]);
        });

        it('returns empty array on error', async () => {
            apiFetchJson.mockRejectedValue(new Error('Forbidden'));
            const result = await fetchMyProjects();
            expect(result).toEqual([]);
        });
    });

    describe('deleteDraft', () => {
        it('DELETEs the draft for its graph', async () => {
            apiFetch.mockResolvedValue(okResponse(undefined));

            await deleteDraft('investigation', 'draft-9');

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/draft/investigation/draft-9',
                { method: 'DELETE' },
            );
        });
    });

    describe('submitModule', () => {
        it('POSTs the module host then DELETEs its draft', async () => {
            const finalResource = { resourceinstanceid: 'inv-1' };
            apiFetchJson.mockResolvedValue(finalResource);
            apiFetch.mockResolvedValue(okResponse(undefined));

            const result = await submitModule(
                'permit-1',
                'draft-7',
                GraphSlug.Investigation,
                { a: 1 } as never,
            );

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/seed/permit-1/investigation',
                {
                    method: 'POST',
                    body: { aliased_data: { a: 1 } },
                },
            );
            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/draft/investigation/draft-7',
                { method: 'DELETE' },
            );
            expect(result).toEqual(finalResource);
        });

        it('skips the draft delete for a staff quick-add (no draft id)', async () => {
            apiFetchJson.mockResolvedValue({ resourceinstanceid: 'inv-1' });

            await submitModule('permit-1', undefined, GraphSlug.Investigation, {
                a: 1,
            } as never);

            expect(apiFetchJson).toHaveBeenCalledOnce();
            expect(apiFetch).not.toHaveBeenCalled();
        });

        it('re-throws and logs when the POST fails', async () => {
            const failure = new Error('POST investigation failed');
            apiFetchJson.mockRejectedValue(failure);

            await expect(
                submitModule(
                    'permit-1',
                    'draft-7',
                    GraphSlug.Investigation,
                    {} as never,
                ),
            ).rejects.toThrow('POST investigation failed');
            expect(console.error).toHaveBeenCalledWith(
                'Module submission API failed:',
                failure,
            );
        });
    });

    describe('submitApplication', () => {
        it('POSTs the final resource and DELETEs the draft on success', async () => {
            const finalResource = { resourceinstanceid: 'final-123' };
            const payload = { test: 'data' };

            apiFetchJson.mockResolvedValue(finalResource);
            apiFetch.mockResolvedValue(okResponse(undefined));

            const result = await submitApplication('draft-123', payload);

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/create/permit_application',
                {
                    method: 'POST',
                    body: {
                        draft_id: 'draft-123',
                        aliased_data: {
                            test: 'data',
                            application_identification: {
                                aliased_data: {
                                    application_id: {
                                        node_value: {
                                            en: {
                                                value: 'DUMMY-APP-0000',
                                                direction: 'ltr',
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            );

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/draft/permit_application/draft-123',
                { method: 'DELETE' },
            );

            expect(result).toEqual(finalResource);
        });

        it('re-throws and logs when a request fails', async () => {
            const failure = new Error('POST .../create failed (400)');
            apiFetchJson.mockRejectedValue(failure);

            await expect(submitApplication('draft-123', {})).rejects.toThrow(
                'POST .../create failed (400)',
            );
            expect(console.error).toHaveBeenCalledWith(
                'Submission API failed:',
                failure,
            );
        });
    });

    describe('getThreadsForResource', () => {
        const root = (id: string, subject: string, unread: number) => ({
            resourceinstanceid: id,
            unread_count: unread,
            aliased_data: {
                message_content: {
                    aliased_data: {
                        message_subject: { display_value: subject },
                        message_author: { display_value: 'Jane Doe' },
                    },
                },
            },
        });

        it('builds thread stubs from roots without fetching messages', async () => {
            apiFetchJson.mockResolvedValue({
                results: [root('t1', 'A question', 2)],
            });

            const threads = await getThreadsForResource('res-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/threads/res-1?archived=false',
            );
            expect(threads).toEqual([
                {
                    id: 't1',
                    topic: 'A question',
                    startedBy: 'Jane Doe',
                    lastMessageDate: '',
                    hasUnread: true,
                    unreadCount: 2,
                },
            ]);
        });

        it('requests the archived list when asked', async () => {
            apiFetchJson.mockResolvedValue({ results: [] });

            await getThreadsForResource('res-1', true);

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/threads/res-1?archived=true',
            );
        });

        it('defaults a missing unread_count to zero and not-unread', async () => {
            apiFetchJson.mockResolvedValue({
                results: [
                    {
                        resourceinstanceid: 't2',
                        aliased_data: { message_content: { aliased_data: {} } },
                    },
                ],
            });

            const [thread] = await getThreadsForResource('res-1');

            expect(thread.unreadCount).toBe(0);
            expect(thread.hasUnread).toBe(false);
            expect(thread.topic).toBe('General Question');
        });
    });

    describe('getMessagesForThread', () => {
        const message = (
            id: string,
            author: string,
            text: string,
            date: string,
            unread = false,
        ) => ({
            resourceinstanceid: id,
            is_unread: unread,
            aliased_data: {
                message_content: {
                    aliased_data: {
                        message_author: { display_value: author },
                        message_content: {
                            node_value: { en: { value: text } },
                        },
                        message_creation_date: { node_value: date },
                    },
                },
            },
        });

        it('returns messages oldest-first and drops empty ones', async () => {
            apiFetchJson.mockResolvedValue({
                results: [
                    message('m2', 'Sam', 'Later', '2026-01-02T00:00:00Z', true),
                    message('m1', 'Amy', 'Earlier', '2026-01-01T00:00:00Z'),
                    message('m3', 'Amy', '', '2026-01-03T00:00:00Z'),
                ],
            });

            const messages = await getMessagesForThread('t1');

            expect(apiFetchJson).toHaveBeenCalledWith('/mock/thread/t1');
            expect(messages.map((m) => m.id)).toEqual(['m1', 'm2']);
            expect(messages[0]).toMatchObject({
                author: 'Amy',
                text: 'Earlier',
                isUnread: false,
            });
            expect(messages[1]).toMatchObject({
                author: 'Sam',
                text: 'Later',
                isUnread: true,
            });
        });
    });

    describe('setThreadArchived', () => {
        it('PATCHes the message with the archived flag', async () => {
            apiFetch.mockResolvedValue(okResponse({}));

            await setThreadArchived('m1', true);

            expect(apiFetch).toHaveBeenCalledWith('/mock/message/m1', {
                method: 'PATCH',
                body: { archived: true },
            });
        });
    });

    describe('markMessageAsRead', () => {
        it('PATCHes the message with a read date', async () => {
            apiFetch.mockResolvedValue(okResponse({}));

            await markMessageAsRead('m1');

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/message/m1',
                expect.objectContaining({ method: 'PATCH' }),
            );
            const body = apiFetch.mock.calls[0][1].body;
            expect(
                body.aliased_data.message_content.aliased_data.message_read_date
                    .node_value,
            ).toEqual(expect.any(String));
        });
    });
});
