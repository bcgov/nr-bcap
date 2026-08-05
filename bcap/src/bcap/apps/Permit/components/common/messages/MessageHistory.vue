<script setup lang="ts">
import { downloadFile, formatFileSize } from '@/bcap/util.ts';
import type { FormattedMessage } from '@/bcap/types.ts';

defineProps<{
    messages: FormattedMessage[];
    isLoading: boolean;
}>();
</script>

<template>
    <div class="message-thread">
        <div
            v-if="isLoading"
            class="messages-loading"
        >
            <i class="fa-solid fa-spinner fa-spin"></i>
            Loading messages…
        </div>
        <template v-else>
            <div
                v-for="(msg, index) in messages"
                :key="index"
                class="historical-message"
            >
                <div class="message-header">
                    <strong>{{ msg.author }}:</strong>
                    <span
                        v-if="msg.date"
                        class="message-date"
                    >
                        {{ msg.date }}
                    </span>
                </div>
                <p>{{ msg.text }}</p>
                <div
                    v-if="msg.attachments?.length"
                    class="message-attachments"
                >
                    <ul class="attachment-list">
                        <li
                            v-for="file in msg.attachments"
                            :key="file.url"
                        >
                            <a
                                :href="file.url"
                                :download="file.name"
                                @click.prevent="
                                    downloadFile(file.url, file.name)
                                "
                            >
                                <i class="fa-regular fa-paperclip"></i>
                                <span class="attachment-name">
                                    {{ file.name }}
                                </span>
                                <span
                                    v-if="file.size"
                                    class="attachment-size"
                                >
                                    {{ formatFileSize(file.size) }}
                                </span>
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
        </template>
    </div>
</template>

<style>
.message-thread {
    flex: 1 1 auto;
    min-height: 10rem;
    overflow-y: auto;
    margin-bottom: 1.5rem;
    padding: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    background-color: #fafafa;
}

.messages-loading {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: center;
    padding: 1rem;
    color: #6c757d;
}

.historical-message {
    margin-bottom: 1rem;
    color: #333;
    padding-bottom: 1rem;
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.5rem;
}

.historical-message strong {
    color: #000;
    font-weight: 600;
    margin: 0;
    font-size: 1.3rem;
}

.message-date {
    font-size: 1.1rem;
    color: #6c757d;
}

.historical-message p {
    margin: 0;
    line-height: 1.5;
    font-size: 1.25rem;
}

.message-attachments {
    margin-top: 0.7rem;
}

.attachment-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.attachment-list a {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 100%;
    padding: 0.4rem 0.9rem;
    background-color: #eef2f7;
    border: 1px solid #d6dee8;
    border-radius: 16px;
    color: var(--bc-navy);
    font-size: 1.15rem;
    text-decoration: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.attachment-list a:hover {
    background-color: var(--bc-selected);
    border-color: var(--bc-navy);
}

.attachment-list i {
    flex-shrink: 0;
    font-size: 1.1rem;
}

.attachment-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.attachment-size {
    flex-shrink: 0;
    color: #6c757d;
    font-size: 0.95em;
}
</style>
