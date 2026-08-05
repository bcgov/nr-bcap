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
        },
    },
}));

import { getResourceData, getRelatedResourceData } from './api';

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

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/resource/arch-site/123',
            expect.anything(),
        );
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
            expect.anything(),
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
