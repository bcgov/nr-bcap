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
        },
    },
}));

// 2. Mock the api layer. apiFetch returns a Response-like object (callers read
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

        it('stores the parent resource id in the draft blob when given', async () => {
            apiFetchJson.mockResolvedValue({ id: 'draft-new', data: {} });

            await createDraft('investigation', 'permit-1');

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/draft/investigation',
                {
                    method: 'POST',
                    body: { data: { parent_resource_id: 'permit-1' } },
                },
            );
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

        it('strips draft-only parent_resource_id from the posted body', async () => {
            apiFetchJson.mockResolvedValue({ resourceinstanceid: 'i' });
            apiFetch.mockResolvedValue(okResponse(undefined));

            await submitModule('permit-1', 'draft-7', GraphSlug.Investigation, {
                parent_resource_id: 'permit-1',
                a: 1,
            } as never);

            expect(apiFetchJson).toHaveBeenCalledWith(
                '/mock/seed/permit-1/investigation',
                { method: 'POST', body: { aliased_data: { a: 1 } } },
            );
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
});
