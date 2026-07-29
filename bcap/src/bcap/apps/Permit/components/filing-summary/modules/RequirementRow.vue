<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from 'primevue/button';
import Menu from 'primevue/menu';
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

const props = defineProps<{
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

const emit = defineEmits<{
    (event: 'toggle'): void;
    (event: 'remove'): void;
    (event: 'view-submission'): void;
}>();

const moreMenu = ref();

// The secondary actions; the destructive one is separated and styled by class.
const moreItems = computed(() => [
    {
        label: 'View in Arches',
        icon: 'fa-solid fa-share-from-square',
        url: `/bcap/resource/${props.requirement.resourceId}`,
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
        <!-- Wrapped because the dialog component has two roots, so a class on it
             is dropped rather than landing on the trigger. -->
        <span
            v-if="applicationId && requirement.resourceId"
            class="req-messages"
        >
            <QuestionDialog
                :key="requirement.resourceId"
                :application-id="applicationId"
                :resource-id="requirement.resourceId"
                :context="requirement.name"
                :context-id="moduleId"
            />
        </span>
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
            <!-- The everyday action stays on the row; the rest sit behind the
                 kebab. -->
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
                title="Complete the checklist to satisfy this requirement"
            >
                <i class="fa-solid fa-magnifying-glass"></i>
                Complete Checklist
            </a>
            <Button
                v-else
                type="button"
                class="req-action req-primary req-satisfy"
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

/* Every action on the row shares this box model -- padding, border, font and
   line-height -- so they come out the same height without a fixed one. */
.req-action {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    box-sizing: border-box;
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

/* The shared Messages trigger is footer-sized; give it the row's box model. */
.req-messages :deep(.trigger-btn) {
    box-sizing: border-box;
    padding: 0.7rem 1.2rem;
    border-width: 1px;
    border-radius: 6px;
    font-size: 14px;
    line-height: 1.2;
    font-weight: 600;
    gap: 0.4rem;
}

.req-messages :deep(.trigger-btn i) {
    font-size: 14px;
}

.req-messages :deep(.message-badge) {
    font-size: 10px;
}

.req-primary {
    background: var(--bc-navy);
    border-color: var(--bc-navy);
    color: #ffffff;
}

.req-primary:hover {
    background: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
    color: #ffffff;
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

.req-more-menu,
.req-more-menu * {
    outline: none !important;
    box-shadow: none !important;
    border-color: transparent !important;
    --p-focus-ring: none !important;
    --p-focus-ring-width: 0px !important;
    --p-focus-ring-color: transparent !important;
    --p-focus-ring-offset: 0px !important;
    --p-focus-ring-shadow: none !important;
}

/* Restored after the reset above, which strips every border colour. */
.req-more-menu {
    border-color: #e5e7eb !important;
    box-shadow: 0 8px 24px rgba(16, 24, 40, 0.16) !important;
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
