import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    getBlankPermitApplication,
    fetchDrafts,
    fetchMyProjects,
    submitApplication,
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
            dashboard_external: '/bcap/api/dashboard/external',
            api_resource: (graph: string, pk: string) =>
                `/bcap/api/resource/${graph}/${pk}`,
        },
    },
}));

// 2. Mock CSRF token utility
vi.mock('@/bcap/util.ts', () => ({
    getCsrfToken: () => 'mock-csrf-token',
}));

// Helper functions for basic fetch mocking
function mockFetchOk(body: unknown) {
    return vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(body),
    });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mockFetchError(status: number, statusText: string, body: any = null) {
    return vi.fn().mockResolvedValue({
        ok: false,
        status,
        statusText,
        json: body
            ? vi.fn().mockResolvedValue(body)
            : vi.fn().mockRejectedValue(new Error('JSON parse error')),
    });
}

describe('Permit API', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        // Hide expected console.errors from cluttering test output
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('getBlankPermitApplication', () => {
        it('fetches a blank permit application JSON', async () => {
            const mockData = { id: 'blank-123' };
            vi.stubGlobal('fetch', mockFetchOk(mockData));

            const result = await getBlankPermitApplication();

            expect(fetch).toHaveBeenCalledWith(
                '/mock/blank/permit_application?format=json',
                {},
            );
            expect(result).toEqual(mockData);
        });
    });

    describe('fetchDrafts', () => {
        it('returns results array when paginated', async () => {
            vi.stubGlobal(
                'fetch',
                mockFetchOk({ results: [{ id: 'draft-1' }] }),
            );
            const result = await fetchDrafts();
            expect(result).toEqual([{ id: 'draft-1' }]);
        });

        it('returns raw data when not paginated', async () => {
            vi.stubGlobal('fetch', mockFetchOk([{ id: 'draft-2' }]));
            const result = await fetchDrafts();
            expect(result).toEqual([{ id: 'draft-2' }]);
        });

        it('returns empty array on HTTP error', async () => {
            vi.stubGlobal('fetch', mockFetchError(500, 'Server Error'));
            const result = await fetchDrafts();
            expect(result).toEqual([]);
            expect(console.error).toHaveBeenCalled();
        });

        it('returns empty array on network failure', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn().mockRejectedValue(new Error('Network Down')),
            );
            const result = await fetchDrafts();
            expect(result).toEqual([]);
        });
    });

    describe('fetchMyProjects', () => {
        it('returns results array when paginated', async () => {
            vi.stubGlobal(
                'fetch',
                mockFetchOk({ results: [{ id: 'proj-1' }] }),
            );
            const result = await fetchMyProjects();
            expect(fetch).toHaveBeenCalledWith(
                '/bcap/api/dashboard/external?status=CREATED_BY_ME',
                expect.any(Object),
            );
            expect(result).toEqual([{ id: 'proj-1' }]);
        });

        it('returns raw data when not paginated', async () => {
            vi.stubGlobal('fetch', mockFetchOk([{ id: 'proj-2' }]));
            const result = await fetchMyProjects();
            expect(result).toEqual([{ id: 'proj-2' }]);
        });

        it('returns empty array on HTTP error', async () => {
            vi.stubGlobal('fetch', mockFetchError(403, 'Forbidden'));
            const result = await fetchMyProjects();
            expect(result).toEqual([]);
        });
    });

    describe('submitApplication', () => {
        it('POSTs the final resource and DELETEs the draft on success', async () => {
            const finalResource = { resourceinstanceid: 'final-123' };
            const payload = { test: 'data' };

            // Mock fetch to resolve twice: first for the POST, second for the DELETE
            const fetchMock = vi
                .fn()
                .mockResolvedValueOnce({
                    ok: true,
                    json: vi.fn().mockResolvedValue(finalResource),
                })
                .mockResolvedValueOnce({
                    ok: true,
                });
            vi.stubGlobal('fetch', fetchMock);

            const result = await submitApplication('draft-123', payload);

            // Assert POST request
            expect(fetchMock).toHaveBeenNthCalledWith(
                1,
                '/mock/create/permit_application',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': 'mock-csrf-token',
                    },
                    body: JSON.stringify({
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
                    }),
                },
            );

            // Assert DELETE request
            expect(fetchMock).toHaveBeenNthCalledWith(
                2,
                '/mock/draft/permit_application/draft-123',
                {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': 'mock-csrf-token' },
                },
            );

            expect(result).toEqual(finalResource);
        });

        it('throws an error with JSON details when POST fails', async () => {
            const errorDetails = { detail: 'Validation failed' };
            vi.stubGlobal(
                'fetch',
                mockFetchError(400, 'Bad Request', errorDetails),
            );

            await expect(submitApplication('draft-123', {})).rejects.toThrow(
                'Status 400: {"detail":"Validation failed"}',
            );
            expect(console.error).toHaveBeenCalledWith(
                'Django 400 Error Details:',
                errorDetails,
            );
        });

        it('throws a fallback error when POST fails and response is not JSON', async () => {
            // Mock a 500 error where json() fails to parse
            vi.stubGlobal('fetch', mockFetchError(500, 'Server Error'));

            await expect(submitApplication('draft-123', {})).rejects.toThrow(
                'Status 500: "No additional details provided by server."',
            );
        });

        it('re-throws network errors', async () => {
            const networkError = new Error('Network failure');
            vi.stubGlobal('fetch', vi.fn().mockRejectedValue(networkError));

            await expect(submitApplication('draft-123', {})).rejects.toThrow(
                'Network failure',
            );
            expect(console.error).toHaveBeenCalledWith(
                'Submission API failed:',
                networkError,
            );
        });
    });
});
