<script setup lang="ts">
import Button from 'primevue/button';
import QuestionDialog from '@/bcap/apps/Permit/components/common/QuestionDialogExternal.vue';
import {
    STATUS_ICON,
    checklistHref,
    editChecklistHref,
    hasSubmission,
    isChecklist,
    withPermitContext,
    type RequirementItem,
} from '@/bcap/apps/Permit/components/filing-summary/modules/moduleRows.ts';

defineProps<{
    requirement: RequirementItem;
    moduleId: string;
    permitId: string;
    isStaff?: boolean;
    applicationId?: string;
    // Rides onto the checklist links so those tabs can come back to this view.
    staff?: unknown;
    // The requirement whose satisfied toggle is mid-save, if any.
    toggling?: string | null;
    canViewSubmission?: boolean;
}>();

defineEmits<{
    (event: 'toggle'): void;
    (event: 'remove'): void;
    (event: 'view-submission'): void;
}>();
</script>

<template>
    <i
        class="status-icon"
        :class="
            requirement.satisfied === null
                ? [STATUS_ICON.unknown, 'status-unknown']
                : requirement.satisfied
                  ? [STATUS_ICON.complete, 'status-ok']
                  : [STATUS_ICON.inProgress, 'status-in-progress']
        "
        :title="
            requirement.satisfied === null
                ? 'Status loading'
                : requirement.satisfied
                  ? 'Satisfied'
                  : 'In progress'
        "
    ></i>
    <span class="requirement-name">{{ requirement.name }}</span>
    <span class="req-right">
        <span
            v-if="requirement.ministryAssignee"
            class="req-assignee"
            title="Ministry assignee"
        >
            <i class="fa-regular fa-user"></i>
            {{ requirement.ministryAssignee }}
        </span>
        <span
            v-if="requirement.type"
            class="req-type"
        >
            {{ requirement.type }}
        </span>
        <QuestionDialog
            v-if="applicationId && requirement.resourceId"
            :key="requirement.resourceId"
            class="req-messages"
            :application-id="applicationId"
            :resource-id="requirement.resourceId"
            :context="requirement.name"
            :context-id="moduleId"
        />
        <Button
            v-if="canViewSubmission && hasSubmission(requirement.type)"
            type="button"
            class="req-action req-view-submission"
            @click="$emit('view-submission')"
        >
            <i class="fa-solid fa-file-lines"></i>
            View Submission
        </Button>
        <template v-if="isStaff && requirement.resourceId">
            <template v-if="isChecklist(requirement.type)">
                <a
                    class="req-action"
                    :href="
                        withPermitContext(
                            checklistHref(requirement.resourceId),
                            permitId,
                            staff,
                        )
                    "
                    target="_blank"
                    rel="noopener"
                    title="Complete the checklist to satisfy this requirement"
                >
                    <i class="fa-solid fa-magnifying-glass"></i>
                    Complete Checklist
                </a>
                <a
                    class="req-action"
                    :href="
                        withPermitContext(
                            editChecklistHref(requirement.resourceId),
                            permitId,
                            staff,
                        )
                    "
                    target="_blank"
                    rel="noopener"
                    title="Add, remove, or reorder subrequirements"
                >
                    Edit Checklist (manager only)
                </a>
            </template>
            <Button
                v-else
                type="button"
                class="req-action req-satisfy"
                :class="{ 'is-satisfied': requirement.satisfied }"
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
            <a
                class="req-action req-view-arches"
                :href="`/bcap/resource/${requirement.resourceId}`"
                target="_blank"
                rel="noopener"
            >
                <i class="fa-solid fa-share-from-square"></i>
                View Arches
            </a>
            <Button
                type="button"
                class="req-remove"
                icon="fa-solid fa-trash"
                title="Remove requirement"
                @click="$emit('remove')"
            />
        </template>
    </span>
</template>

<style scoped>
.status-icon {
    font-size: 13px;
    flex-shrink: 0;
}

.status-ok {
    color: #16a34a;
}

/* Gold marks the row as in progress, matching the module status glyph. */
.status-in-progress {
    color: #e3a82b;
}

.status-unknown {
    color: #cbd5e1;
}

.requirement-name {
    color: #111827;
    font-weight: 500;
    font-size: 13px;
}

.req-right {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    white-space: nowrap;
}

/* Subtle bordered chip so the type reads as an intentional tag, not a stray
   label. Fixed width keeps the actions after it (View, trash) aligned. */
.req-type {
    display: inline-block;
    min-width: 8rem;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--bc-muted);
    border: 1px solid var(--bc-border);
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    white-space: nowrap;
}

.req-assignee {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 12px;
    color: #475569;
    white-space: nowrap;
}

.req-action {
    font-size: 13px;
    font-weight: 600;
    color: var(--bc-navy);
    text-decoration: none;
    padding: 0.25rem 0.65rem;
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

/* Buttons styled as req-actions; the icon needs the shared inline spacing. */
.req-satisfy,
.req-view-arches,
.req-view-submission {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    cursor: pointer;
    font-family: inherit;
}

/* Filled green once satisfied so the state reads off the button as well as the
   status icon, matching the module-level toggle. */
.req-satisfy.is-satisfied {
    background: #16a34a;
    border-color: #16a34a;
    color: #ffffff;
}

.req-satisfy.is-satisfied:hover {
    background: #15803d;
    border-color: #15803d;
}

.req-satisfy:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* The shared Messages trigger is footer-sized; match the row actions instead. */
.req-messages :deep(.trigger-btn) {
    padding: 0.25rem 0.65rem;
    border-width: 1px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    line-height: 1.4;
    gap: 0.35rem;
}

.req-messages :deep(.trigger-btn i) {
    font-size: 12px;
}

.req-messages :deep(.message-badge) {
    font-size: 10px;
}

.req-remove {
    background: none;
    border: none;
    color: #c8102e;
    cursor: pointer;
    font-size: 13px;
    padding: 0.25rem 0.35rem;
    border-radius: 4px;
    transition: background-color 0.15s ease;
}

.req-remove:hover {
    background-color: #fde8ea;
}
</style>
