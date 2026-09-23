<script setup lang="ts">
import { formatTimestamp } from '@/bcap/util.ts';
import { useUserStore } from '@/bcap/stores/user.ts';
import { NEW_THREAD_ID } from '@/bcap/types.ts';
import type { MessageThread } from '@/bcap/types.ts';

defineProps<{
    threads: MessageThread[];
    showArchived: boolean;
    selectedThreadId: string;
}>();

defineEmits<{
    (e: 'select-tab', archived: boolean): void;
    (e: 'select-thread', threadId: string): void;
}>();

const userStore = useUserStore();
</script>

<template>
    <div class="thread-sidebar">
        <div
            class="sidebar-item new-message-item"
            :class="{ active: selectedThreadId === NEW_THREAD_ID }"
            @click="$emit('select-thread', NEW_THREAD_ID)"
        >
            <i class="fa-solid fa-plus"></i>
            New Message
        </div>
        <div class="sidebar-tabs">
            <button
                type="button"
                class="sidebar-tab"
                :class="{ active: !showArchived }"
                @click="$emit('select-tab', false)"
            >
                Active
            </button>
            <button
                type="button"
                class="sidebar-tab"
                :class="{ active: showArchived }"
                @click="$emit('select-tab', true)"
            >
                Archived
            </button>
        </div>

        <div class="thread-list">
            <div
                v-for="thread in threads"
                :key="thread.id"
                class="sidebar-item"
                :class="{
                    active: selectedThreadId === thread.id,
                    unresolved: thread.needsAction,
                }"
                @click="$emit('select-thread', thread.id)"
            >
                <span class="thread-badges">
                    <span
                        v-if="thread.isInternal"
                        class="thread-badge thread-internal"
                    >
                        <i class="fa-solid fa-lock"></i>
                        Internal
                    </span>
                    <span
                        v-else-if="userStore.isInternal"
                        class="thread-badge thread-external"
                    >
                        <i class="fa-solid fa-users"></i>
                        External
                    </span>
                    <span
                        v-if="userStore.isInternal && thread.isResolved"
                        class="thread-badge thread-resolved"
                    >
                        <i class="fa-solid fa-check"></i>
                        Resolved
                    </span>
                </span>
                <span class="thread-topic-label">{{ thread.topic }}</span>
                <span class="thread-started-by">{{ thread.startedBy }}</span>
                <span
                    v-if="thread.lastMessageDate"
                    class="thread-date"
                >
                    {{ formatTimestamp(thread.lastMessageDate) }}
                </span>
            </div>

            <div
                v-if="threads.length === 0"
                class="sidebar-item empty-note"
            >
                {{ showArchived ? 'No archived messages.' : 'No messages.' }}
            </div>
        </div>
    </div>
</template>

<style>
.thread-sidebar {
    width: 320px;
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.sidebar-tabs {
    flex-shrink: 0;
    display: flex;
    border-bottom: 1px solid #e0e0e0;
}

.sidebar-tab {
    flex: 1;
    padding: 1.25rem;
    border: none;
    border-bottom: 3px solid transparent;
    background: none;
    cursor: pointer;
    font-size: 1.35rem;
    font-weight: 600;
    color: #6c757d;
}

/* A border, not a box-shadow: the global focus reset strips box-shadows. */
.sidebar-tab.active {
    color: var(--bc-navy);
    font-weight: 700;
    border-bottom-color: var(--bc-navy);
}

.thread-list {
    flex: 1;
    overflow-y: auto;
}

.sidebar-item {
    padding: 1.2rem 1.5rem;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;
    font-size: 1.35rem;
    color: #333;
    transition: background-color 0.2s ease;
}

.sidebar-item:hover {
    background-color: #f1f3f5;
}

.sidebar-item.empty-note {
    color: #6c757d;
    cursor: default;
}

.thread-topic-label {
    text-transform: capitalize;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
}

.thread-started-by {
    display: block;
    margin-top: 0.2rem;
    font-size: 1.15rem;
    color: #495057;
}

.thread-date {
    display: block;
    margin-top: 0.3rem;
    font-size: 1.1rem;
    color: #6c757d;
}

.sidebar-item.unresolved .thread-topic-label {
    font-weight: 700;
    color: #000;
}

.thread-badges {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 0.3rem;
}

.thread-badges:empty {
    display: none;
}

.thread-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.1rem 0.5rem;
    border-radius: 4px;
    font-size: 1.05rem;
    font-weight: 600;
}

.thread-internal {
    background-color: var(--internal-bg);
    color: var(--internal-text);
}

.thread-external {
    background-color: var(--external-bg);
    color: var(--external-text);
}

.thread-resolved {
    background-color: var(--resolved-bg);
    color: var(--resolved-text);
}

.sidebar-item.active {
    background-color: #1a6ab0;
    color: #ffffff;
    border-bottom-color: #1a6ab0;
}

.sidebar-item.active .thread-started-by,
.sidebar-item.active .thread-date {
    color: rgba(255, 255, 255, 0.9);
}

.sidebar-item.active.unresolved .thread-topic-label {
    color: #ffffff;
}

/* Same top offset, size and type as the thread-header buttons opposite. */
.new-message-item {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    margin: 1.5rem 1.5rem 0.75rem;
    padding: 0.7rem 1.2rem;
    font-weight: 600;
    font-size: 14px;
    line-height: 1.2;
    color: #ffffff;
    background-color: var(--bc-navy);
    border: 1px solid var(--bc-navy);
    border-radius: 6px;
}

.new-message-item.active {
    background-color: #003366;
    color: #ffffff;
}

.new-message-item:hover {
    background-color: var(--bc-navy-dark);
    color: #ffffff;
}
</style>
