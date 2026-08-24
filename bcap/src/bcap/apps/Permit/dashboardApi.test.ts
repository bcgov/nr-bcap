// Stand in for the runtime-injected `arches.urls` so these tests don't depend
// on the real arches.js bundle resolving. Mirrors the patterns in bcap/urls.py.

import {
    getProcessRequirementData,
    getInternalDashboardData,
} from '@/bcap/apps/Permit/api.ts';

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

describe('getProcessRequirementData', () => {
    it('returns parsed JSON on success', async () => {
        // The response is validated against zProcessRequirement, so the fixture
        // must satisfy the resource schema's required fields.
        const data = {
            graph_has_different_publication: false,
            name: 'Test Requirement',
            descriptors: {
                en: { name: 'Test', description: '', map_popup: '' },
            },
            legacyid: null,
            createdtime: '2026-01-01T00:00:00Z',
            graph_publication: null,
            resource_instance_lifecycle_state:
                '00000000-0000-0000-0000-000000000000',
            principaluser: null,
        };
        vi.stubGlobal('fetch', mockFetchOk(data));

        const result = await getProcessRequirementData('p1');

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/process_requirement/p1',
            expect.anything(),
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

describe('getInternalDashboardData', () => {
    it('returns results array on success', async () => {
        const results = [{ id: 'proj1' }, { id: 'proj2' }];
        vi.stubGlobal('fetch', mockFetchOk({ results }));

        const result = await getInternalDashboardData();

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/dashboard?limit=100&page=1',
            expect.anything(),
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
