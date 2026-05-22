<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';

interface SubRequirement {
    id: string;
    sortOrder: number;
    name: string;
    description: string;
    isSatisfied: boolean;
    notes: string;
}

interface DateTile {
    tileid: string | null;
    nodegroup_id: string;
    data: Record<string, any>;
}

const route = useRoute();
const idFromUrl = route.query.id;
const subRequirements = ref<SubRequirement[]>([]);
const dateTile = ref<DateTile | null>(null);
const isLoading = ref(true);
const errorMessage = ref('');

// Arches UUID Constants
const SUB_REQ_NODEGROUP = '5ea00f2f-1a7b-47ee-b23c-9dd8cb3c5cd7';
const NODE_SORT = '461e5988-c6c7-41a7-ac48-abbd28216542';
const NODE_NAME = '9e5eff66-1dc8-41de-a544-930e348b3782';
const NODE_DESC = 'feddcbb3-e905-44e4-93b7-d63ce3be92fa';
const NODE_SATISFIED = '49d33cbb-e857-4b21-8bfe-f6632ce53f9f';
const NODE_NOTES = 'a44988ea-0c8a-40f0-a51c-90fb5616e34e';
const DATE_NODEGROUP = '71cc085c-9f66-47d6-8b56-b223e9a60cb8';
const NODE_START_DATE = '8c896564-f9c9-44ac-a563-93c1ee751fea';
const NODE_COMP_DATE = '0cadf9ba-0e2d-42e9-b11e-042390bcb88c';

const loadData = async () => {
    if (!idFromUrl) {
        errorMessage.value = 'No resource ID provided in the URL.';
        isLoading.value = false;
        return;
    }

    try {
        const response = await fetch(
            `/bcap/api/process_requirements/${idFromUrl}`,
        );
        if (!response.ok)
            throw new Error(`API returned status: ${response.status}`);

        const data = await response.json();

        if (data.tiles && data.tiles.length > 0) {
            const foundDateTile = data.tiles.find(
                (t: Record<string, any>) => t.nodegroup_id === DATE_NODEGROUP,
            );
            if (foundDateTile) {
                dateTile.value = foundDateTile as DateTile;
            } else {
                dateTile.value = {
                    tileid: null,
                    nodegroup_id: DATE_NODEGROUP,
                    data: {},
                };
            }

            subRequirements.value = data.tiles
                .filter(
                    (tile: Record<string, any>) =>
                        tile.nodegroup_id === SUB_REQ_NODEGROUP,
                )
                .map((tile: Record<string, any>): SubRequirement => {
                    const tileData = tile.data;
                    const extractText = (node: any) =>
                        node?.en?.value || node || '';

                    return {
                        id: tile.tileid,
                        sortOrder: tileData[NODE_SORT] || 99,
                        name:
                            extractText(tileData[NODE_NAME]) || 'Unnamed Step',
                        description: extractText(tileData[NODE_DESC]),
                        isSatisfied:
                            tileData[NODE_SATISFIED] === true ||
                            tileData[NODE_SATISFIED] === 'true',
                        notes: extractText(tileData[NODE_NOTES]),
                    };
                })
                .sort(
                    (a: SubRequirement, b: SubRequirement) =>
                        a.sortOrder - b.sortOrder,
                );
        }
    } catch (error) {
        console.error('Failed to load sub-requirements:', error);
        errorMessage.value = 'Failed to load checklist data. Please try again.';
    } finally {
        isLoading.value = false;
    }
};

onMounted(() => {
    loadData();
});

const handleCheckboxChange = () => {
    if (!dateTile.value) return;
    const today = new Date().toISOString().split('T')[0];
    const anyChecked = subRequirements.value.some((req) => req.isSatisfied);
    const allChecked = subRequirements.value.every((req) => req.isSatisfied);

    if (anyChecked && !dateTile.value.data[NODE_START_DATE]) {
        dateTile.value.data[NODE_START_DATE] = today;
    }
    if (allChecked && !dateTile.value.data[NODE_COMP_DATE]) {
        dateTile.value.data[NODE_COMP_DATE] = today;
    } else if (!allChecked && dateTile.value.data[NODE_COMP_DATE]) {
        dateTile.value.data[NODE_COMP_DATE] = null;
    }

    saveChanges();
};

const saveChanges = async () => {
    try {
        const response = await fetch(
            `/bcap/api/process_requirements/${idFromUrl}`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken':
                        document.cookie
                            .split('; ')
                            .find((row) => row.startsWith('csrftoken='))
                            ?.split('=')[1] || '',
                },
                body: JSON.stringify({
                    dateTile: dateTile.value,
                    requirements: subRequirements.value,
                }),
            },
        );

        if (!response.ok) throw new Error('Failed to save');
    } catch (error) {
        console.error('Save error:', error);
    }
};
</script>

