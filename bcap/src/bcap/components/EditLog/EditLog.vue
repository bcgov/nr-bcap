<script setup lang="ts">
import { ref } from "vue";
import Button from 'primevue/button';

export interface EditLogResponse {
    modified_on: string | null;
    modified_by: string | null;
    transaction_id?: string | null;
    edit_type?: string | null;
    user_email?: string | null;
    is_system_edit?: boolean;
    method_used?: string;
    error?: string;
    tile_id?: string | null;
    nodegroup_id?: string | null;
}

export type { EditLogResponse };

const props = defineProps<{
    resourceId: string;
    graph: string;
    tileIds?: string[];
    nodegroupConfigs?: Array<{
        alias: string;
        label?: string;
        fetchTiles?: boolean;
    }>;
}>();

const emit = defineEmits<{
    loaded: [data: EditLogResponse];
    error: [error: string];
    populateAllFields: [results: Record<string, { entered_on: string | null; entered_by: string | null }>];
}>();

const loading = ref(false);
const error = ref<string | null>(null);
const dataLoaded = ref(false);

const formatDisplayName = (response: EditLogResponse): string => {
    if (!response.modified_by) {
        return "Unknown";
    }

    if (response.is_system_edit) {
        return response.modified_by;
    }

    return response.modified_by;
};

const formatDate = (dateString: string | null): string => {
    if (!dateString) return "Unknown";

    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch {
        return dateString;
    }
};

const loadEditLog = async (
    resourceId: string,
    graph: string,
    options?: {
        tileId?: string;
        nodegroupId?: string;
        nodegroupAlias?: string;
    }
): Promise<EditLogResponse | null> => {
    try {
        const params = new URLSearchParams();

        if (options?.tileId) {
            params.append('tile_id', options.tileId);
        }
        if (options?.nodegroupId) {
            params.append('nodegroup_id', options.nodegroupId);
        }
        if (options?.nodegroupAlias) {
            params.append('nodegroup_alias', options.nodegroupAlias);
        }

        const queryString = params.toString();
        const url = `/bcap/api/resources/${graph}/${resourceId}/edit-log/${queryString ? `?${queryString}` : ''}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Failed to load edit information: ${response.status}`);
        }

        const result: EditLogResponse = await response.json();
        return result;
    } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error occurred";
        error.value = errorMessage;
        console.error("Error loading edit log:", err);
        return null;
    }
};

const populateAllEnteredFields = async () => {
    loading.value = true;
    const results: Record<string, { entered_on: string | null; entered_by: string | null }> = {};

    try {
        // If specific tile IDs are provided, fetch data for each
        if (props.tileIds && props.tileIds.length > 0) {
            const promises = props.tileIds.map(async (tileId) => {
                const result = await loadEditLog(props.resourceId, props.graph, {
                    tileId: tileId
                });

                if (result) {
                    return {
                        tileId: tileId,
                        data: {
                            entered_on: formatDate(result.modified_on),
                            entered_by: formatDisplayName(result)
                        }
                    };
                }
                return null;
            });

            const responses = await Promise.all(promises);

            responses.forEach((response) => {
                if (response) {
                    results[`tile_${response.tileId}`] = response.data;
                }
            });
        }
        // If nodegroup configs provided
        else if (props.nodegroupConfigs && props.nodegroupConfigs.length > 0) {
            const promises = props.nodegroupConfigs.map(async (config) => {
                const result = await loadEditLog(props.resourceId, props.graph, {
                    nodegroupAlias: config.alias
                });

                if (result) {
                    return {
                        alias: config.alias,
                        data: {
                            entered_on: formatDate(result.modified_on),
                            entered_by: formatDisplayName(result)
                        }
                    };
                }

                return null;
            });

            const responses = await Promise.all(promises);

            responses.forEach((response) => {
                if (response) {
                    results[response.alias] = response.data;
                }
            });
        }
        // Fetch resource-level data
        else {
            const result = await loadEditLog(props.resourceId, props.graph);
            if (result) {
                results['resource'] = {
                    entered_on: formatDate(result.modified_on),
                    entered_by: formatDisplayName(result)
                };
            }
        }

        emit('populateAllFields', results);
        dataLoaded.value = true;
    } catch (err) {
        console.error('Error loading edit logs:', err);
        error.value = err instanceof Error ? err.message : 'Unknown error';
    } finally {
        loading.value = false;
    }
};
</script>

<template>
    <Button
        :label="loading ? 'Loading...' : 'Populate All Entered On/By Fields'"
        :icon="loading ? 'pi pi-spinner pi-spin' : 'pi pi-user-edit'"
        :disabled="loading"
        class="control-button"
        severity="info"
        @click="populateAllEnteredFields"
    />
</template>

<style scoped>
.control-button {
    min-width: 180px;
    font-size: 1.2rem;
    font-weight: 500;
}

@media (max-width: 768px) {
    .control-button {
        width: 100%;
        min-width: auto;
    }
}
</style>
