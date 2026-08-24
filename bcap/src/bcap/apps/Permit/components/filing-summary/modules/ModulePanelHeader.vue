<script setup lang="ts">
import { computed, ref } from 'vue';
import arches from 'arches';
import Button from 'primevue/button';
import Menu from 'primevue/menu';
import { useMessageStore } from '@/bcap/stores/message.ts';
import {
    STATUS_ICON,
    type ModuleRow,
} from '@/bcap/apps/Permit/components/filing-summary/modules/moduleRows.ts';

const props = defineProps<{
    row: ModuleRow;
    isStaff?: boolean;
    // The resource this module opens in Arches; blank hides the link.
    resourceId?: string;
    // The module whose completion toggle is mid-save, if any.
    toggling?: string | null;
}>();

const emit = defineEmits<{
    (event: 'toggle'): void;
    (event: 'remove'): void;
    (event: 'dragstart'): void;
    (event: 'dragend'): void;
}>();

const messageStore = useMessageStore();

const moreMenu = ref();

const moreItems = computed(() => [
    {
        label: 'View in Arches',
        icon: 'fa-solid fa-up-right-from-square',
        visible: Boolean(props.resourceId),
        command: () =>
            window.open(
                `${arches.urls.resource_editor}${props.resourceId}`,
                '_blank',
                'noopener',
            ),
    },
    {
        label: 'Delete module',
        icon: 'fa-solid fa-trash',
        class: 'req-more-danger',
        command: () => emit('remove'),
    },
]);
</script>

<template>
    <span class="module-head">
        <span
            v-if="isStaff"
            class="drag-handle"
            title="Drag to reorder"
            draggable="true"
            @dragstart="$emit('dragstart')"
            @dragend="$emit('dragend')"
            @click.stop
        >
            <i class="fa-solid fa-grip-vertical"></i>
        </span>
        <span class="module-title">
            <span class="module-name">{{ row.name }}</span>
            <span
                v-if="row.moduleId"
                class="module-id"
            >
                · {{ row.moduleId }}
            </span>
            <span
                class="module-state-pill"
                :class="row.isCompleted ? 'state-complete' : 'state-progress'"
            >
                <i
                    :class="
                        row.isCompleted
                            ? STATUS_ICON.complete
                            : STATUS_ICON.inProgress
                    "
                ></i>
                {{ row.isCompleted ? 'Complete' : 'In progress' }}
            </span>
        </span>
        <span class="module-trailing">
            <Button
                v-if="isStaff"
                type="button"
                class="module-toggle"
                :disabled="toggling === row.tileid"
                :title="
                    row.isCompleted
                        ? 'Mark this module unsatisfied'
                        : 'Mark this module satisfied'
                "
                @click.stop="$emit('toggle')"
            >
                <i
                    class="fa-solid"
                    :class="
                        toggling === row.tileid
                            ? 'fa-circle-notch fa-spin'
                            : row.isCompleted
                              ? 'fa-rotate-left'
                              : 'fa-check'
                    "
                ></i>
                {{ row.isCompleted ? 'Mark unsatisfied' : 'Mark satisfied' }}
            </Button>
            <Button
                v-if="isStaff"
                type="button"
                class="module-more-toggle"
                icon="fa-solid fa-ellipsis"
                title="More actions"
                @click.stop="moreMenu?.toggle($event)"
            />
            <Menu
                ref="moreMenu"
                :model="moreItems"
                popup
                append-to="body"
                class="req-more-menu"
                @click.stop
            />
        </span>
        <span
            v-if="messageStore.moduleUnreadCount(row.tileid)"
            class="module-unread-badge"
            :title="`${messageStore.moduleUnreadCount(
                row.tileid,
            )} unread message(s)`"
        >
            <i class="fa-solid fa-comment-dots"></i>
            {{ messageStore.moduleUnreadCount(row.tileid) }}
        </span>
    </span>
</template>

<style scoped>
.module-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding-right: 0.75rem;
}

.drag-handle {
    cursor: grab;
    color: rgba(0, 51, 102, 0.5);
    padding: 0.25rem;
    border-radius: 6px;
    transition:
        color 0.15s ease,
        background-color 0.15s ease;
}

.drag-handle:hover {
    color: var(--bc-navy);
    background-color: rgba(0, 51, 102, 0.1);
}

.drag-handle:active {
    cursor: grabbing;
}

.module-title {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.module-name {
    font-weight: 700;
    font-size: max(16px, 1.25rem);
    color: var(--bc-navy);
}

.module-id {
    font-size: 1.3rem;
    font-weight: 400;
    color: var(--bc-muted);
}

.module-trailing {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
}

.module-state-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin-left: 0.75rem;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    white-space: nowrap;
}

.module-state-pill.state-progress {
    background-color: #fbeecb;
    color: #8a6100;
}

.module-state-pill.state-complete {
    background-color: #cdeed6;
    color: #15803d;
}

.module-unread-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.6rem;
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    background-color: #d32f2f;
    border-radius: 999px;
    white-space: nowrap;
}

.module-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 1rem;
    border: 1px solid var(--bc-navy);
    border-radius: 4px;
    background: var(--bc-navy);
    color: #ffffff;
    font: inherit;
    font-weight: 700;
    white-space: nowrap;
    cursor: pointer;
}

.module-toggle:hover:not(:disabled) {
    background: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
}

.module-toggle:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.module-more-toggle {
    background: none;
    border: 1px solid var(--bc-border);
    color: var(--bc-navy);
    cursor: pointer;
    font-size: 1rem;
    padding: 0.35rem 0.7rem;
    border-radius: 6px;
    transition: background-color 0.15s ease;
}

.module-more-toggle:hover {
    background-color: var(--bc-panel);
    border-color: var(--bc-navy);
}
</style>
