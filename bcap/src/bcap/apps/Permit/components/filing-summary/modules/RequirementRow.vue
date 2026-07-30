<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from 'primevue/button';
import Menu from 'primevue/menu';
import Select from 'primevue/select';
import type { ContributorSummary } from '@/bcap/client/types.gen.ts';
import { initials } from '@/bcap/util.ts';
import MessageDialog from '@/bcap/apps/Permit/components/common/messages/MessageDialog.vue';
import {
    checklistHref,
    editChecklistHref,
    hasSubmission,
    isChecklist,
    withPermitContext,
    type RequirementItem,
} from '@/bcap/apps/Permit/components/filing-summary/modules/moduleRows.ts';

const props = defineProps<{
    requirement: RequirementItem;
    moduleId: string;
    permitId: string;
    isStaff?: boolean;
    applicationId?: string;
    staff?: unknown;
    toggling?: string | null;
    canViewSubmission?: boolean;
    assignees?: ContributorSummary[];
    position?: number;
}>();

const status = computed(() => {
    if (props.requirement.satisfied === null) {
        return { label: 'Loading', tone: 'is-unknown' };
    }
    return props.requirement.satisfied
        ? { label: 'Complete', tone: 'is-complete' }
        : { label: 'In progress', tone: 'is-in-progress' };
});

const emit = defineEmits<{
    (event: 'toggle'): void;
    (event: 'remove'): void;
    (event: 'view-submission'): void;
    (event: 'assign', contributorId: string | null): void;
}>();

const moreMenu = ref();

// Empty id is the unassigned choice; it goes back to the server as null.
const assigneeOptions = computed(() => [
    { id: '', name: 'Unassigned' },
    ...(props.assignees ?? []),
]);

const showSubmission = computed(
    () => props.canViewSubmission && hasSubmission(props.requirement.type),
);

const assigneeName = (id: string) =>
    assigneeOptions.value.find((one) => one.id === id)?.name ?? '';

// The secondary actions; the destructive one is separated and styled by class.
const moreItems = computed(() => [
    {
        label: 'View in Arches',
        icon: 'fa-solid fa-share-from-square',
        // A workflow/document requirement's subject is the resource it was filed
        // against (the permit application itself for the submission module), not
        // the requirement resource.
        url: `/bcap/resource/${
            hasSubmission(props.requirement.type)
                ? props.requirement.hostResourceId ||
                  props.requirement.resourceId
                : props.requirement.resourceId
        }`,
        target: '_blank',
    },
    ...(isChecklist(props.requirement.type)
        ? [
              {
                  label: 'Edit checklist (manager only)',
                  icon: 'fa-solid fa-pen-to-square',
                  url: withPermitContext(
                      editChecklistHref(props.requirement.resourceId),
                      props.permitId,
                      props.staff,
                  ),
                  target: '_blank',
              },
          ]
        : []),
    {
        separator: true,
    },
    {
        label: 'Delete requirement',
        icon: 'fa-solid fa-trash',
        class: 'req-more-danger',
        command: () => emit('remove'),
    },
]);
</script>

