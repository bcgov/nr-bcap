<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const processId = computed(() => route.query.id as string | undefined);
const isEditing = computed(() => !!processId.value);
const isLoading = ref(false);
const originalData = ref<ArchesResourcePayload | null>(null);

interface ArchesResourcePayload {
    displayname?: string;
    resource: {
        'Requirement Identification'?: {
            'Requirement Name'?: string;
            'Is Template Requirement'?: {
                'Has Submission Requirement'?: string;
                [key: string]: unknown;
            };
            [key: string]: unknown;
        };
        'Sub Requirement'?: ArchesSubRequirement[];
        [key: string]: unknown;
    };
    [key: string]: unknown;
}

interface DraftRequirement {
    id: string;
    sortOrder: number;
    name: string;
    description: string;
}

interface ArchesNodeValue {
    '@value'?: string;
    [key: string]: unknown;
}

// Defines the Sub Requirement object
interface ArchesSubRequirement {
    'Sub Requirement Name'?: ArchesNodeValue | string;
    'Sub Requirement Description'?: ArchesNodeValue | string;
    Description?: ArchesNodeValue | string;
    [key: string]: unknown;
}

const requirementTitle = ref('');
const requiresSubmission = ref(false);

// Start with one empty requirement by default
const requirements = ref<DraftRequirement[]>([
    {
        id: `temp-${Math.random().toString(36).slice(2, 9)}`,
        sortOrder: 1,
        name: '',
        description: '',
    },
]);

const isSaving = ref(false);
const saveMessage = ref('');

onMounted(async () => {
    if (isEditing.value) {
        isLoading.value = true;
        try {
            const apiUrl = `/bcap/resources/${processId.value}?format=json`;
            const response = await fetch(apiUrl);

            if (!response.ok) throw new Error('Failed to fetch data');

            const data = await response.json();
            originalData.value = data;
            requirementTitle.value = data.displayname || '';
            requiresSubmission.value =
                data.resource?.['Requirement Identification']?.[
                    'Is Template Requirement'
                ] === 'True';

            const subRequirements = data.resource?.['Sub Requirement'];

            if (Array.isArray(subRequirements) && subRequirements.length > 0) {
                requirements.value = subRequirements.map(
                    (subItem: ArchesSubRequirement, index: number) => {
                        const nameData = subItem['Sub Requirement Name'];
                        const reqName =
                            nameData &&
                            typeof nameData === 'object' &&
                            '@value' in nameData
                                ? String(nameData['@value'])
                                : String(nameData || '');

                        const descData =
                            subItem['Sub Requirement Description'] ||
                            subItem['Description'];
                        const reqDesc =
                            descData &&
                            typeof descData === 'object' &&
                            '@value' in descData
                                ? String(descData['@value'])
                                : String(descData || '');

                        return {
                            id: `temp-${Math.random().toString(36).slice(2, 9)}`,
                            sortOrder: index + 1,
                            name: reqName,
                            description: reqDesc,
                        };
                    },
                );
            }
        } catch (error) {
            console.error('Error loading process requirement:', error);
            saveMessage.value = 'Error loading existing checklist data.';
        } finally {
            isLoading.value = false;
        }
    }
});

// drag and drop logic
const draggedIndex = ref<number | null>(null);

const onDragStart = (index: number, event: DragEvent) => {
    draggedIndex.value = index;
    if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
    }
};

const onDrop = (dropIndex: number) => {
    if (draggedIndex.value === null || draggedIndex.value === dropIndex) return;

    const draggedItem = requirements.value.splice(draggedIndex.value, 1)[0];
    requirements.value.splice(dropIndex, 0, draggedItem);

    requirements.value.forEach((req, idx) => {
        req.sortOrder = idx + 1;
    });

    draggedIndex.value = null;
};

const onDragEnd = () => {
    draggedIndex.value = null;
};

// List management
const addRequirement = () => {
    requirements.value.push({
        id: `temp-${Math.random().toString(36).slice(2, 9)}`,
        sortOrder: requirements.value.length + 1,
        name: '',
        description: '',
    });
};

const removeRequirement = (index: number) => {
    requirements.value.splice(index, 1);
    requirements.value.forEach((req, idx) => {
        req.sortOrder = idx + 1;
    });
};

