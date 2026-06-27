import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    fetchDrafts,
    fetchMyProjects,
    submitApplication,
    submitInvestigation,
    deleteDraft,
} from './api';

// 1. Mock the Arches URL generator
vi.mock('arches', () => ({
    default: {
        urls: {
            api_resource_blank: (graphSlug: string) =>
                `/mock/blank/${graphSlug}`,
            api_resource_draft: (graphSlug: string) =>
                `/mock/draft/${graphSlug}`,
            permit_application_create: '/mock/create/permit_application',
            api_investigation: '/mock/create/investigation',
            dashboard_external: '/bcap/api/dashboard/external',
            api_resource: (graph: string, pk: string) =>
                `/bcap/api/resource/${graph}/${pk}`,
        },
    },
}));

// 2. Mock the apiFetch wrapper (its own behavior is covered in api.test.ts)
const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }));
vi.mock('@/bcap/api.ts', () => ({ apiFetch }));

// Resolve apiFetch to a Response-like object whose json() yields body
function okResponse(body: unknown) {
    return { json: vi.fn().mockResolvedValue(body) };
}

describe('Permit API', () => {
    beforeEach(() => {
        apiFetch.mockReset();
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

    describe('submitInvestigation', () => {
        it('POSTs the investigation then DELETEs its draft', async () => {
            const finalResource = { resourceinstanceid: 'inv-1' };
            apiFetch
                .mockResolvedValueOnce(okResponse(finalResource))
                .mockResolvedValueOnce(okResponse(undefined));

            const result = await submitInvestigation('draft-7', { a: 1 });

            expect(apiFetch).toHaveBeenNthCalledWith(
                1,
                '/mock/create/investigation',
                {
                    method: 'POST',
                    body: { draft_id: 'draft-7', aliased_data: { a: 1 } },
                },
            );
            expect(apiFetch).toHaveBeenNthCalledWith(
                2,
                '/mock/draft/investigation/draft-7',
                { method: 'DELETE' },
            );
            expect(result).toEqual(finalResource);
        });

        it('re-throws and logs when the POST fails', async () => {
            const failure = new Error('POST investigation failed');
            apiFetch.mockRejectedValue(failure);

            await expect(submitInvestigation('draft-7', {})).rejects.toThrow(
                'POST investigation failed',
            );
            expect(console.error).toHaveBeenCalledWith(
                'Investigation submission API failed:',
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
});
