<script setup lang="ts">
import { ref, watch } from 'vue';
import { downloadFile, formatFileSize } from '@/bcap/util.ts';
import { useMessageStore } from '@/bcap/stores/message.ts';

const props = defineProps<{
    threadId: string;
    isLoading: boolean;
}>();

const messageStore = useMessageStore();
const thread = ref<HTMLElement | null>(null);
const isLoadingEarlier = ref(false);

const loadEarlier = async () => {
    isLoadingEarlier.value = true;
    try {
        await messageStore.loadEarlierMessages(props.threadId);
    } finally {
        isLoadingEarlier.value = false;
    }
};

// Open on the latest message. Messages arrive while the spinner still shows, so
// also scroll once it clears. Earlier pages leave the newest alone, so they
// don't pull the view down.
watch(
    [() => messageStore.openMessages.at(-1)?.id, () => props.isLoading],
    () => {
        if (thread.value) thread.value.scrollTop = thread.value.scrollHeight;
    },
    { flush: 'post' },
);
</script>

<template>
    <div
        ref="thread"
        class="message-thread"
    >
        <div
            v-if="isLoading"
            class="messages-loading"
        >
            <i class="fa-solid fa-spinner fa-spin"></i>
            Loading messages…
        </div>
        <template v-else>
            <button
                v-if="messageStore.hasEarlierMessages"
                type="button"
                class="load-earlier"
                :disabled="isLoadingEarlier"
                @click="loadEarlier"
            >
                <i
                    v-if="isLoadingEarlier"
                    class="fa-solid fa-spinner fa-spin"
                ></i>
                Show earlier messages
            </button>
            <div
                v-for="msg in messageStore.openMessages"
                :key="msg.id"
                class="historical-message"
            >
                <div class="message-header">
                    <span class="message-author">
                        <strong>{{ msg.author }}</strong>
                        <span
                            v-if="msg.authorIsStaff"
                            class="staff-chip"
                        >
                            Archaeology Branch
                        </span>
                    </span>
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

.load-earlier {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 auto 1rem;
    padding: 0.4rem 1rem;
    border: none;
    background: none;
    color: var(--bc-navy);
    font-size: 1.2rem;
    font-weight: 600;
    cursor: pointer;
}

.load-earlier:hover:not(:disabled) {
    text-decoration: underline;
}

.historical-message {
    padding: 1rem 0.25rem;
    color: #333;
}

.historical-message:first-child {
    padding-top: 0;
}

.historical-message:last-child {
    padding-bottom: 0;
}

.historical-message + .historical-message {
    border-top: 1px solid #e5e7eb;
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    margin-bottom: 0.35rem;
}

.historical-message strong {
    color: var(--bc-text);
    font-weight: 700;
    margin: 0;
    font-size: 1.3rem;
}

.message-date {
    flex-shrink: 0;
    font-size: 1.1rem;
    color: var(--bc-muted);
}

.historical-message p {
    margin: 0;
    line-height: 1.55;
    font-size: 1.3rem;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
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
.message-author {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.staff-chip {
    padding: 0.1rem 0.5rem;
    border-radius: 4px;
    font-size: 1.05rem;
    font-weight: 600;
    color: #334155;
    background-color: #eef1f4;
}
</style>