const saveRequirements = async () => {
    isSaving.value = true;
    saveMessage.value = '';

    try {
        const payload = JSON.parse(
            JSON.stringify(originalData.value),
        ) as ArchesResourcePayload;

        payload.displayname = requirementTitle.value;

        payload.resource['Requirement Identification'] ||= {};
        payload.resource['Requirement Identification'][
            'Is Template Requirement'
        ] ||= {};
        payload.resource['Requirement Identification']['Requirement Name'] =
            requirementTitle.value;
        payload.resource['Requirement Identification'][
            'Is Template Requirement'
        ]['Has Submission Requirement'] = requiresSubmission.value
            ? 'True'
            : 'False';

        payload.resource['Sub Requirement'] = requirements.value.map((req) => ({
            'Sub Requirement Name': {
                '@value': req.name,
                'Sub Requirement Description': req.description,
                'Sub Requirement Sort Order': String(req.sortOrder),
                'Sub Requirement Mandatory': '',
                'Sub Requirement Assessment': {
                    'Sub Requirement Assessment Notes': '',
                    'Sub Requirement Satisfied': '',
                },
            },
        }));

        console.log('Sending Mutated Payload to Backend:', payload);

        // Backend call

        saveMessage.value = 'Checklist updated successfully!';
    } catch (error) {
        console.error('Save error:', error);
        saveMessage.value = 'Error saving checklist to backend.';
    } finally {
        isSaving.value = false;
        setTimeout(() => {
            saveMessage.value = '';
        }, 3000);
    }
};
</script>

<template>
    <div class="checklist-container">
        <div class="title-row">
            <h2 class="page-title">
                {{ isEditing ? 'Edit' : 'Create' }} Process Requirement
            </h2>
            <button
                class="btn-primary"
                :disabled="isSaving || isLoading"
                @click="saveRequirements"
            >
                {{ isSaving ? 'Saving...' : 'Save Checklist' }}
            </button>
        </div>

        <div
            v-if="saveMessage"
            class="status-state"
            :class="{ error: saveMessage.includes('Error') }"
        >
            <p>{{ saveMessage }}</p>
        </div>

        <div
            v-if="isLoading"
            style="text-align: center; padding: 3rem"
        >
            <p>Loading requirement data...</p>
        </div>

        <div v-else>
            <div class="main-settings">
                <input
                    v-model="requirementTitle"
                    type="text"
                    class="req-title-input"
                    placeholder="Requirement List Title"
                />

                <div class="checkbox-group">
                    <input
                        id="require-submission"
                        v-model="requiresSubmission"
                        type="checkbox"
                        class="req-checkbox"
                    />
                    <label for="require-submission">Require a submission</label>
                </div>
            </div>
            <br />

            <div class="checklist-items">
                <div
                    v-for="(req, index) in requirements"
                    :key="req.id"
                    class="requirement-item"
                    draggable="true"
                    :class="{ 'is-dragging': draggedIndex === index }"
                    @dragstart="onDragStart(index, $event)"
                    @dragover.prevent
                    @dragenter.prevent
                    @drop="onDrop(index)"
                    @dragend="onDragEnd"
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
                                <label :for="'name-' + req.id">
                                    Step {{ req.sortOrder }} Title
                                </label>
                                <input
                                    :id="'name-' + req.id"
                                    v-model="req.name"
                                    type="text"
                                    class="req-title-input"
                                    placeholder="E.g. 'Submit Application'"
                                />
                            </div>

                            <div class="input-group">
                                <label :for="'desc-' + req.id">
                                    Description / Instructions
                                </label>
                                <textarea
                                    :id="'desc-' + req.id"
                                    v-model="req.description"
                                    class="req-notes-input"
                                    rows="2"
                                    placeholder="Add specific considerations or instructions..."
                                ></textarea>
                            </div>
                        </div>

                        <button
                            v-if="requirements.length > 1"
                            class="btn-delete"
                            title="Remove Step"
                            @click="removeRequirement(index)"
                        >
                            &times;
                        </button>
                    </div>
                </div>
            </div>

            <div class="action-row">
                <button
                    class="btn-secondary"
                    @click="addRequirement"
                >
                    + Add Another Step
                </button>
            </div>
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

/* Updated main-settings padding and borders */
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

.checkbox-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.checkbox-group label {
    font-size: 1.1rem;
    font-weight: 600;
    color: #4b5563;
    cursor: pointer;
}

.req-checkbox {
    width: 24px;
    height: 24px;
    cursor: pointer;
    accent-color: #003366;
}

.checklist-items {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

/* Card Styling & Dragging */
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

/* Drag Handle */
.drag-handle {
    cursor: grab;
    font-size: 2.5rem;
    color: #9ca3af;
    user-select: none;
}

.drag-handle:active {
    cursor: grabbing;
}

/* Inputs */
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

/* Buttons */
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