<template>
    <div class="checklist-container">
        <div class="title-row">
            <h2 class="page-title">Process Sub-Requirements</h2>

            <div
                class="date-metadata"
                v-if="dateTile"
            >
                <span
                    class="date-pill"
                    :class="{ active: dateTile.data[NODE_START_DATE] }"
                >
                    <strong>Started:</strong>
                    {{ dateTile.data[NODE_START_DATE] || 'Pending' }}
                </span>
                <span
                    class="date-pill"
                    :class="{ complete: dateTile.data[NODE_COMP_DATE] }"
                >
                    <strong>Completed:</strong>
                    {{ dateTile.data[NODE_COMP_DATE] || 'Pending' }}
                </span>
            </div>
        </div>

        <div
            v-if="isLoading"
            class="status-state"
        >
            <p>Loading checklist...</p>
        </div>

        <div
            v-else-if="errorMessage"
            class="status-state error"
        >
            <p>{{ errorMessage }}</p>
        </div>

        <div
            v-else
            class="checklist-items"
        >
            <div
                v-for="req in subRequirements"
                :key="req.id"
                class="requirement-item"
            >
                <div class="req-header">
                    <input
                        type="checkbox"
                        :id="'check-' + req.id"
                        v-model="req.isSatisfied"
                        @change="handleCheckboxChange"
                        class="req-checkbox"
                    />
                    <div class="req-titles">
                        <label
                            :for="'check-' + req.id"
                            class="req-name"
                        >
                            {{ req.name }}
                        </label>
                        <p class="req-desc">{{ req.description }}</p>
                    </div>
                </div>

                <div class="req-body">
                    <textarea
                        :id="'notes-' + req.id"
                        v-model="req.notes"
                        @change="saveChanges"
                        class="req-notes-input"
                        rows="2"
                        placeholder="Add assessment notes..."
                    ></textarea>
                </div>
            </div>

            <div
                v-if="subRequirements.length === 0"
                class="status-state"
            >
                <p>No sub-requirements found for this process.</p>
            </div>
        </div>
    </div>
    <br />
    <br />
    <br />
    <br />
</template>

<style scoped>
.checklist-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem 1rem;
    font-family: Arial, sans-serif;
    color: #222;
}

.title-row {
    border-bottom: 3px solid #333;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
}

.page-title {
    color: #003366;
    margin: 0;
    font-size: 2.5rem;
    font-weight: 700;
}

/* date pills */
.date-metadata {
    display: flex;
    gap: 1rem;
}

.date-pill {
    font-size: 0.9rem;
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    background-color: #f3f4f6;
    color: #6b7280;
    border: 1px solid #d1d5db;
}

.date-pill.active {
    background-color: #e0f2fe;
    color: #0369a1;
    border-color: #bae6fd;
}

.date-pill.complete {
    background-color: #dcfce3;
    color: #166534;
    border-color: #bbf7d0;
}

.checklist-items {
    display: flex;
    flex-direction: column;
}

.requirement-item {
    padding: 2rem 0;
    border-bottom: 1px solid #d1d5db;
}

.requirement-item:last-child {
    border-bottom: none;
}

.req-header {
    display: flex;
    align-items: flex-start;
    gap: 1.25rem;
    margin-bottom: 1.25rem;
}

.req-checkbox {
    width: 28px;
    height: 28px;
    margin-top: 4px;
    cursor: pointer;
    accent-color: #003366;
}

.req-titles {
    display: flex;
    flex-direction: column;
}

.req-name {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
    cursor: pointer;
    line-height: 1.2;
}

.req-desc {
    margin: 0.5rem 0 0 0;
    color: #4b5563;
    font-size: 1.15rem;
    line-height: 1.6;
}

.req-body {
    padding-left: 3rem;
}

.req-notes-input {
    width: 100%;
    padding: 1rem;
    border: 1px solid #9ca3af;
    border-radius: 6px;
    font-family: inherit;
    font-size: 1.15rem;
    line-height: 1.5;
    resize: vertical;
    background-color: transparent;
    transition:
        border-color 0.2s ease,
        box-shadow 0.2s ease;
}

.req-notes-input:focus {
    outline: none;
    border-color: #003366;
    box-shadow: 0 0 0 3px rgba(0, 51, 102, 0.1);
}

.status-state {
    padding: 2rem 0;
    color: #6b7280;
    font-size: 1.25rem;
    font-style: italic;
}

.status-state.error {
    color: #b91c1c;
    font-style: normal;
}
</style>
