import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    fetchDraft,
    createDraft,
    fetchDrafts,
    fetchMyProjects,
    submitApplication,
    submitModule,
    fetchPermitModules,
    deleteDraft,
    createBcapMessage,
    getMessagesForPermit,
    getContributors,
} from './api';
import { GraphSlug } from './graphSlug.ts';

// 1. Mock the Arches URL generator
vi.mock('arches', () => ({
    default: {
        urls: {
            api_resource_blank: (graphSlug: string) =>
                `/mock/blank/${graphSlug}`,
            api_resource_draft: (graphSlug: string) =>
                `/mock/draft/${graphSlug}`,
            permit_application_create: '/mock/create/permit_application',
            seed_process_requirements: (permitId: string, slug: string) =>
                `/mock/seed/${permitId}/${slug}`,
            dashboard_external: '/bcap/api/dashboard/external',
            api_resource: (graph: string, pk: string) =>
                `/bcap/api/resource/${graph}/${pk}`,

            // New URLs for Messaging & Contributors
            api_contributor: '/mock/api/contributor',
            bcap_message_list_create: '/mock/messages/create',
            bcap_message_resource_threads: (id: string) =>
                `/mock/messages/threads/${id}`,
            bcap_message_thread_messages: (id: string) =>
                `/mock/messages/thread/${id}/messages`,
        },
    },
}));

// 2. Mock the apiFetch wrapper (its own behavior is covered in api.test.ts)
const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }));
vi.mock('@/bcap/api.ts', () => ({ apiFetch }));

// Mock the CSRF Token utility
vi.mock('@/bcap/util.ts', () => ({
    getCsrfToken: vi.fn(() => 'mock-csrf-token'),
}));

// Resolve apiFetch to a Response-like object whose json() yields body
function okResponse(body: unknown) {
    return { json: vi.fn().mockResolvedValue(body) };
}

