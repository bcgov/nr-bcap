import { ref, watchEffect, type Ref } from "vue";
import { getResourceData, getRelatedResourceData } from "@/bcap/components/pages/api.ts";

export function useResourceData<T>(
    resourceType: string,
    resourceId: Ref<string | undefined>
) {
    const cache = ref<Record<string, T | null>>({});
    const current = ref<T | null>(null);
    const loading = ref(true);

    watchEffect(async () => {
        const id = resourceId.value;
        if (!id) {
            loading.value = false;
            return;
        }

        if (!(id in cache.value)) {
            loading.value = true;

            try {
                const data = await getResourceData(resourceType, id);
                cache.value[id] = data as T;
                current.value = cache.value[id];
            } catch (error) {
                console.error(`Failed to fetch ${resourceType}:`, error);
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
        cache,
    };
}

export function useRelatedResourceData<T>(
    resourceType: string,
    resourceId: Ref<string | undefined>,
    getFirst: boolean = false
) {
    const cache = ref<Record<string, T[] | T | null>>({});
    const current = ref<T[] | T | null>(null);
    const loading = ref(true);

    watchEffect(async () => {
        const id = resourceId.value;

        if (!id) {
            loading.value = false;
            return;
        }

        if (!(id in cache.value)) {
            loading.value = true;

            try {
                const data = await getRelatedResourceData(resourceType, id);
                const result = getFirst && data.length > 0 ? data[0] : data;
                cache.value[id] = result as T[] | T;
                current.value = cache.value[id];
            } catch (error) {
                console.error(`Failed to fetch related ${resourceType}:`, error);
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
        cache,
    };
}
