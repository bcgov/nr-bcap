import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
    getResourceData,
    getRelatedResourceData,
    getPermitRequirementData,
    getRequirementSubmissionData,
    getInternalDashboardData,
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
        vi.stubGlobal('fetch', mockFetchError(404, 'Not Found', 'Resource missing'));

        await expect(getResourceData('arch-site', '999')).rejects.toThrow(
            'Resource missing',
        );
    });

    it('throws with statusText when response body is empty', async () => {
        vi.stubGlobal('fetch', mockFetchError(500, 'Internal Server Error', ''));

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
        vi.stubGlobal('fetch', mockFetchError(403, 'Forbidden', 'Access denied'));

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

describe('getPermitRequirementData', () => {
    it('returns parsed JSON on success', async () => {
        const data = { permit_id: 'p1', requirements: [] };
        vi.stubGlobal('fetch', mockFetchOk(data));

        const result = await getPermitRequirementData('p1');

        expect(fetch).toHaveBeenCalledWith('/bcap/api/permit_requirements/p1/');
        expect(result).toEqual(data);
    });

    it('throws with response text on error', async () => {
        vi.stubGlobal('fetch', mockFetchError(404, 'Not Found', 'Permit not found'));

        await expect(getPermitRequirementData('p99')).rejects.toThrow(
            'Permit not found',
        );
    });

    it('throws with statusText when response body is empty', async () => {
        vi.stubGlobal('fetch', mockFetchError(500, 'Internal Server Error', ''));

        await expect(getPermitRequirementData('p1')).rejects.toThrow(
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
        vi.stubGlobal('fetch', mockFetchError(404, 'Not Found', 'Submission not found'));

        await expect(getRequirementSubmissionData('s99')).rejects.toThrow(
            'Submission not found',
        );
    });

    it('throws with statusText when response body is empty', async () => {
        vi.stubGlobal('fetch', mockFetchError(500, 'Internal Server Error', ''));

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
            '/bcap/api/dashboard?limit=100&page=1&status=UNASSIGNED',
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
