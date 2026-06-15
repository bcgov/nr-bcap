import { describe, it, expect, vi, beforeEach } from 'vitest';

// Stand in for the runtime-injected `arches.urls` so these tests don't depend
// on the real arches.js bundle resolving. Mirrors the patterns in bcap/urls.py.
vi.mock('arches', () => ({
    default: {
        urls: {
            api_resource: (graph_slug: string, resource_id: string) =>
                `/bcap/api/resource/${graph_slug}/${resource_id}`,
            api_site_related_resources: (
                graph_slug: string,
                resource_id: string,
            ) =>
                `/bcap/api/arch_site_related_resources/${graph_slug}/${resource_id}`,
            api_process_requirements: (resource_id: string) =>
                `/bcap/api/resource/process_requirement/${resource_id}`,
            api_requirement_submission: (resource_id: string) =>
                `/bcap/api/requirement_submissions/${resource_id}/`,
            dashboard: '/bcap/api/dashboard',
            unlinked_contributors: '/bcap/api/unlinked_contributors',
            assignable_groups: '/bcap/api/assignable_groups',
            registration_link: '/bcap/api/registration_link',
        },
    },
}));

import {
    getResourceData,
    getRelatedResourceData,
    getProcessRequirementData,
    getRequirementSubmissionData,
    getInternalDashboardData,
    getUnlinkedContributors,
    getAssignableGroups,
    issueRegistrationLink,
} from './api';

function mockFetchOk(body: unknown) {
    return vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(body),
        text: vi.fn().mockResolvedValue(''),
    });
}

function mockFetchError(status: number, statusText: string, body = '') {
    return vi.fn().mockResolvedValue({
        ok: false,
        status,
        statusText,
        json: vi.fn().mockResolvedValue({}),
        text: vi.fn().mockResolvedValue(body),
    });
}

beforeEach(() => {
    vi.restoreAllMocks();
});

describe('getResourceData', () => {
    it('returns parsed JSON on success', async () => {
        const data = { resource_id: '123', graph_slug: 'arch-site' };
        vi.stubGlobal('fetch', mockFetchOk(data));

        const result = await getResourceData('arch-site', '123');

        expect(fetch).toHaveBeenCalledWith('/bcap/api/resource/arch-site/123');
        expect(result).toEqual(data);
    });

    it('throws with response text on error', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(404, 'Not Found', 'Resource missing'),
        );

        await expect(getResourceData('arch-site', '999')).rejects.toThrow(
            'Resource missing',
        );
    });

    it('throws with statusText when response body is empty', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(500, 'Internal Server Error', ''),
        );

        await expect(getResourceData('arch-site', '1')).rejects.toThrow(
            'Internal Server Error',
        );
    });
});

describe('getRelatedResourceData', () => {
    it('returns the results array on success', async () => {
        const results = [{ id: 'a' }, { id: 'b' }];
        vi.stubGlobal('fetch', mockFetchOk({ results }));

        const result = await getRelatedResourceData('arch-site', '123');

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/arch_site_related_resources/arch-site/123',
        );
        expect(result).toEqual(results);
    });

    it('throws with response text on error', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(403, 'Forbidden', 'Access denied'),
        );

        await expect(getRelatedResourceData('arch-site', '1')).rejects.toThrow(
            'Access denied',
        );
    });

    it('throws with statusText when response body is empty', async () => {
        vi.stubGlobal('fetch', mockFetchError(500, 'Server Error', ''));

        await expect(getRelatedResourceData('arch-site', '1')).rejects.toThrow(
            'Server Error',
        );
    });
});

describe('getProcessRequirementData', () => {
    it('returns parsed JSON on success', async () => {
        const data = { permit_id: 'p1', requirements: [] };
        vi.stubGlobal('fetch', mockFetchOk(data));

        const result = await getProcessRequirementData('p1');

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/resource/process_requirement/p1',
        );
        expect(result).toEqual(data);
    });

    it('throws with response text on error', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(404, 'Not Found', 'Permit not found'),
        );

        await expect(getProcessRequirementData('p99')).rejects.toThrow(
            'Permit not found',
        );
    });

    it('throws with statusText when response body is empty', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(500, 'Internal Server Error', ''),
        );

        await expect(getProcessRequirementData('p1')).rejects.toThrow(
            'Internal Server Error',
        );
    });
});