describe('Permit API', () => {
    // Save original global fetch to restore later
    const originalFetch = global.fetch;

    beforeEach(() => {
        apiFetch.mockReset();
        // Mock global fetch for the new messaging functions
        global.fetch = vi.fn();
        // Hide expected console.errors from cluttering test output
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
        global.fetch = originalFetch;
    });

    // ... [Existing Draft / Submission Tests remain unchanged] ...

    describe('fetchDrafts', () => {
        it('fetches and merges drafts across every draft graph', async () => {
            apiFetch
                .mockResolvedValueOnce(
                    okResponse({ results: [{ id: 'permit-1' }] }),
                )
                .mockResolvedValueOnce(okResponse([{ id: 'investigation-1' }]));

            const result = await fetchDrafts();

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/draft/permit_application',
            );
            expect(apiFetch).toHaveBeenCalledWith('/mock/draft/investigation');
            expect(result).toEqual([
                { id: 'permit-1' },
                { id: 'investigation-1' },
            ]);
        });

        it('skips a failing graph but keeps the others', async () => {
            apiFetch
                .mockResolvedValueOnce(okResponse([{ id: 'permit-1' }]))
                .mockRejectedValueOnce(new Error('Server Error'));

            const result = await fetchDrafts();

            expect(result).toEqual([{ id: 'permit-1' }]);
            expect(console.error).toHaveBeenCalled();
        });
    });

    describe('fetchDraft', () => {
        it('GETs the draft by graph and id', async () => {
            const draft = { id: 'draft-1', data: {} };
            apiFetch.mockResolvedValue(okResponse(draft));

            const result = await fetchDraft('investigation', 'draft-1');

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/draft/investigation/draft-1',
            );
            expect(result).toEqual(draft);
        });
    });

    describe('createDraft', () => {
        it('POSTs an empty draft for the graph', async () => {
            const draft = { id: 'draft-new', data: {} };
            apiFetch.mockResolvedValue(okResponse(draft));

            const result = await createDraft('investigation');

            expect(apiFetch).toHaveBeenCalledWith('/mock/draft/investigation', {
                method: 'POST',
                body: { data: {} },
            });
            expect(result).toEqual(draft);
        });
    });

    describe('fetchMyProjects', () => {
        it('returns results array when paginated', async () => {
            apiFetch.mockResolvedValue(
                okResponse({ results: [{ id: 'proj-1' }] }),
            );
            const result = await fetchMyProjects();
            expect(apiFetch).toHaveBeenCalledWith(
                '/bcap/api/dashboard/external?status=CREATED_BY_ME',
            );
            expect(result).toEqual([{ id: 'proj-1' }]);
        });

        it('returns raw data when not paginated', async () => {
            apiFetch.mockResolvedValue(okResponse([{ id: 'proj-2' }]));
            const result = await fetchMyProjects();
            expect(result).toEqual([{ id: 'proj-2' }]);
        });

        it('returns empty array on error', async () => {
            apiFetch.mockRejectedValue(new Error('Forbidden'));
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
            apiFetch
                .mockResolvedValueOnce(okResponse(finalResource))
                .mockResolvedValueOnce(okResponse(undefined));

            const result = await submitModule(
                'permit-1',
                'draft-7',
                GraphSlug.Investigation,
                { a: 1 } as never,
            );

            expect(apiFetch).toHaveBeenNthCalledWith(
                1,
                '/mock/seed/permit-1/investigation',
                {
                    method: 'POST',
                    body: { aliased_data: { a: 1 } },
                },
            );
            expect(apiFetch).toHaveBeenNthCalledWith(
                2,
                '/mock/draft/investigation/draft-7',
                { method: 'DELETE' },
            );
            expect(result).toEqual(finalResource);
        });

        it('strips draft-only parent_resource_id from the posted body', async () => {
            apiFetch
                .mockResolvedValueOnce(okResponse({ resourceinstanceid: 'i' }))
                .mockResolvedValueOnce(okResponse(undefined));

            await submitModule('permit-1', 'draft-7', GraphSlug.Investigation, {
                parent_resource_id: 'permit-1',
                a: 1,
            } as never);

            expect(apiFetch).toHaveBeenNthCalledWith(
                1,
                '/mock/seed/permit-1/investigation',
                { method: 'POST', body: { aliased_data: { a: 1 } } },
            );
        });

        it('re-throws and logs when the POST fails', async () => {
            const failure = new Error('POST investigation failed');
            apiFetch.mockRejectedValue(failure);

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

    describe('fetchPermitModules', () => {
        it('GETs the seed route and reshapes hosts like drafts', async () => {
            apiFetch.mockResolvedValue(
                okResponse([
                    {
                        resourceinstanceid: 'inv-1',
                        aliased_data: { investigation_identification: {} },
                    },
                ]),
            );

            const result = await fetchPermitModules(
                'permit-1',
                GraphSlug.Investigation,
            );

            expect(apiFetch).toHaveBeenCalledWith(
                '/mock/seed/permit-1/investigation',
            );
            expect(result).toEqual([
                {
                    id: 'inv-1',
                    graph_slug: GraphSlug.Investigation,
                    data: { investigation_identification: {} },
                },
            ]);
        });

        it('returns an empty array on a null body', async () => {
            apiFetch.mockResolvedValue(okResponse(null));

            const result = await fetchPermitModules(
                'permit-1',
                GraphSlug.Investigation,
            );

            expect(result).toEqual([]);
        });

        it('returns an empty array and logs when the request fails', async () => {
            const failure = new Error('boom');
            apiFetch.mockRejectedValue(failure);

            const result = await fetchPermitModules(
                'permit-1',
                GraphSlug.Investigation,
            );

            expect(result).toEqual([]);
            expect(console.error).toHaveBeenCalledWith(
                'Failed to load permit module hosts:',
                failure,
            );
        });
    });

    describe('submitApplication', () => {
        it('POSTs the final resource and DELETEs the draft on success', async () => {
            const finalResource = { resourceinstanceid: 'final-123' };
            const payload = { test: 'data' };

            apiFetch
                .mockResolvedValueOnce(okResponse(finalResource))
                .mockResolvedValueOnce(okResponse(undefined));

            const result = await submitApplication('draft-123', payload);

            expect(apiFetch).toHaveBeenNthCalledWith(
                1,
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

            expect(apiFetch).toHaveBeenNthCalledWith(
                2,
                '/mock/draft/permit_application/draft-123',
                { method: 'DELETE' },
            );

            expect(result).toEqual(finalResource);
        });

        it('re-throws and logs when a request fails', async () => {
            const failure = new Error('POST .../create failed (400)');
            apiFetch.mockRejectedValue(failure);

            await expect(submitApplication('draft-123', {})).rejects.toThrow(
                'POST .../create failed (400)',
            );
            expect(console.error).toHaveBeenCalledWith(
                'Submission API failed:',
                failure,
            );
        });
    });

    // --- NEW TESTS: BCAP Messaging & Contributors ---

    describe('getContributors', () => {
        it('fetches and maps contributors successfully', async () => {
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    results: [
                        { name: 'John Doe', resourceinstanceid: 'user-1' },
                        { resourceinstanceid: 'user-2' }, // Missing name
                    ],
                }),
            } as Response);

            const result = await getContributors();

            expect(global.fetch).toHaveBeenCalledWith('/mock/api/contributor', {
                headers: { accept: 'application/json' },
            });
            expect(result).toEqual([
                { label: 'John Doe', value: 'user-1' },
                { label: 'Unknown Contributor', value: 'user-2' }, // Fallback testing
            ]);
        });

        it('throws an error if response is not ok', async () => {
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: false,
            } as Response);

            await expect(getContributors()).rejects.toThrow(
                'Failed to fetch contributors',
            );
        });
    });

    describe('createBcapMessage', () => {
        it('POSTs a new message with the correct payload and CSRF header', async () => {
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ id: 'new-msg-id' }),
            } as Response);

            const result = await createBcapMessage(
                'Test message',
                'recipient-1',
                'APP-99',
                'permit-99',
                'thread-99',
            );

            expect(global.fetch).toHaveBeenCalledWith(
                '/mock/messages/create',
                expect.objectContaining({
                    method: 'POST',
                    headers: {
                        Accept: 'application/json',
                        'Content-Type': 'application/json',
                        'X-CSRFTOKEN': 'mock-csrf-token',
                    },
                }),
            );

            // Extract the body sent to fetch to verify structure
            const fetchCall = vi.mocked(global.fetch).mock.calls[0];
            const body = JSON.parse(fetchCall[1]?.body as string);

            expect(
                body.aliased_data.message_content.aliased_data.message_content
                    .node_value.en.value,
            ).toBe('Test message');
            expect(
                body.aliased_data.message_content.aliased_data.recipient
                    .node_value.resourceId,
            ).toBe('recipient-1');
            expect(
                body.aliased_data.related_source_message.aliased_data
                    .related_source_message.node_value.resourceId,
            ).toBe('thread-99');

            expect(result).toEqual({ id: 'new-msg-id' });
        });

        it('throws an error if message creation fails', async () => {
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: false,
                statusText: 'Bad Request',
                json: async () => ({ error: 'Invalid data' }),
            } as Response);

            await expect(
                createBcapMessage('test', 'rec-1', 'APP-1', 'perm-1'),
            ).rejects.toThrow('Failed to post message: Bad Request');
            expect(console.error).toHaveBeenCalled();
        });
    });

    describe('getMessagesForPermit', () => {
        it('returns empty messages and null threadId if no threads exist', async () => {
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ results: [] }),
            } as Response);

            const result = await getMessagesForPermit('permit-123');

            expect(global.fetch).toHaveBeenCalledWith(
                '/mock/messages/threads/permit-123',
                expect.any(Object),
            );
            expect(result).toEqual({ messages: [], threadId: null });
        });

        it('fetches threads and messages, formats them, and sorts chronologically', async () => {
            // 1. Mock Thread Response
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ results: ['thread-123'] }), // Simple string format
            } as Response);

            // 2. Mock Messages Response
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    results: [
                        {
                            // Old Question
                            aliased_data: {
                                message_content: {
                                    aliased_data: {
                                        message_author: {
                                            display_value: 'Applicant',
                                        },
                                        message_content: {
                                            node_value: {
                                                en: { value: 'First question' },
                                            },
                                        },
                                        message_creation_date: {
                                            node_value: '2025-01-01T10:00:00Z',
                                        },
                                    },
                                },
                            },
                        },
                        {
                            // Newer Message with Reply embedded
                            aliased_data: {
                                message_content: {
                                    aliased_data: {
                                        message_author: {
                                            display_value: 'Applicant',
                                        },
                                        message_content: {
                                            display_value: 'Second question',
                                        },
                                        message_creation_date: {
                                            node_value: '2026-01-01T10:00:00Z',
                                        },
                                    },
                                },
                                message_response: {
                                    aliased_data: {
                                        response_author: {
                                            display_value: 'Admin',
                                        },
                                        message_response: {
                                            display_value: 'Admin reply',
                                        },
                                        response_issued_date: {
                                            node_value: '2026-02-01T10:00:00Z',
                                        },
                                    },
                                },
                            },
                        },
                    ],
                }),
            } as Response);

            const result = await getMessagesForPermit('permit-123');

            expect(global.fetch).toHaveBeenCalledTimes(2);
            expect(global.fetch).toHaveBeenNthCalledWith(
                2,
                '/mock/messages/thread/thread-123/messages',
                expect.any(Object),
            );

            expect(result.threadId).toBe('thread-123');
            expect(result.messages.length).toBe(3); // 2 questions + 1 reply flattened

            // Validate chronological sorting (2025 -> 2026 Jan -> 2026 Feb)
            expect(result.messages[0].text).toBe('First question');
            expect(result.messages[1].text).toBe('Second question');
            expect(result.messages[2].text).toBe('Admin reply');
            expect(result.messages[2].author).toBe('Admin');
        });

        it('throws an error if threads fetch fails', async () => {
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: false,
            } as Response);

            await expect(getMessagesForPermit('permit-123')).rejects.toThrow(
                'Failed to fetch threads',
            );
        });

        it('throws an error if messages fetch fails', async () => {
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: true,
                json: async () => ['thread-123'],
            } as Response);
            vi.mocked(global.fetch).mockResolvedValueOnce({
                ok: false,
            } as Response);

            await expect(getMessagesForPermit('permit-123')).rejects.toThrow(
                'Failed to fetch messages',
            );
        });
    });
});