<template>
    <span
        v-if="position"
        class="req-position"
        :class="status.tone"
    >
        {{ position }}
    </span>
    <span class="requirement-label">
        <span class="requirement-name">{{ requirement.title }}</span>
        <span class="requirement-meta">
            <span v-if="requirement.type">{{ requirement.type }}</span>
            <span
                v-if="requirement.type"
                class="meta-dot"
            >
                &bull;
            </span>
            <span
                class="requirement-status"
                :class="status.tone"
            >
                <span class="status-dot"></span>
                {{ status.label }}
            </span>
        </span>
    </span>

    <span
        class="req-right"
        :class="{ 'is-readonly': !isStaff }"
    >
        <span class="req-lead">
            <Select
                v-if="isStaff && requirement.resourceId"
                :model-value="requirement.ministryAssigneeId"
                :options="assigneeOptions"
                option-label="name"
                option-value="id"
                filter
                filter-placeholder="Search contributors..."
                placeholder="Assign to..."
                class="req-assignee-select"
                append-to="body"
                @update:model-value="
                    (id: string) => $emit('assign', id || null)
                "
            >
                <template #value="{ value }">
                    <span class="req-assignee-value">
                        <span
                            class="req-avatar"
                            :class="{ 'is-empty': !value }"
                        >
                            {{ value ? initials(assigneeName(value)) : '+' }}
                        </span>
                        <span :class="{ 'is-unassigned': !value }">
                            {{ value ? assigneeName(value) : 'Assign to…' }}
                        </span>
                    </span>
                </template>
                <template #option="{ option }">
                    <span class="req-assignee-value">
                        <span
                            class="req-avatar"
                            :class="{ 'is-empty': !option.id }"
                        >
                            {{ option.id ? initials(option.name) : '+' }}
                        </span>
                        <span :class="{ 'is-unassigned': !option.id }">
                            {{ option.name }}
                        </span>
                    </span>
                </template>
            </Select>
            <!-- Rendered even when empty, so the messages button beside it keeps
                 its column on an unassigned row. -->
            <span
                v-else
                class="req-assignee"
                :class="{ 'is-unassigned': !requirement.ministryAssignee }"
                title="Ministry assignee"
            >
                <i class="fa-regular fa-user"></i>
                {{ requirement.ministryAssignee || 'Unassigned' }}
            </span>
        </span>
        <span class="req-actions">
            <!-- Wrapped because the dialog component has two roots, so a class on it
                 is dropped rather than landing on the trigger. -->
            <span
                v-if="applicationId && requirement.resourceId"
                class="req-messages"
            >
                <MessageDialog
                    :key="requirement.resourceId"
                    :application-id="applicationId"
                    :resource-id="requirement.resourceId"
                    :context="requirement.name"
                    :context-id="moduleId"
                />
            </span>
            <span
                v-if="showSubmission"
                class="req-submission-slot"
            >
                <Button
                    type="button"
                    class="req-action req-primary req-view-submission"
                    @click="$emit('view-submission')"
                >
                    <i class="fa-solid fa-eye"></i>
                    View Submission
                </Button>
            </span>
            <span
                class="req-action-slot"
                :class="{ 'no-submission': !showSubmission }"
            >
                <template v-if="isStaff && requirement.resourceId">
                    <!-- The everyday action stays on the row; the rest sit behind
                     the kebab. -->
                    <a
                        v-if="isChecklist(requirement.type)"
                        class="req-action req-primary"
                        :href="
                            withPermitContext(
                                checklistHref(requirement.resourceId),
                                permitId,
                                staff,
                            )
                        "
                        target="_blank"
                        rel="noopener"
                        title="Open the checklist to complete this requirement"
                    >
                        Open checklist
                    </a>
                    <Button
                        v-else
                        type="button"
                        class="req-action req-primary req-satisfy"
                        :disabled="toggling === requirement.resourceId"
                        @click="$emit('toggle')"
                    >
                        <i
                            class="fa-solid"
                            :class="
                                toggling === requirement.resourceId
                                    ? 'fa-circle-notch fa-spin'
                                    : requirement.satisfied
                                      ? 'fa-rotate-left'
                                      : 'fa-check'
                            "
                        ></i>
                        {{
                            requirement.satisfied
                                ? 'Mark unsatisfied'
                                : 'Mark satisfied'
                        }}
                    </Button>
                </template>
            </span>
        </span>
        <span class="req-more">
            <template v-if="isStaff && requirement.resourceId">
                <Button
                    type="button"
                    class="req-more-toggle"
                    icon="fa-solid fa-ellipsis"
                    title="More actions"
                    @click="moreMenu?.toggle($event)"
                />
                <Menu
                    ref="moreMenu"
                    :model="moreItems"
                    popup
                    append-to="body"
                    class="req-more-menu"
                />
            </template>
        </span>
    </span>
</template>

