import { ref, watchEffect, type Ref } from 'vue';
import {
    getResourceData,
    getResourceList,
    getRelatedResourceData,
} from '@/bcap/components/pages/api.ts';
import { inlineMessage } from '@/bcap/notify.ts';

export function useResourceData<T>(
    resourceType: string,
    resourceId: Ref<string | undefined>,
) {
    const cache = ref<Record<string, T | null>>({});
    const current = ref<T | null>(null);
    const loading = ref(true);
    const error = ref('');

    watchEffect(async () => {
        const id = resourceId.value;
        if (!id) {
            loading.value = false;
            return;
        }

        if (!(id in cache.value)) {
            loading.value = true;
            error.value = '';

            try {
                const data = await getResourceData(resourceType, id);
                cache.value[id] = data as T;
                current.value = cache.value[id];
            } catch (err) {
                error.value = inlineMessage(err);
                cache.value[id] = null;
                current.value = null;
            } finally {
                loading.value = false;
            }
        } else {
            current.value = cache.value[id];
            loading.value = false;
        }
    });

    return {
        data: current,
        loading,
        error,
        cache,
    };
}

export function useResourceList<T>(
    resourceType: string,
    resourceIds: Ref<string[] | undefined>,
) {
    const cache = ref<Record<string, T | null>>({});
    const current = ref<T | null>(null);
    const loading = ref(true);
    const error = ref('');

    watchEffect(async () => {
        const ids = resourceIds.value;
        if (!ids || ids.length === 0) {
            loading.value = false;
            return;
        }

        loading.value = true;
        error.value = '';

        try {
            const data = await getResourceList(resourceType, ids);
            current.value = data as T;
        } catch (err) {
            error.value = inlineMessage(err);
            current.value = null;
        } finally {
            loading.value = false;
        }
    });

    return {
        data: current,
        loading,
        error,
        cache,
    };
}

export function useRelatedResourceData<
    T extends { resourceinstanceid?: string | null },
>(
    resourceType: string,
    resourceId: Ref<string | string[] | undefined>,
    getFirst: boolean = false,
) {
    const current = ref<T[] | T | null>(null);
    const loading = ref(true);
    const error = ref('');

    watchEffect(async () => {
        const id = resourceId.value;
        const ids = Array.isArray(id) ? id : id ? [id] : [];

        if (ids.length === 0) {
            loading.value = false;
            return;
        }

        loading.value = true;
        error.value = '';

        try {
            const results = await Promise.all(
                ids.map((i) => getRelatedResourceData(resourceType, i)),
            );
            const flat = results.flat() as unknown as T[];
            const seen = new Set<string>();
            const deduped = flat.filter((item) => {
                const itemId = item.resourceinstanceid;
                if (!itemId || seen.has(itemId)) return false;
                seen.add(itemId);
                return true;
            });
            current.value = getFirst ? (deduped[0] ?? null) : deduped;
        } catch (err) {
            error.value = inlineMessage(err);
            current.value = null;
        } finally {
            loading.value = false;
        }
    });

    return { data: current, loading, error };
}
