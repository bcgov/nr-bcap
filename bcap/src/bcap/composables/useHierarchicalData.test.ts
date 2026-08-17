import { ref } from 'vue';
import { flushPromises } from '@vue/test-utils';

import { useHierarchicalData } from './useHierarchicalData';

const fetchMock = vi.fn();

beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

const config = {
    sourceField: 'category',
    hierarchicalFields: ['level1', 'level2'],
};

describe('useHierarchicalData', () => {
    it('produces no rows when the source is undefined', async () => {
        const { processedData } = useHierarchicalData(ref(undefined), config);
        await flushPromises();
        expect(processedData.value).toEqual([]);
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it('produces no rows when the source is empty', async () => {
        const { processedData } = useHierarchicalData(ref([]), config);
        await flushPromises();
        expect(processedData.value).toEqual([]);
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it('falls back to the display value when there is no list-item URI', async () => {
        const source = ref([
            {
                tileid: 't1',
                aliased_data: {
                    category: {
                        node_value: 'Stone',
                        display_value: 'Stone',
                        details: [],
                    },
                },
            },
        ]);

        const { processedData } = useHierarchicalData(source, config);
        await flushPromises();

        expect(fetchMock).not.toHaveBeenCalled();
        const row = processedData.value[0].aliased_data;
        expect(row.level1.display_value).toBe('Stone');
        expect(row.level2.display_value).toBe('');
        expect(row.level2.node_value).toBeNull();
    });

    it('extracts the list-item id from the URI and maps the fetched hierarchy', async () => {
        fetchMock.mockResolvedValue({
            ok: true,
            json: async () => ({ labels: ['Root', 'Child'] }),
        });

        const source = ref([
            {
                tileid: 't1',
                aliased_data: {
                    category: {
                        node_value: [{ uri: 'https://x/item/abc123' }],
                        display_value: 'Child',
                        details: [],
                    },
                },
            },
        ]);

        const { processedData } = useHierarchicalData(source, config);
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith('/bcap/api/hierarchy/abc123/');
        const row = processedData.value[0].aliased_data;
        expect(row.level1.display_value).toBe('Root');
        expect(row.level2.display_value).toBe('Child');
    });

    it('falls back to the display value when the hierarchy fetch fails', async () => {
        fetchMock.mockResolvedValue({ ok: false, status: 500 });

        const source = ref([
            {
                tileid: 't1',
                aliased_data: {
                    category: {
                        node_value: [{ uri: 'https://x/item/abc123' }],
                        display_value: 'Leaf',
                        details: [],
                    },
                },
            },
        ]);

        const { processedData } = useHierarchicalData(source, config);
        await flushPromises();

        expect(fetchMock).toHaveBeenCalled();
        expect(processedData.value[0].aliased_data.level1.display_value).toBe(
            'Leaf',
        );
    });

    it('passes flat fields through and defaults the missing ones', async () => {
        const source = ref([
            {
                tileid: 't1',
                aliased_data: {
                    category: {
                        node_value: 'X',
                        display_value: 'X',
                        details: [],
                    },
                    note: {
                        node_value: 'hello',
                        display_value: 'hello',
                        details: [],
                    },
                },
            },
        ]);

        const { processedData } = useHierarchicalData(source, {
            ...config,
            flatFields: ['note', 'absent'],
        });
        await flushPromises();

        const row = processedData.value[0].aliased_data;
        expect(row.note.display_value).toBe('hello');
        expect(row.absent.display_value).toBe('');
        expect(row.absent.node_value).toBeNull();
    });

    it('synthesises a tileid from the source field and index when absent', async () => {
        const source = ref([
            {
                aliased_data: {
                    category: {
                        node_value: 'X',
                        display_value: 'X',
                        details: [],
                    },
                },
            },
        ]);

        const { processedData } = useHierarchicalData(source, config);
        await flushPromises();

        expect(processedData.value[0].tileid).toBe('category-0');
    });
});
