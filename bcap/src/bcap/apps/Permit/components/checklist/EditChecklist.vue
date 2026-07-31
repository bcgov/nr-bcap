<script setup lang="ts">
import { reactive, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import arches from 'arches';
import Button from 'primevue/button';
import { apiFetchJson } from '@/bcap/api.ts';
import { saveChecklist } from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { readString } from '@/bcap/util.ts';
import { useDragReorder } from '@/bcap/apps/Permit/composables/useDragReorder.ts';
import type { ProcessRequirement } from '@/bcap/client/types.gen.ts';
import PermitBreadcrumbs from '@/bcap/apps/Permit/components/common/PermitBreadcrumbs.vue';
import PermitHeaderBand from '@/bcap/apps/Permit/components/filing-summary/PermitHeaderBand.vue';
import { usePermitHeaderStore } from '@/bcap/stores/permitHeader.ts';
import { permitCrumbs } from '@/bcap/apps/Permit/components/common/permitCrumbs.ts';

const route = useRoute();
const processId = computed(() => route.query.id as string | undefined);
const isEditing = computed(() => !!processId.value);

const crumbs = computed(() =>
    permitCrumbs(
        route.query.permit,
        route.query.staff,
        state.requirementTitle || 'Edit Checklist',
    ),
);

const backLink = computed(() => crumbs.value[0]?.to ?? '');

interface StepItem {
    // Present for steps loaded from the resource; absent for newly added ones,
    // so the save creates their tiles.
    tileid?: string;
    id: string;
    sortOrder: number;
    name: string;
    description: string;
}

const tempId = () => `temp-${Math.random().toString(36).slice(2, 9)}`;
const blankStep = (): StepItem => ({
    id: tempId(),
    sortOrder: 1,
    name: '',
    description: '',
});

const state = reactive({
    isLoading: false,
    isSaving: false,
    saveMessage: '',
    requirementTitle: '',
    steps: [blankStep()] as StepItem[],
});

const reorder = useDragReorder();
const STEP_GROUP = 'steps';

// Renumber sortOrder to match list position, after a reorder or a removal.
const resequence = () => {
    state.steps.forEach((step, index) => {
        step.sortOrder = index + 1;
    });
};

// A blank step name would create an unnamed tile, so block the save until every
// step has a title.
const missingStepName = computed(() =>
    state.steps.some((step) => step.name.trim() === ''),
);
const canSave = computed(
    () => !state.isSaving && !state.isLoading && !missingStepName.value,
);

// The aliased resource API returns the same shape for template and non-template
// requirements, so one load/save path covers both. withSpinner is off for the
// post-save refresh so the list stays put instead of flashing the loader.
const loadRequirement = async (withSpinner = true) => {
    if (!isEditing.value) return;
    if (withSpinner) state.isLoading = true;
    try {
        const url = arches.urls.api_resource(
            GraphSlug.ProcessRequirement,
            processId.value!,
        );
        const resource = await apiFetchJson<ProcessRequirement>(url);
        const data = resource.aliased_data;

        state.requirementTitle = readString(
            data?.requirement_identification?.aliased_data?.requirement_name,
        );

        const subs =
            data?.requirement_data?.aliased_data?.sub_requirement_n1 ?? [];
        if (subs.length) {
            state.steps = [...subs]
                .map((sub) => ({
                    tileid: sub.tileid ?? undefined,
                    id: sub.tileid ?? tempId(),
                    sortOrder:
                        sub.aliased_data?.checklist_item_sort_order
                            ?.node_value ?? 0,
                    name: readString(sub.aliased_data?.checklist_item_name),
                    description: readString(
                        sub.aliased_data?.checklist_item_description,
                    ),
                }))
                .sort((a, b) => a.sortOrder - b.sortOrder);
            resequence();
        }
    } catch (error) {
        console.error('Error loading process requirement:', error);
        state.saveMessage = 'Error loading existing checklist data.';
    } finally {
        if (withSpinner) state.isLoading = false;
    }
};

const headerStore = usePermitHeaderStore();
const permitId = computed(() => String(route.query.permit ?? ''));
const permitHeader = computed(() => headerStore.state.header);

onMounted(() => {
    loadRequirement();
    headerStore.load(permitId.value);
});

const addStep = () => {
    state.steps.push({ ...blankStep(), sortOrder: state.steps.length + 1 });
};

const removeStep = (index: number) => {
    // Removed steps just drop from the list; the backend deletes any that were
    // persisted when the list is saved.
    state.steps.splice(index, 1);
    resequence();
};

const saveRequirements = async () => {
    if (!processId.value || !canSave.value) return;
    state.isSaving = true;
    state.saveMessage = '';
    try {
        await saveChecklist(
            processId.value,
            state.requirementTitle,
            state.steps.map((step) => ({
                tileid: step.tileid,
                name: step.name,
                description: step.description,
            })),
        );
        // Refresh (no spinner) so newly created steps pick up their tile ids; a
        // re-save without the ids would otherwise create duplicates.
        await loadRequirement(false);
        state.saveMessage = 'Checklist updated successfully!';
    } catch (error) {
        console.error('Save error:', error);
        state.saveMessage = 'Error saving checklist.';
    } finally {
        state.isSaving = false;
        setTimeout(() => {
            state.saveMessage = '';
        }, 3000);
    }
};
</script>

<template>
    <PermitHeaderBand
        v-if="permitHeader"
        :header="permitHeader"
    />
    <div class="checklist-container">
        <PermitBreadcrumbs
            v-if="crumbs.length"
            :crumbs="crumbs"
            class="page-crumbs"
        />
        <div class="title-row">
            <h2 class="page-title">
                {{ isEditing ? 'Edit' : 'Create' }} Process Requirement
            </h2>
            <Button
                class="btn-primary"
                :disabled="!canSave"
                :label="state.isSaving ? 'Saving...' : 'Save Checklist'"
                @click="saveRequirements"
            />
        </div>

        <p
            v-if="missingStepName"
            class="validation-hint"
        >
            Give every step a title before saving.
        </p>

        <div
            v-if="state.saveMessage"
            class="status-state"
            :class="{ error: state.saveMessage.includes('Error') }"
        >
            <p>{{ state.saveMessage }}</p>
        </div>

        <div
            v-if="state.isLoading"
            style="text-align: center; padding: 3rem"
        >
            <p>Loading requirement data...</p>
        </div>

        <div v-else>
            <div class="main-settings">
                <input
                    v-model="state.requirementTitle"
                    type="text"
                    class="req-title-input"
                    placeholder="Requirement List Title"
                />
            </div>
            <br />

            <div class="checklist-items">
                <div
                    v-for="(step, index) in state.steps"
                    :key="step.id"
                    class="requirement-item"
                    draggable="true"
                    :class="{
                        'is-dragging': reorder.isDragging(STEP_GROUP, index),
                    }"
                    @dragstart="reorder.start(STEP_GROUP, index)"
                    @dragover.prevent
                    @dragenter.prevent="reorder.enter(STEP_GROUP, index)"
                    @drop="
                        reorder.drop(STEP_GROUP, index, state.steps, resequence)
                    "
                    @dragend="reorder.end"
                >
                    <div class="req-header">
                        <div
                            class="drag-handle"
                            title="Drag to reorder"
                        >
                            &#x2630;
                        </div>

                        <div class="req-inputs">
                            <div class="input-group">
                                <label :for="'name-' + step.id">
                                    Step {{ step.sortOrder }} Title
                                </label>
                                <input
                                    :id="'name-' + step.id"
                                    v-model="step.name"
                                    type="text"
                                    class="req-title-input"
                                    :class="{
                                        'input-error': !step.name.trim(),
                                    }"
                                    placeholder="E.g. 'Submit Application'"
                                />
                            </div>

                            <div class="input-group">
                                <label :for="'desc-' + step.id">
                                    Description / Instructions
                                </label>
                                <textarea
                                    :id="'desc-' + step.id"
                                    v-model="step.description"
                                    class="req-notes-input"
                                    rows="2"
                                    placeholder="Add specific considerations or instructions..."
                                ></textarea>
                            </div>
                        </div>

                        <Button
                            v-if="state.steps.length > 1"
                            class="btn-delete"
                            title="Remove Step"
                            @click="removeStep(index)"
                        >
                            &times;
                        </Button>
                    </div>
                </div>
            </div>

            <div class="action-row">
                <Button
                    class="btn-secondary"
                    label="+ Add Another Step"
                    @click="addStep"
                />
            </div>
        </div>

        <div class="actions-bar">
            <RouterLink
                v-if="backLink"
                class="btn-secondary back-btn"
                :to="backLink"
            >
                <i class="fa-solid fa-arrow-left"></i>
                Back to Filing Summary
            </RouterLink>
        </div>
    </div>
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