describe('getRequirementSubmissionData', () => {
    it('returns parsed JSON on success', async () => {
        const data = { submission_id: 's1', status: 'pending' };
        vi.stubGlobal('fetch', mockFetchOk(data));

        const result = await getRequirementSubmissionData('s1');

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/requirement_submissions/s1/',
        );
        expect(result).toEqual(data);
    });

    it('throws with response text on error', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(404, 'Not Found', 'Submission not found'),
        );

        await expect(getRequirementSubmissionData('s99')).rejects.toThrow(
            'Submission not found',
        );
    });

    it('throws with statusText when response body is empty', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(500, 'Internal Server Error', ''),
        );

        await expect(getRequirementSubmissionData('s1')).rejects.toThrow(
            'Internal Server Error',
        );
    });
});

describe('getInternalDashboardData', () => {
    it('returns results array on success', async () => {
        const results = [{ id: 'proj1' }, { id: 'proj2' }];
        vi.stubGlobal('fetch', mockFetchOk({ results }));

        const result = await getInternalDashboardData();

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/dashboard?limit=100&page=1',
        );
        expect(result).toEqual(results);
    });

    it('returns empty array when response has no results key', async () => {
        vi.stubGlobal('fetch', mockFetchOk({ data: [] }));

        const result = await getInternalDashboardData();

        expect(result).toEqual([]);
    });

    it('returns empty array when results is not an array', async () => {
        vi.stubGlobal('fetch', mockFetchOk({ results: 'not-an-array' }));

        const result = await getInternalDashboardData();

        expect(result).toEqual([]);
    });

    it('returns empty array on HTTP error', async () => {
        vi.stubGlobal('fetch', mockFetchError(500, 'Internal Server Error'));

        const result = await getInternalDashboardData();

        expect(result).toEqual([]);
    });

    it('returns empty array when fetch throws', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockRejectedValue(new Error('Network failure')),
        );

        const result = await getInternalDashboardData();

        expect(result).toEqual([]);
    });
});

describe('getUnlinkedContributors', () => {
    it('appends the search query when provided', async () => {
        vi.stubGlobal('fetch', mockFetchOk([]));

        await getUnlinkedContributors('jane doe');

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/unlinked_contributors?search=jane%20doe',
        );
    });

    it('omits the query when no search term', async () => {
        vi.stubGlobal('fetch', mockFetchOk([]));

        await getUnlinkedContributors();

        expect(fetch).toHaveBeenCalledWith('/bcap/api/unlinked_contributors');
    });
});

describe('issueRegistrationLink error flattening', () => {
    it('surfaces a DRF { detail } message', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(
                400,
                'Bad Request',
                JSON.stringify({ detail: 'Already linked.' }),
            ),
        );

        await expect(issueRegistrationLink({ groups: [] })).rejects.toThrow(
            'Already linked.',
        );
    });

    it('flattens nested field errors instead of dumping JSON', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(
                400,
                'Bad Request',
                JSON.stringify({
                    new_contributor: {
                        email: ['Enter a valid email address.'],
                    },
                }),
            ),
        );

        await expect(issueRegistrationLink({ groups: [] })).rejects.toThrow(
            'Enter a valid email address.',
        );
    });

    it('falls back to raw text when the body is not JSON', async () => {
        vi.stubGlobal('fetch', mockFetchError(500, 'Server Error', 'boom'));

        await expect(issueRegistrationLink({ groups: [] })).rejects.toThrow(
            'boom',
        );
    });
});

describe('getAssignableGroups', () => {
    it('returns the group list on success', async () => {
        vi.stubGlobal('fetch', mockFetchOk(['Submitter', 'Permit Decider']));

        const result = await getAssignableGroups();

        expect(fetch).toHaveBeenCalledWith('/bcap/api/assignable_groups');
        expect(result).toEqual(['Submitter', 'Permit Decider']);
    });
});