<style scoped>
/* The row's position in the module, tinted by status. */
.req-position {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 1.9rem;
    height: 1.9rem;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 600;
    background: #eef2f7;
    color: #64748b;
}

.req-position.is-complete {
    background: #dcfce7;
    color: #15803d;
}

.req-position.is-in-progress {
    background: #fef3c7;
    color: #b45309;
}

/* Takes the slack and truncates, so the trailing cluster (assignee, messages,
   actions) is never pushed off the row. */
.requirement-label {
    display: inline-flex;
    flex-direction: column;
    gap: 0.15rem;
    flex: 1;
    min-width: 0;
    overflow: hidden;
}

.requirement-name {
    color: #1f2937;
    font-weight: 600;
    font-size: 14px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.requirement-meta {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 12px;
    color: #64748b;
    white-space: nowrap;
}

.meta-dot {
    color: #cbd5e1;
}

.requirement-status {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}

.status-dot {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: #cbd5e1;
}

.requirement-status.is-complete {
    color: #15803d;
}

.requirement-status.is-complete .status-dot {
    background: #16a34a;
}

/* Gold marks the row as in progress, matching the module status glyph. */
.requirement-status.is-in-progress {
    color: #b45309;
}

.requirement-status.is-in-progress .status-dot {
    background: #e3a82b;
}

/* The assignee holds a fixed column so the names line up down the list; the
   actions pack against the right edge, so a row with fewer buttons closes the
   gap instead of leaving holes mid-row. */
.req-right {
    margin-left: auto;
    /* Shrinks before anything clips when the window is narrow. */
    min-width: 0;
    display: grid;
    align-items: center;
    /* Matches the gap between the action buttons themselves. */
    gap: 0.75rem;
    white-space: nowrap;
    grid-template-columns: minmax(0, 16rem) minmax(0, 46rem) auto;
}

.req-right.is-readonly {
    grid-template-columns: minmax(0, 16rem) minmax(0, 30rem) auto;
}

.req-lead {
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    grid-column: 1;
    min-width: 0;
}

.req-actions {
    display: inline-flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.75rem;
    grid-column: 2;
}

.req-assignee-select,
.req-assignee {
    width: 100%;
    min-width: 0;
    overflow: hidden;
}

/* Long names ellipsis rather than spilling over the buttons beside them. */
.req-assignee-select :deep(.p-select-label),
.req-assignee {
    text-overflow: ellipsis;
}

.req-more {
    grid-column: 3;
}

.req-messages,
.req-submission-slot,
.req-action-slot,
.req-more {
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
}

.req-assignee {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 14px;
    color: #475569;
    white-space: nowrap;
}

.req-assignee-select {
    font-size: 14px;
    border: 1px solid transparent;
    background: transparent;
    box-shadow: none;
}

.req-assignee-select:hover,
.req-assignee-select.p-select-open,
.req-assignee-select:focus,
.req-assignee-select.p-focus {
    border-color: var(--bc-border);
    background: #ffffff;
}

/* Its own focus indicator, since the theme zeroes PrimeVue's ring globally. */
.req-assignee-select:focus-visible,
.req-assignee-select :deep(:focus-visible) {
    outline: none;
    border-color: var(--bc-navy);
    box-shadow: 0 0 0 2px rgba(0, 51, 102, 0.25);
}

.req-assignee-select :deep(.p-select-label) {
    padding: 0.35rem 0.5rem;
    font-size: 14px;
    line-height: 1.2;
    color: var(--bc-navy);
}

.req-assignee-select :deep(.p-select-dropdown) {
    width: 1.5rem;
    color: #94a3b8;
}

.req-assignee-value {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.req-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 1.9rem;
    height: 1.9rem;
    border-radius: 50%;
    background: #dbeafe;
    color: var(--bc-navy);
    font-size: 11px;
    font-weight: 700;
}

.req-avatar.is-empty {
    background: transparent;
    border: 1px dashed #cbd5e1;
    color: #94a3b8;
    font-weight: 400;
}

.is-unassigned {
    color: #94a3b8;
}

/* Every action on the row shares this box model -- padding, border, font and
   line-height -- so they come out the same height without a fixed one. */
.req-action {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    box-sizing: border-box;
    /* Labels stay on one line; the column is sized for them. */
    white-space: nowrap;
    flex-shrink: 0;
    font-size: 14px;
    line-height: 1.2;
    font-weight: 600;
    color: var(--bc-navy);
    text-decoration: none;
    padding: 0.7rem 1.2rem;
    border: 1px solid var(--bc-border);
    border-radius: 6px;
    background: #ffffff;
    transition:
        background-color 0.15s ease,
        border-color 0.15s ease;
}

.req-action:hover {
    background: var(--bc-panel);
    border-color: var(--bc-navy);
    text-decoration: none;
}

/* Buttons styled as req-actions; the layout comes from .req-action above. */
.req-satisfy,
.req-view-arches,
.req-view-submission {
    cursor: pointer;
    font-family: inherit;
}

.req-satisfy:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* The shared Messages trigger is footer-sized and navy-filled; on the row it
   takes the row's box model and the outline treatment. */
.req-messages :deep(.trigger-btn) {
    box-sizing: border-box;
    padding: 0.7rem 1.2rem;
    border-width: 1px;
    border-radius: 6px;
    font-size: 14px;
    line-height: 1.2;
    font-weight: 600;
    gap: 0.4rem;
    background: #ffffff;
    border-color: var(--bc-navy);
    color: var(--bc-navy);
}

.req-messages :deep(.trigger-btn:hover) {
    background: var(--bc-panel);
    border-color: var(--bc-navy);
    color: var(--bc-navy);
}

.req-messages :deep(.trigger-btn i) {
    font-size: 14px;
}

.req-messages :deep(.message-badge) {
    font-size: 10px;
}

.req-primary {
    background: #ffffff;
    border-color: var(--bc-navy);
    color: var(--bc-navy);
}

.req-primary:hover {
    background: var(--bc-panel);
    border-color: var(--bc-navy);
    color: var(--bc-navy);
}

/* The row's decisive action, so it's filled rather than outlined. */
.req-satisfy,
.req-satisfy:hover {
    background: var(--bc-navy);
    border-color: var(--bc-navy);
    color: #ffffff;
}

.req-satisfy:hover {
    opacity: 0.9;
}

.req-more-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    padding: 0.7rem 1rem;
    font-size: 14px;
    line-height: 1.2;
    color: var(--bc-navy);
    border: 1px solid var(--bc-border);
    border-radius: 6px;
    background: #ffffff;
    cursor: pointer;
}

