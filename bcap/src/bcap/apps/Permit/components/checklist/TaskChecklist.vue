<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import Button from 'primevue/button';
import {
    getProcessRequirementData,
    patchProcessRequirement,
} from '@/bcap/apps/Permit/api.ts';
import PermitBreadcrumbs from '@/bcap/apps/Permit/components/common/PermitBreadcrumbs.vue';
import PermitHeaderBand from '@/bcap/apps/Permit/components/filing-summary/PermitHeaderBand.vue';
import { usePermitHeaderStore } from '@/bcap/stores/permitHeader.ts';
import { permitCrumbs } from '@/bcap/apps/Permit/components/common/permitCrumbs.ts';
import type { ProcessRequirement } from '@/bcap/client/types.gen.ts';
import { zPatchedProcessRequirement } from '@/bcap/client/zod.gen.ts';

const route = useRoute();
const idFromUrl = route.query.id;
const isLoading = ref(true);
const isSaving = ref(false);
const errorMessage = ref('');

const requirementData = ref<ProcessRequirement | null>(null);

const subRequirements = computed(
    () =>
        requirementData.value?.aliased_data?.requirement_data?.aliased_data
            ?.sub_requirement_n1 || [],
);

const requirementName = computed(
    () => requirementData.value?.descriptors?.en?.name ?? '',
);

const crumbs = computed(() =>
    permitCrumbs(
        route.query.permit,
        route.query.staff,
        requirementName.value || 'Checklist',
    ),
);

const backLink = computed(() => crumbs.value[0]?.to ?? '');

// Requirement-level status + notes (the assessment tile).
const assessment = computed(
    () => requirementData.value?.aliased_data?.sub_requirement_assessment_n1,
);

// String nodes carry a localized value ({ en: { value } }), so binding
// node_value directly renders "[object Object]". These read/write the inner
// string instead. Used by every notes textarea (sub-requirement + assessment).
type LocalizedString = { en?: { value?: string } };

const readText = (node?: { node_value?: unknown } | null): string => {
    const value = node?.node_value as
        LocalizedString | string | null | undefined;
    if (value == null) return '';
    return typeof value === 'string' ? value : (value.en?.value ?? '');
};

const writeText = (
    node: { node_value?: unknown } | null | undefined,
    text: string,
) => {
    if (node) {
        node.node_value = { en: { value: text, direction: 'ltr' } };
    }
};

// Manual save: snapshot the last-saved state so we can detect edits and revert.
const savedSnapshot = ref('');
const isDirty = computed(
    () =>
        !!requirementData.value &&
        savedSnapshot.value !== JSON.stringify(requirementData.value),
);
const markPristine = () => {
    savedSnapshot.value = JSON.stringify(requirementData.value);
};
const undoChanges = () => {
    if (savedSnapshot.value) {
        requirementData.value = JSON.parse(savedSnapshot.value);
    }
};

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
        markPristine();
    } catch (error) {
        console.error('Failed to load sub-requirements:', error);
        errorMessage.value = 'Failed to load checklist data. Please try again.';
    } finally {
        isLoading.value = false;
    }
};

const headerStore = usePermitHeaderStore();
const permitId = computed(() => String(route.query.permit ?? ''));
const permitHeader = computed(() => headerStore.state.header);

onMounted(() => {
    loadData();
    headerStore.load(permitId.value);
});

// Derive start/completion dates from the checklist. Run on Save (not on each
// toggle) so the dates only change when the user commits.
const applyDerivedDates = () => {
    if (!requirementData.value) return;
    const today = new Date().toISOString().split('T')[0];
    const duration =
        requirementData.value.aliased_data?.requirement_execution_duration
            ?.aliased_data;
    if (!duration) return;
    const subs = subRequirements.value;
    const isChecked = (req: (typeof subs)[number]) =>
        req.aliased_data?.checklist_item_completed?.node_value;
    const anyChecked = subs.some(isChecked);
    const allChecked = subs.length > 0 && subs.every(isChecked);

    const start = duration.requirement_process_start_date;
    const completion = duration.requirement_process_completion_date;
    if (anyChecked && start && !start.node_value) {
        start.node_value = today;
    }
    if (allChecked && completion && !completion.node_value) {
        completion.node_value = today;
    } else if (!allChecked && completion && completion.node_value) {
        completion.node_value = null;
    }
};

