<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue';
import { debounce } from 'underscore';

import Button from 'primevue/button';
import Checkbox from 'primevue/checkbox';
import InputText from 'primevue/inputtext';
import MultiSelect from 'primevue/multiselect';
import Select from 'primevue/select';
import SelectButton from 'primevue/selectbutton';
import { useToast } from 'primevue/usetoast';

import {
    getAssignableGroups,
    getUnlinkedContributors,
    issueRegistrationLink,
} from '@/bcap/apps/Admin/api.ts';

import type {
    ContributorSummary,
    RegistrationLinkResponse,
} from '@/bcap/client/types.gen.ts';

const toast = useToast();

const MODE = { existing: 'existing', new: 'new' };
const modeOptions = [
    { label: 'Existing contributor', value: MODE.existing },
    { label: 'New contributor', value: MODE.new },
];

// New contributors are always individuals; the server defaults the type.
const state = reactive({
    mode: MODE.existing,
    contributors: [] as ContributorSummary[],
    contributorId: null as string | null,
    newContributor: {
        name: '',
        first_name: '',
        email: '',
        phone: '',
    },
    availableGroups: [] as string[],
    groups: [] as string[],
    externalApplicant: false,
    submitting: false,
    result: null as RegistrationLinkResponse | null,
    error: null as string | null,
});

const EXTERNAL_APPLICANT_GROUP = 'Submitter';

watch(
    () => [
        state.mode,
        state.contributorId,
        state.newContributor.name,
        state.newContributor.first_name,
        state.newContributor.email,
        state.newContributor.phone,
        state.groups,
        state.externalApplicant,
    ],
    () => {
        state.result = null;
        state.error = null;
    },
    { deep: true },
);

watch(
    () => state.externalApplicant,
    (isExternal) => {
        state.groups = isExternal ? [EXTERNAL_APPLICANT_GROUP] : [];
    },
);

onMounted(async () => {
    try {
        [state.contributors, state.availableGroups] = await Promise.all([
            getUnlinkedContributors(),
            getAssignableGroups(),
        ]);
    } catch (error) {
        showError(error);
    }
});

const isNew = computed(() => state.mode === MODE.new);

// Submitter isn't a manual choice -- it's applied only via the External
// Applicant checkbox. Keep it out of the picker normally, but include it while
// the box is checked so its chip renders (PrimeVue only shows chips for values
// present in the options).
const groupOptions = computed(() =>
    state.externalApplicant
        ? [EXTERNAL_APPLICANT_GROUP]
        : state.availableGroups.filter((g) => g !== EXTERNAL_APPLICANT_GROUP),
);

const canSubmit = computed(() => {
    if (!state.groups.length) {
        return false;
    }
    if (!isNew.value) {
        return Boolean(state.contributorId);
    }
    const c = state.newContributor;
    // name holds the individual's last name.
    return Boolean(c.first_name && c.name && c.email);
});

const submit = async () => {
    state.submitting = true;
    state.result = null;
    state.error = null;
    try {
        const body = {
            // externalApplicant watch already pins groups to [Submitter].
            groups: state.groups,
            ...(isNew.value
                ? { new_contributor: state.newContributor }
                : { contributor_id: state.contributorId! }),
        };
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
    state.error = error instanceof Error ? error.message : String(error);
}
</script>

<template>
    <div class="invite-container bc-form">
        <div class="title-row">
            <h2 class="page-title">
                <i class="pi pi-user-plus title-icon" />
                Invite a Contributor
            </h2>
        </div>

        <p class="subtitle">
            Send a single-use link. When the person signs in with their BCSC,
            BCEID or IDIR login, their account is automatically linked to the
            Contributor record.
        </p>

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
            <label class="label">
                Contributor
                <span class="req">*</span>
            </label>
            <Select
                v-model="state.contributorId"
                :options="state.contributors"
                option-label="name"
                option-value="id"
                filter
                :reset-filter-on-hide="false"
                placeholder="Select a contributor"
                class="field"
                overlay-class="bc-overlay"
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
            <div class="field-group">
                <label class="label">Phone</label>
                <InputText
                    v-model="state.newContributor.phone"
                    type="tel"
                    class="field"
                />
            </div>
        </template>

        <div class="field-group">
            <div class="groups-header">
                <label class="label">
                    Groups
                    <span class="req">*</span>
                </label>
                <div class="checkbox-row">
                    <Checkbox
                        v-model="state.externalApplicant"
                        input-id="external-applicant"
                        binary
                    />
                    <label
                        class="label"
                        for="external-applicant"
                    >
                        Is External Applicant
                    </label>
                </div>
            </div>
            <MultiSelect
                v-model="state.groups"
                :options="groupOptions"
                :disabled="state.externalApplicant"
                filter
                display="chip"
                :placeholder="
                    state.externalApplicant
                        ? 'Submitter'
                        : 'Select groups to grant'
                "
                class="field"
                overlay-class="bc-overlay"
            />
            <small class="hint">
                {{
                    state.externalApplicant
                        ? 'External applicants are granted the Submitter role.'
                        : 'Groups the invited user is added to on sign-in.'
                }}
            </small>
        </div>

        <div class="actions">
            <Button
                class="cta"
                icon="pi pi-link"
                label="Generate signup link"
                :disabled="!canSubmit || state.submitting"
                :loading="state.submitting"
                @click="submit"
            />
        </div>

        <small
            v-if="state.error"
            class="error-msg"
        >
            {{ state.error }}
        </small>

        <div
            v-if="state.result"
            class="result"
        >
            <h2 class="result-title">Send this link to the contributor</h2>
            <div class="result-row">
                <InputText
                    :model-value="state.result.signup_url"
                    readonly
                    class="field"
                />
                <Button
                    class="copy-btn"
                    icon="pi pi-copy"
                    label="Copy"
                    severity="secondary"
                    @click="copyLink"
                />
            </div>
            <small class="hint">Expires: {{ formattedExpires() }}</small>
        </div>
    </div>
</template>

<style scoped>
@import url('@/bcap/styles/bc-theme.css');

/* Page layout only; header, tokens and widget theming live in bc-theme.css. */
.invite-container {
    max-width: 640px;
    margin: 0 auto 50px auto;
    padding: 2rem 1rem;
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
    color: #222;
    font-size: 1.125rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}
.title-row {
    gap: 1rem;
}
.title-icon {
    font-size: 2rem;
    margin-right: 0.6rem;
    vertical-align: baseline;
}
.subtitle {
    margin: 0 0 0.5rem;
    color: #1f2937;
    line-height: 1.6;
    font-size: 1.125rem;
}
.actions {
    display: flex;
    justify-content: flex-end;
}
.field-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}
.groups-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}
.checkbox-row {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0.5rem;
}
.checkbox-row .label {
    margin: 0;
    cursor: pointer;
    user-select: none;
}
.label {
    font-weight: 700;
    text-align: left;
    align-self: flex-start;
    color: var(--bc-navy);
    font-size: 1.2rem;
    padding-left: 0;
}
.req {
    color: #d8292f;
    margin-left: 0.2rem;
}
.error-msg {
    color: #d8292f;
    text-align: right;
    font-size: 1.2rem;
    font-weight: 600;
}
.hint {
    color: var(--bc-muted);
    font-size: 1rem;
}
.field-group .hint {
    margin-top: 0.25rem;
}
.field {
    width: 100%;
}
.result {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 1rem 1.25rem;
    border-radius: 8px;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-left: 4px solid var(--bc-navy);
}
.result-title {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--bc-navy);
}
.result-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}
.option {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
}
</style>