.req-more-toggle:hover {
    background: var(--bc-panel);
    border-color: var(--bc-navy);
}
</style>

<style>
/* The popup teleports to <body>, so its rules can't be scoped. Styled to match
   the dashboard's sort menu. */
.req-more-menu {
    min-width: 24rem;
    padding: 0.35rem 0;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    box-shadow: 0 8px 24px rgba(16, 24, 40, 0.16);
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
}

.req-more-menu .p-menu-list {
    margin-bottom: 0;
}

.req-more-menu .p-menu-separator {
    border-top: 1px solid #e5e7eb !important;
    margin: 0.35rem 0;
}

.req-more-menu .p-menu-item-link {
    padding: 0.75rem 1.35rem;
    font-size: 14px;
    font-weight: 600;
    color: var(--bc-navy);
    text-decoration: none;
}

.req-more-menu .p-menu-item-icon {
    width: 1.6rem;
    margin-right: 0.75rem;
    font-size: 13px;
    color: inherit;
}

.req-more-menu .p-menu-item-link:hover {
    background: var(--bc-navy);
    color: #ffffff;
    text-decoration: none;
}

.req-more-menu .req-more-danger .p-menu-item-link {
    color: #c8102e;
}

.req-more-menu .req-more-danger .p-menu-item-link:hover {
    background: #c8102e;
    color: #ffffff;
}
</style>
