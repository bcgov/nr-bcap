import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';
import { flushPromises } from '@vue/test-utils';

const getResourceData = vi.fn();
const getRelatedResourceData = vi.fn();
vi.mock('@/bcap/components/pages/api.ts', () => ({
    getResourceData: (...args: unknown[]) => getResourceData(...args),
    getRelatedResourceData: (...args: unknown[]) =>
        getRelatedResourceData(...args),
}));

import { useResourceData, useRelatedResourceData } from './useResourceData';

beforeEach(() => {
    getResourceData.mockReset();
    getRelatedResourceData.mockReset();
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('useResourceData', () => {
    it('does not fetch and clears loading when there is no id', async () => {
        const { data, loading } = useResourceData('site', ref(undefined));
        await flushPromises();
        expect(getResourceData).not.toHaveBeenCalled();
        expect(data.value).toBeNull();
        expect(loading.value).toBe(false);
    });

    it('fetches, exposes the result and caches it by id', async () => {
        getResourceData.mockResolvedValue({ name: 'Site A' });
        const { data, loading, cache } = useResourceData('site', ref('a'));
        await flushPromises();

        expect(getResourceData).toHaveBeenCalledWith('site', 'a');
        expect(data.value).toEqual({ name: 'Site A' });
        expect(cache.value['a']).toEqual({ name: 'Site A' });
        expect(loading.value).toBe(false);
    });

    it('serves a cached id without fetching again', async () => {
        getResourceData.mockResolvedValueOnce({ name: 'A' });
        getResourceData.mockResolvedValueOnce({ name: 'B' });
        const id = ref('a');
        const { data } = useResourceData('site', id);
        await flushPromises();

        id.value = 'b';
        await flushPromises();
        expect(getResourceData).toHaveBeenCalledTimes(2);

        id.value = 'a';
        await flushPromises();
        expect(getResourceData).toHaveBeenCalledTimes(2); // 'a' came from cache
        expect(data.value).toEqual({ name: 'A' });
    });

    it('clears data on fetch error', async () => {
        getResourceData.mockRejectedValue(new Error('boom'));
        const { data, loading } = useResourceData('site', ref('a'));
        await flushPromises();

        expect(data.value).toBeNull();
        expect(loading.value).toBe(false);
    });
});

describe('useRelatedResourceData', () => {
    it('returns the full array by default', async () => {
        getRelatedResourceData.mockResolvedValue([{ id: 1 }, { id: 2 }]);
        const { data } = useRelatedResourceData('visit', ref('a'));
        await flushPromises();
        expect(data.value).toEqual([{ id: 1 }, { id: 2 }]);
    });

    it('returns the first element when getFirst is set', async () => {
        getRelatedResourceData.mockResolvedValue([{ id: 1 }, { id: 2 }]);
        const { data } = useRelatedResourceData('visit', ref('a'), true);
        await flushPromises();
        expect(data.value).toEqual({ id: 1 });
    });

    it('clears data on fetch error', async () => {
        getRelatedResourceData.mockRejectedValue(new Error('boom'));
        const { data } = useRelatedResourceData('visit', ref('a'));
        await flushPromises();
        expect(data.value).toBeNull();
    });
});
