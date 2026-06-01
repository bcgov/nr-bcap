<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import arches from 'arches';
import { getProcessRequirementData } from '@/bcap/components/pages/api.ts';
import type { PermitRequirementSchema } from '@/bcap/schema/PermitRequirementSchema.ts';
import Checkbox from 'primevue/checkbox';

interface DateTile {
    tileid: string | null;
    nodegroup_id: string;
    data: Record<string, unknown>;
}

const route = useRoute();
const idFromUrl = route.query.id;
const dateTile = ref<DateTile | null>(null);
const isLoading = ref(true);
const errorMessage = ref('');

const requirementData = ref<PermitRequirementSchema | null>(null);

const subRequirements = computed(
    () => requirementData.value?.aliased_data?.sub_requirement || [],
);

const startDate = computed(() => {
    return requirementData.value?.aliased_data?.requirement_execution_duration
        ?.aliased_data?.requirement_process_start_date?.node_value;
});
const completedDate = computed(() => {
    return requirementData.value?.aliased_data?.requirement_execution_duration
        ?.aliased_data?.requirement_process_completion_date?.node_value;
});

const loadData = async () => {
    if (!idFromUrl) {
        errorMessage.value = 'No resource ID provided in the URL.';
        isLoading.value = false;
        return;
    }

    try {
        requirementData.value = await getProcessRequirementData(
            idFromUrl as string,
        );
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
    const today = new Date().toISOString().split('T')[0];
    const anyChecked = subRequirements.value.some(
        (req) => req.aliased_data.sub_requirement_satisfied.node_value,
    );
    const allChecked = subRequirements.value.every(
        (req) => req.aliased_data.sub_requirement_satisfied.node_value,
    );

    console.log('All checked:', allChecked);
    console.log('Any checked:', anyChecked);

    if (anyChecked && requirementData.value && !startDate.value) {
        requirementData.value.aliased_data.requirement_execution_duration.aliased_data.requirement_process_start_date.node_value =
            today;
    }

    if (allChecked && requirementData.value && !completedDate.value) {
        requirementData.value.aliased_data.requirement_execution_duration.aliased_data.requirement_process_completion_date.node_value =
            today;
    } else if (!allChecked && requirementData.value && completedDate.value) {
        requirementData.value.aliased_data.requirement_execution_duration.aliased_data.requirement_process_completion_date.node_value =
            null;
    }

    saveChanges();
};

const saveChanges = async () => {
    try {
        const response = await fetch(
            arches.urls.api_process_requirements(idFromUrl),
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
            <h2 class="page-title">
                {{
                    requirementData?.aliased_data?.requirement_identification
                        ?.aliased_data?.requirement_name?.display_value
                }}
            </h2>

            <div class="date-metadata">
                <span
                    class="date-pill"
                    :class="{ active: startDate }"
                >
                    <strong>Started:</strong>
                    {{ startDate || 'Pending' }}
                </span>
                <span
                    class="date-pill"
                    :class="{ complete: completedDate }"
                >
                    <strong>Completed:</strong>
                    {{ completedDate || 'Pending' }}
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
            <div class="subtitle-row">
                <h3 class="page-subtitle">Requirement Tasks</h3>
            </div>
            <div
                v-for="req in subRequirements"
                :key="req.tileid ?? ''"
                class="requirement-item"
            >
                <div class="req-header">
                    <input
                        :id="'check-' + (req.tileid ?? '')"
                        v-model="
                            req.aliased_data.sub_requirement_satisfied
                                .node_value
                        "
                        type="checkbox"
                        class="req-checkbox"
                        @change="handleCheckboxChange"
                    />
                    <div class="req-titles">
                        <label
                            :for="'check-' + (req.tileid ?? '')"
                            class="req-name"
                        >
                            {{
                                req.aliased_data.sub_requirement_name
                                    ?.display_value
                            }}
                        </label>
                        <p class="req-desc">
                            {{
                                req.aliased_data.sub_requirement_description
                                    ?.display_value
                            }}
                        </p>
                    </div>
                </div>

                <div class="req-body">
                    <textarea
                        :id="'notes-' + req.tileid"
                        v-model="
                            req.aliased_data.sub_requirement_assessment_notes
                                .node_value as string
                        "
                        class="req-notes-input"
                        rows="2"
                        placeholder="Add assessment notes..."
                        @change="saveChanges"
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

        <div class="subtitle-row">
            <h3 class="page-subtitle">Requirement Status & Summary</h3>
        </div>

        <div class="req-header">
            <input
                id="requirement_satisfied"
                type="checkbox"
                class="req-checkbox"
            />
            <div class="req-titles">
                <label
                    for="requirement_satisfied"
                    class="req-name"
                >
                    Requirement Review Completed
                </label>
            </div>
        </div>

        <div class="req-body">
            <textarea
                id="requirement-notes"
                class="req-notes-input"
                rows="8"
                placeholder="Add assessment summary and notes..."
                @change="saveChanges"
            ></textarea>
        </div>
        <div style="margin-bottom: 10rem"></div>
    </div>
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

.subtitle-row {
    border-bottom: 1px solid #333;
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
.page-subtitle {
    color: #003366;
    margin: 0;
    font-size: 1.75rem;
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
    width: 18px;
    height: 18px;
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