.page-crumbs {
    margin-bottom: 1rem;
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

.main-settings {
    background: #ffffff;
    padding: 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
}

.checklist-items {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.requirement-item {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 1.5rem;
    transition:
        transform 0.2s ease,
        box-shadow 0.2s ease;
}

.requirement-item.is-dragging {
    opacity: 0.4;
    border: 2px dashed #003366;
    background: #f8fafc;
}

.req-header {
    display: flex;
    align-items: flex-start;
    gap: 1.25rem;
}

.drag-handle {
    cursor: grab;
    font-size: 2.5rem;
    color: #9ca3af;
    user-select: none;
}

.drag-handle:active {
    cursor: grabbing;
}

.req-inputs {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.input-group label {
    display: block;
    font-size: 0.9rem;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 0.25rem;
}

.req-title-input,
.req-notes-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #9ca3af;
    border-radius: 6px;
    font-family: inherit;
    font-size: 1.1rem;
    background-color: transparent;
    transition:
        border-color 0.2s ease,
        box-shadow 0.2s ease;
}

.req-title-input {
    font-weight: 600;
    color: #111827;
}

.req-notes-input {
    resize: vertical;
    line-height: 1.5;
}

.req-title-input:focus,
.req-notes-input:focus {
    outline: none;
    border-color: #003366;
    box-shadow: 0 0 0 3px rgba(0, 51, 102, 0.1);
}

.input-error {
    border-color: #ef4444;
}

.validation-hint {
    margin: -0.5rem 0 1rem;
    color: #b91c1c;
    font-size: 0.9rem;
    font-weight: 600;
}

.btn-primary,
.btn-secondary {
    padding: 0.75rem 1.5rem;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 1rem;
    border: none;
    transition: background-color 0.2s;
}

.btn-primary {
    background-color: #003366;
    color: white;
}

.actions-bar {
    display: flex;
    margin-top: 2rem;
}

.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    border: 1.5px solid #003366;
    color: #003366;
    background-color: #ffffff;
    text-decoration: none;
}

.back-btn:hover {
    background-color: #f3f4f6;
    text-decoration: none;
}

.btn-primary:hover {
    background-color: #002244;
}

.btn-primary:disabled {
    background-color: #9ca3af;
    cursor: not-allowed;
}

.btn-secondary {
    background-color: #f3f4f6;
    color: #374151;
    border: 1px solid #d1d5db;
}

.btn-secondary:hover {
    background-color: #e5e7eb;
}

.btn-delete {
    background: none;
    border: none;
    color: #ef4444;
    font-size: 3rem;
    cursor: pointer;
    line-height: 1;
    padding: 0 0.5rem;
}

.btn-delete:hover {
    color: #b91c1c;
}

.action-row {
    margin-top: 2rem;
    display: flex;
    justify-content: center;
}

.status-state {
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 6px;
    background-color: #dcfce3;
    color: #166534;
}

.status-state.error {
    background-color: #fee2e2;
    color: #b91c1c;
}
</style>
