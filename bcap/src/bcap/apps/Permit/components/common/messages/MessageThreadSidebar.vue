<script setup lang="ts">
import { formatTimestamp } from '@/bcap/util.ts';
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
</script>

<template>
    <div class="thread-sidebar">
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
                    unread: thread.hasUnread,
                    resolved: thread.isResolved,
                }"
                @click="$emit('select-thread', thread.id)"
            >
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

        <div
            class="sidebar-item new-message-item"
            :class="{ active: selectedThreadId === 'new' }"
            @click="$emit('select-thread', 'new')"
        >
            + New Message
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
    background: none;
    cursor: pointer;
    font-size: 1.5rem;
    font-weight: 600;
    color: #6c757d;
}

.sidebar-tab.active {
    color: var(--bc-navy);
    font-weight: 700;
    box-shadow: inset 0 -3px 0 var(--bc-navy);
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

.sidebar-item.unread .thread-topic-label {
    font-weight: 700;
    color: #000;
}

.sidebar-item.resolved {
    color: #a0a0a0;
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

.sidebar-item.active.unread .thread-topic-label,
.sidebar-item.active.resolved {
    color: #ffffff;
}

.new-message-item {
    flex-shrink: 0;
    margin: 0.75rem;
    padding: 1.1rem;
    text-align: center;
    font-weight: 700;
    font-size: 1.25rem;
    color: #ffffff;
    background-color: #003366;
    border: none;
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
