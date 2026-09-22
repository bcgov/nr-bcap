import {
    dashboardScope,
    fetchDraft,
    createDraft,
    fetchDrafts,
    fetchCompanyProjects,
    fetchDraftCards,
    fetchMyProjects,
    fetchAssignableContributors,
    fetchRequirementDetails,
    getContributorsForResources,
    patchProcessRequirement,
    setRequirementAssignee,
    submitApplication,
    submitModule,
    deleteDraft,
    getThreadsForResource,
    getMessagesForThread,
    setThreadArchived,
    setThreadResolved,
    getSubmissionModulesUnresolvedCounts,
} from './api';
import { GraphSlug } from './graphSlug.ts';
import { ThreadSide } from '@/bcap/types.ts';

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

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/workflow_draft',
            );
            expect(result).toEqual(drafts);
        });

        it('narrows to one permit when given a parent', async () => {
            apiFetchJson.mockResolvedValue([]);

            await fetchDrafts('permit-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/workflow_draft?parent=permit-1',
            );
        });

        it('throws when the request fails, for the page to report inline', async () => {
            apiFetchJson.mockRejectedValue(new Error('Server Error'));

            await expect(fetchDrafts()).rejects.toThrow('Server Error');
        });
    });

    describe('fetchDraft', () => {
        it('GETs the draft by graph and id', async () => {
            const draft = { id: 'draft-1', data: {} };
            apiFetchJson.mockResolvedValue(draft);

            const result = await fetchDraft('investigation', 'draft-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/workflow_draft/investigation/draft-1',
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
                '/bcap/api/workflow_draft/investigation',
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
                '/bcap/api/workflow_draft/investigation',
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
                '/bcap/api/permit_application/permit-1/module/module-tile-1/requirement/req-1',
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
                '/bcap/api/permit_application/permit-1/module/module-tile-1/requirement/req-1',
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
                '/bcap/api/contributors/assignable',
            );

            apiFetchJson.mockResolvedValue(null);
            expect(await fetchAssignableContributors()).toEqual([]);
        });
    });

    describe('getContributorsForResources', () => {
        it('labels the proponent so staff can tell them apart', async () => {
            apiFetchJson.mockResolvedValue([
                { id: 'c-1', name: 'Applicant, Amy', is_proponent: true },
                { id: 'c-2', name: 'Staff, Sam', is_proponent: false },
            ]);

            expect(await getContributorsForResources('permit-1')).toEqual([
                { label: 'Applicant, Amy (Proponent)', value: 'c-1' },
                { label: 'Staff, Sam', value: 'c-2' },
            ]);
        });
    });

    describe('patchProcessRequirement', () => {
        it('PATCHes the aliased data under an aliased_data envelope', async () => {
            apiFetch.mockResolvedValue(okResponse(null));
            const aliasedData = { requirement_data: {} };

            await patchProcessRequirement('req-1', aliasedData as never);

            expect(apiFetch).toHaveBeenCalledWith(
                '/bcap/api/process_requirement/req-1',
                { method: 'PATCH', body: { aliased_data: aliasedData } },
            );
        });
    });

    describe('fetchRequirementDetails', () => {
        it('reads each requirement from the graph route, not the generic one', async () => {
            // The generic resource route answers to the graph policy, which has
            // nothing for an applicant; this one lets their permit decide.
            apiFetchJson.mockResolvedValue({ resourceinstanceid: 'req-1' });

            const result = await fetchRequirementDetails(['req-1']);

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/process_requirement/req-1',
            );
            expect(result).toEqual({
                'req-1': { resourceinstanceid: 'req-1' },
            });
        });

        it('throws when a requirement fails to load, for the page to report inline', async () => {
            apiFetchJson.mockRejectedValue(new Error('403'));

            await expect(fetchRequirementDetails(['req-1'])).rejects.toThrow(
                '403',
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

        it('throws on error, for the page to report inline', async () => {
            apiFetchJson.mockRejectedValue(new Error('Forbidden'));
            await expect(fetchMyProjects()).rejects.toThrow('Forbidden');
        });
    });

    describe('deleteDraft', () => {
        it('DELETEs the draft for its graph', async () => {
            apiFetch.mockResolvedValue(okResponse(undefined));

            await deleteDraft('investigation', 'draft-9');

            expect(apiFetch).toHaveBeenCalledWith(
                '/bcap/api/workflow_draft/investigation/draft-9',
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
                '/bcap/api/permit_application/permit-1/process_requirement/investigation',
                {
                    method: 'POST',
                    body: { aliased_data: { a: 1 } },
                },
            );
            expect(apiFetch).toHaveBeenCalledWith(
                '/bcap/api/workflow_draft/investigation/draft-7',
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

        it('re-throws when the POST fails, for the page to report inline', async () => {
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
            // The draft is only deleted once the module has landed.
            expect(apiFetch).not.toHaveBeenCalled();
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
                '/bcap/api/permit_application',
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
                '/bcap/api/workflow_draft/permit_application/draft-123',
                { method: 'DELETE' },
            );

            expect(result).toEqual(finalResource);
        });

        it('re-throws when a request fails, for the page to report inline', async () => {
            apiFetchJson.mockRejectedValue(
                new Error('POST .../create failed (400)'),
            );

            await expect(submitApplication('draft-123', {})).rejects.toThrow(
                'POST .../create failed (400)',
            );
            // The draft survives a failed submission.
            expect(apiFetch).not.toHaveBeenCalled();
        });
    });

    describe('getThreadsForResource', () => {
        const root = (
            id: string,
            subject: string,
            extra: Record<string, unknown> = {},
        ) => ({
            resourceinstanceid: id,
            aliased_data: {
                message_content: {
                    aliased_data: {
                        message_subject: { display_value: subject },
                        message_author: { display_value: 'Jane Doe' },
                        ...extra,
                    },
                },
            },
        });

        it('builds thread stubs from roots without fetching messages', async () => {
            apiFetchJson.mockResolvedValue({
                results: [root('t1', 'A question')],
            });

            const threads = await getThreadsForResource('res-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/bcap_message/resource/res-1/threads?archived=false',
            );
            expect(threads).toEqual([
                {
                    id: 't1',
                    topic: 'A question',
                    startedBy: 'Jane Doe',
                    lastMessageDate: '',
                    isResolved: false,
                    onSide: false,
                    resolvedBy: '',
                    resolvedDate: '',
                    isInternal: false,
                },
            ]);
        });

        // The author side resolved, the recipient side has not: each viewer
        // sees their own side's.
        const resolvedByAuthor = (viewerSide: string) => ({
            ...root('t1', 'Closed', {
                author_resolved_date: {
                    node_value: '2026-02-01 12:00:00+00:00',
                },
                author_resolved_by: { display_value: 'Sam Staff' },
                is_internal: { node_value: true },
            }),
            viewer_side: viewerSide,
        });

        it('shows the recipient their own side, still open', async () => {
            apiFetchJson.mockResolvedValue({
                results: [resolvedByAuthor(ThreadSide.Recipient)],
            });

            const [thread] = await getThreadsForResource('res-1');

            expect(thread).toMatchObject({
                onSide: true,
                isResolved: false,
                resolvedBy: '',
            });
        });

        it('leaves a viewer on neither side nothing to resolve', async () => {
            apiFetchJson.mockResolvedValue({
                results: [resolvedByAuthor('')],
            });

            const [thread] = await getThreadsForResource('res-1');

            expect(thread).toMatchObject({ onSide: false, isResolved: false });
        });

        it("reads the viewer's side's resolution and the internal flag", async () => {
            apiFetchJson.mockResolvedValue({
                results: [resolvedByAuthor(ThreadSide.Author)],
            });

            const [thread] = await getThreadsForResource('res-1');

            expect(thread).toMatchObject({
                isResolved: true,
                resolvedBy: 'Sam Staff',
                resolvedDate: '2026-02-01 12:00:00+00:00',
                isInternal: true,
            });
        });

        it('requests the archived list when asked', async () => {
            apiFetchJson.mockResolvedValue({ results: [] });

            await getThreadsForResource('res-1', true);

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/bcap_message/resource/res-1/threads?archived=true',
            );
        });

        it('treats a root without those nodes as open and shared', async () => {
            apiFetchJson.mockResolvedValue({
                results: [
                    {
                        resourceinstanceid: 't2',
                        aliased_data: { message_content: { aliased_data: {} } },
                    },
                ],
            });

            const [thread] = await getThreadsForResource('res-1');

            expect(thread.isResolved).toBe(false);
            expect(thread.isInternal).toBe(false);
            expect(thread.topic).toBe('General Question');
        });
    });

    describe('getSubmissionModulesUnresolvedCounts', () => {
        it('reads the per-module unresolved counts', async () => {
            const rows = [{ module_id: 'mod-a', unresolved_count: 2 }];
            apiFetchJson.mockResolvedValue(rows);

            await expect(
                getSubmissionModulesUnresolvedCounts('sub-1'),
            ).resolves.toEqual(rows);
            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/bcap_message/submission/sub-1/unresolved-by-module',
            );
        });
    });

    describe('getMessagesForThread', () => {
        const message = (
            id: string,
            author: string,
            text: string,
            date: string,
        ) => ({
            resourceinstanceid: id,
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
                    message('m2', 'Sam', 'Later', '2026-01-02T00:00:00Z'),
                    message('m1', 'Amy', 'Earlier', '2026-01-01T00:00:00Z'),
                    message('m3', 'Amy', '', '2026-01-03T00:00:00Z'),
                ],
            });

            const messages = await getMessagesForThread('t1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/bcap/api/bcap_message/thread/t1',
            );
            expect(messages.map((m) => m.id)).toEqual(['m1', 'm2']);
            expect(messages[0]).toMatchObject({
                author: 'Amy',
                text: 'Earlier',
            });
            expect(messages[1]).toMatchObject({ author: 'Sam', text: 'Later' });
        });
    });

    describe('setThreadArchived', () => {
        it('PATCHes the message with the archived flag', async () => {
            apiFetch.mockResolvedValue(okResponse({}));

            await setThreadArchived('m1', true);

            expect(apiFetch).toHaveBeenCalledWith('/bcap/api/bcap_message/m1', {
                method: 'PATCH',
                body: { archived: true },
            });
        });
    });

    describe('setThreadResolved', () => {
        it('PATCHes the message with the resolved flag', async () => {
            apiFetch.mockResolvedValue(okResponse({}));

            await setThreadResolved('m1', false);

            expect(apiFetch).toHaveBeenCalledWith('/bcap/api/bcap_message/m1', {
                method: 'PATCH',
                body: { resolved: false },
            });
        });
    });
});
