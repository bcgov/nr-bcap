<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue';
import { debounce } from 'underscore';

import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Select from 'primevue/select';
import SelectButton from 'primevue/selectbutton';
import { useToast } from 'primevue/usetoast';

import {
    getUnlinkedContributors,
    issueRegistrationLink,
} from '@/bcap/components/pages/api.ts';

import type {
    RegistrationLinkResult,
    UnlinkedContributor,
} from '@/bcap/components/pages/api.ts';

const toast = useToast();

const MODE = { existing: 'existing', new: 'new' };
const modeOptions = [
    { label: 'Existing contributor', value: MODE.existing },
    { label: 'New contributor', value: MODE.new },
];

// Grouped form/page state (a single reactive object rather than many refs).
// New contributors are always individuals; the server defaults the type.
const state = reactive({
    mode: MODE.existing,
    contributors: [] as UnlinkedContributor[],
    contributorId: null as string | null,
    newContributor: {
        name: '',
        first_name: '',
        email: '',
    },
    submitting: false,
    result: null as RegistrationLinkResult | null,
});

// A generated link belongs to the previous target, so changing the selection
// or any new-contributor field makes it stale; clear it.
watch(
    () => [
        state.mode,
        state.contributorId,
        state.newContributor.name,
        state.newContributor.first_name,
        state.newContributor.email,
    ],
    () => {
        state.result = null;
    },
);

onMounted(async () => {
    try {
        state.contributors = await getUnlinkedContributors();
    } catch (error) {
        showError(error);
    }
});

const isNew = computed(() => state.mode === MODE.new);

const canSubmit = () => {
    if (!isNew.value) {
        return Boolean(state.contributorId);
    }
    const c = state.newContributor;
    // name holds the individual's last name.
    return Boolean(c.first_name && c.name && c.email);
};

const submit = async () => {
    state.submitting = true;
    state.result = null;
    try {
        const body = isNew.value
            ? { new_contributor: state.newContributor }
            : { contributor_id: state.contributorId! };
        state.result = await issueRegistrationLink(body);
    } catch (error) {
        showError(error);
    } finally {
        state.submitting = false;
    }
};

const copyLink = () => {
    if (state.result) {
        navigator.clipboard.writeText(state.result.signup_url);
        toast.add({
            severity: 'success',
            summary: 'Link copied',
            life: 2000,
        });
    }
};

const formattedExpires = () =>
    state.result ? new Date(state.result.expires).toLocaleString() : '';

// Server-side search: the list is capped, so filter against the API rather
// than only the options already loaded. Debounced so a fast typist doesn't
// fire a request per keystroke.
const searchContributors = debounce(async (event: { value: string }) => {
    try {
        state.contributors = await getUnlinkedContributors(event.value);
    } catch (error) {
        showError(error);
    }
}, 250);

function showError(error: unknown) {
    toast.add({
        severity: 'error',
        summary: 'Something went wrong',
        detail: error instanceof Error ? error.message : String(error),
        life: 5000,
    });
}
</script>

<template>
    <section class="invite">
        <div class="card">
            <header class="header">
                <i class="pi pi-user-plus header-icon" />
                <div>
                    <h1>Invite a Contributor</h1>
                    <p class="subtitle">
                        Send a single-use link. When the person signs in with
                        their BC government login, their account is
                        automatically linked to the Contributor record.
                    </p>
                </div>
            </header>

            <SelectButton
                v-model="state.mode"
                :options="modeOptions"
                option-label="label"
                option-value="value"
                :allow-empty="false"
            />

            <div
                v-if="!isNew"
                class="field-group"
            >
                <label class="label">Contributor</label>
                <Select
                    v-model="state.contributorId"
                    :options="state.contributors"
                    option-label="name"
                    option-value="id"
                    filter
                    :reset-filter-on-hide="false"
                    placeholder="Select a contributor"
                    class="field"
                    @filter="searchContributors"
                >
                    <template #option="{ option }">
                        <div class="option">
                            <span>{{ option.name }}</span>
                            <small
                                v-if="option.email"
                                class="hint"
                            >
                                {{ option.email }}
                            </small>
                        </div>
                    </template>
                </Select>
                <small class="hint">
                    Only contributors not yet linked to an account are shown.
                </small>
            </div>

            <template v-else>
                <div class="field-group">
                    <label class="label">
                        First name
                        <span class="req">*</span>
                    </label>
                    <InputText
                        v-model="state.newContributor.first_name"
                        class="field"
                    />
                </div>
                <div class="field-group">
                    <label class="label">
                        Last name
                        <span class="req">*</span>
                    </label>
                    <InputText
                        v-model="state.newContributor.name"
                        class="field"
                    />
                </div>
                <div class="field-group">
                    <label class="label">
                        Email
                        <span class="req">*</span>
                    </label>
                    <InputText
                        v-model="state.newContributor.email"
                        type="email"
                        class="field"
                    />
                </div>
            </template>

            <div class="actions">
                <Button
                    icon="pi pi-link"
                    label="Generate signup link"
                    :disabled="!canSubmit() || state.submitting"
                    :loading="state.submitting"
                    @click="submit"
                />
            </div>

            <div
                v-if="state.result"
                class="result"
            >
                <h2>Send this link to the contributor</h2>
                <div class="result-row">
                    <InputText
                        :model-value="state.result.signup_url"
                        readonly
                        class="field"
                    />
                    <Button
                        icon="pi pi-copy"
                        label="Copy"
                        severity="secondary"
                        @click="copyLink"
                    />
                </div>
                <small class="hint">Expires: {{ formattedExpires() }}</small>
            </div>
        </div>
    </section>
</template>

<style scoped>
.invite {
    display: flex;
    justify-content: center;
    padding: 2rem 1rem;
}
.card {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    width: 100%;
    max-width: 46rem;
    padding: 2rem;
    border-radius: 12px;
    background: #1f1f1f;
    color: #f1f1f1;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
    font-size: 1rem;
}
.header {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
}
.header-icon {
    font-size: 1.6rem;
    color: #4a9eed;
    margin-top: 0.2rem;
}
h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
}
.subtitle {
    margin: 0.4rem 0 0;
    color: #9aa0a6;
    line-height: 1.4;
    font-size: 1rem;
}
.field-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}
.label {
    font-weight: 700;
    text-align: left;
    align-self: flex-start;
    font-size: 1rem;
}
.req {
    color: #f87171;
    margin-left: 0.2rem;
}
.hint {
    color: #9aa0a6;
    font-size: 0.875rem;
}
.field-group .hint {
    margin-top: 0.25rem;
}
.field {
    width: 100%;
    font-size: 1rem;
}
/* The Select's focused state pulls the preset's primary (blue) into a thick
   ring; soften it to a thin neutral border. */
:deep(.p-select.p-focus) {
    border-color: #6b7280;
    box-shadow: none;
}
.actions {
    display: flex;
    justify-content: flex-end;
}
.result {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 1rem;
    border-radius: 8px;
    background: rgba(40, 120, 60, 0.25);
    border: 1px solid rgba(80, 200, 120, 0.4);
}
.result h2 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 700;
    color: #4ade80;
}
.result-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

/* The Select dropdown panel is teleported out of this component, so its
   options and filter input need global rules. */
:global(.p-select-option) {
    font-size: 1rem;
}
.option {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
}
:global(.p-select-filter) {
    font-size: 1rem;
}
</style>