const saveChanges = async () => {
    if (!requirementData.value || isSaving.value) return;
    applyDerivedDates();
    isSaving.value = true;
    const body = { aliased_data: requirementData.value.aliased_data };
    // Soft-validate against the writable schema: warn on a mismatch, never block.
    const validation = zPatchedProcessRequirement.safeParse(body);
    if (!validation.success) {
        console.warn(
            'Process requirement patch body failed validation:',
            validation.error,
        );
    }
    try {
        await patchProcessRequirement(
            idFromUrl as string,
            requirementData.value.aliased_data,
        );
        markPristine();
    } catch (error) {
        console.error('Save error:', error);
    } finally {
        isSaving.value = false;
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
                {{ requirementName || 'Process Requirement' }}
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
                            req.aliased_data!.checklist_item_completed!
                                .node_value
                        "
                        type="checkbox"
                        class="req-checkbox"
                    />
                    <div class="req-titles">
                        <label
                            :for="'check-' + (req.tileid ?? '')"
                            class="req-name"
                        >
                            {{
                                req.aliased_data?.checklist_item_name
                                    ?.display_value
                            }}
                        </label>
                        <p
                            v-if="
                                req.aliased_data?.checklist_item_description
                                    ?.display_value
                            "
                            class="req-desc"
                        >
                            {{
                                req.aliased_data?.checklist_item_description
                                    ?.display_value
                            }}
                        </p>
                    </div>
                </div>

                <div class="req-body">
                    <textarea
                        :id="'notes-' + req.tileid"
                        :value="
                            readText(
                                req.aliased_data
                                    ?.checklist_item_assessment_notes,
                            )
                        "
                        class="req-notes-input"
                        rows="2"
                        placeholder="Add assessment notes..."
                        @input="
                            writeText(
                                req.aliased_data
                                    ?.checklist_item_assessment_notes,
                                ($event.target as HTMLTextAreaElement).value,
                            )
                        "
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

        <div
            v-if="!isLoading && !errorMessage && assessment"
            class="requirement-summary"
        >
            <div class="subtitle-row">
                <h3 class="page-subtitle">Requirement Status & Summary</h3>
            </div>

            <div class="req-header">
                <input
                    id="requirement_satisfied"
                    v-model="
                        assessment!.aliased_data!.requirement_status!.node_value
                    "
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
                    :value="
                        readText(assessment?.aliased_data?.assessment_notes)
                    "
                    class="req-notes-input"
                    rows="8"
                    placeholder="Add assessment summary and notes..."
                    @input="
                        writeText(
                            assessment?.aliased_data?.assessment_notes,
                            ($event.target as HTMLTextAreaElement).value,
                        )
                    "
                ></textarea>
            </div>
        </div>

        <div class="actions-bar">
            <RouterLink
                v-if="backLink"
                class="action-btn back-btn"
                :to="backLink"
            >
                <i class="fa-solid fa-arrow-left"></i>
                Back to Filing Summary
            </RouterLink>
            <Button
                v-if="isDirty"
                type="button"
                class="action-btn undo-btn"
                icon="fa-solid fa-rotate-left"
                label="Undo"
                :disabled="isSaving"
                @click="undoChanges"
            />
            <Button
                type="button"
                class="action-btn save-btn"
                :icon="
                    isSaving
                        ? 'fa-solid fa-spinner fa-spin'
                        : 'fa-solid fa-floppy-disk'
                "
                :label="isSaving ? 'Saving…' : 'Save'"
                :disabled="isSaving"
                @click="saveChanges"
            />
        </div>
    </div>
</template>

<style scoped>
.checklist-container {
    max-width: 800px;
    margin: 0 auto 50px auto;
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

.notes-header {
    margin: 0 0 0.75rem 0;
    font-size: 1.2rem;
    font-weight: 600;
    color: #374151;
}

.actions-bar {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 2rem;
}

.action-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.7rem 1.6rem;
    border-radius: 999px;
    font-family: inherit;
    font-size: 1.2rem;
    font-weight: 600;
    line-height: 1;
    cursor: pointer;
    border: 1.5px solid transparent;
    transition:
        background-color 0.18s ease,
        border-color 0.18s ease,
        box-shadow 0.18s ease,
        transform 0.05s ease;
}

.action-btn:active {
    transform: translateY(1px);
}

.action-btn:disabled {
    opacity: 0.65;
    cursor: not-allowed;
    box-shadow: none;
}

.action-btn i {
    font-size: 1rem;
}

.save-btn {
    background-color: #003366;
    color: #ffffff;
    box-shadow: 0 2px 6px rgba(0, 51, 102, 0.25);
}

.back-btn {
    margin-right: auto;
    background-color: #ffffff;
    border-color: #003366;
    color: #003366;
    text-decoration: none;
}

.back-btn:hover {
    background-color: #f3f4f6;
    text-decoration: none;
}

.save-btn:hover {
    background-color: #00264d;
    box-shadow: 0 4px 10px rgba(0, 51, 102, 0.3);
}

.undo-btn {
    background-color: #ffffff;
    color: #374151;
    border-color: #d1d5db;
}

.undo-btn:hover {
    background-color: #f9fafb;
    border-color: #9ca3af;
    color: #111827;
}

.requirement-satisfied {
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 2px solid #333;
}

.satisfied-header {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    margin-bottom: 1.25rem;
    cursor: pointer;
}

.satisfied-label {
    font-size: 1.5rem;
    font-weight: 600;
    color: #111827;
}

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
    flex-shrink: 0;
    cursor: pointer;
    accent-color: #003366;
    /* center the 18px box on the first line of the 1.5rem/1.2 label REMOVE THIS LATER*/
    margin-top: calc((1.5rem * 1.2 - 18px) / 2);
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
    /* line the notes box up with the label text (checkbox width + header gap) */
    padding-left: calc(18px + 1.25rem);
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
