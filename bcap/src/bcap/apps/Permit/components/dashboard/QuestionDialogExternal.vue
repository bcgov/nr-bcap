<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import Dialog from 'primevue/dialog';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';
import { z } from 'zod';
import {
    createBcapMessage,
    getContributors,
    markMessageAsRead,
} from '@/bcap/apps/Permit/api.ts';
import type { FormattedMessage, AppThread } from '@/bcap/types.ts';
import {
    zBcapMessage,
    zPaginatedBcapMessageList,
    zPaginatedContributorList,
} from '@/bcap/client/zod.gen.ts';

export type RawBcapMessage = z.infer<typeof zBcapMessage>;
export type BcapMessageList = z.infer<typeof zPaginatedBcapMessageList>;
export type ContributorList = z.infer<typeof zPaginatedContributorList>;

const props = withDefaults(
    defineProps<{
        applicationId: string;
        permitResourceId: string;
        threads?: AppThread[];
        context?: string;
    }>(),
    {
        threads: () => [],
        context: 'General',
    },
);

const emit = defineEmits(['message-sent', 'thread-resolved']);

const visible = ref(false);
const messageText = ref('');
const isSubmitting = ref(false);
const messageInput = ref();
const threadContainer = ref<HTMLElement | null>(null);
const selectedRecipient = ref('');
const recipients = ref<Array<{ label: string; value: string }>>([]);
const isLoadingRecipients = ref(false);
const selectedTopic = ref('General Question');
const topics = ref([
    { label: 'General Question', value: 'General Question' },
    { label: 'Modification Request', value: 'Modification Request' },
    { label: 'Additional Information', value: 'Additional Information' },
]);
const selectedThreadId = ref<string>('new');

const activeThread = computed(() => {
    if (selectedThreadId.value === 'new' || !props.threads) return null;
    return props.threads.find((t) => t.id === selectedThreadId.value) || null;
});

const isReplyMode = computed(() => {
    return selectedThreadId.value !== 'new' && activeThread.value !== null;
});

const loadRecipients = async () => {
    isLoadingRecipients.value = true;
    try {
        const fetchedRecipients = await getContributorsForResources(
            props.permitResourceId,
        );
        recipients.value = fetchedRecipients;

        if (recipients.value.length > 0) {
            selectedRecipient.value = recipients.value[0].value;
        }
    } catch (error) {
        console.error('Error loading recipients:', error);
        recipients.value = [{ label: 'Ministry Desk', value: '' }];
        selectedRecipient.value = '';
    } finally {
        isLoadingRecipients.value = false;
    }
};

const openDialog = () => {
    selectedThreadId.value = 'new';
    visible.value = true;
};

const closeDialog = () => {
    visible.value = false;
    messageText.value = '';
    selectedTopic.value = 'General Question';
};

const selectThread = async (threadId: string) => {
    selectedThreadId.value = threadId;
    messageText.value = '';

    if (activeThread.value && activeThread.value.hasUnread) {
        const unreadMessages = activeThread.value.messages.filter(
            (msg: FormattedMessage) => msg.isUnread,
        );

        for (const msg of unreadMessages) {
            if (msg.id) {
                try {
                    await markMessageAsRead(msg.id);
                    msg.isUnread = false;

                    if (
                        activeThread.value.unreadCount &&
                        activeThread.value.unreadCount > 0
                    ) {
                        activeThread.value.unreadCount--;
                    }
                } catch (e) {
                    console.error('Failed to mark message as read:', e);
                }
            }
        }

        activeThread.value.hasUnread = false;
    }

    await nextTick();
    if (messageInput.value) {
        messageInput.value.$el.focus();
    }

    if (threadContainer.value) {
        threadContainer.value.scrollTop = threadContainer.value.scrollHeight;
    }
};

const submitMessage = async () => {
    if (!messageText.value) return;

    if (!isReplyMode.value && !selectedRecipient.value) {
        alert('Please select a recipient.');
        return;
    }

    isSubmitting.value = true;

    try {
        const targetThreadId = isReplyMode.value
            ? activeThread.value?.id
            : undefined;

        const formattedTopic = `${props.context} ${selectedTopic.value.toLowerCase()}`;

        const responseData = await createBcapMessage(
            messageText.value,
            selectedRecipient.value as string,
            props.applicationId,
            props.permitResourceId,
            targetThreadId,
            isReplyMode.value ? undefined : formattedTopic,
        );

        emit('message-sent', responseData);
        closeDialog();
    } catch (error) {
        console.error('Error submitting message:', error);
        alert('There was an error sending your message. Please try again.');
    } finally {
        isSubmitting.value = false;
    }
};

const markAsResolved = () => {
    if (!activeThread.value) return;
    emit('thread-resolved', activeThread.value.id);
};

onMounted(() => {
    loadRecipients();
});
</script>

<template>
    <div class="ask-question-trigger">
        <Button
            severity="secondary"
            class="trigger-btn"
            @click="openDialog"
        >
            <span class="trigger-label">View Messages</span>
            <i class="fa-regular fa-comment-dots"></i>

            <span
                v-if="threads.some((t) => t.hasUnread)"
                class="message-badge"
            >
                {{ threads.reduce((sum, t) => sum + (t.unreadCount || 0), 0) }}
            </span>
        </Button>
    </div>

    <Dialog
        v-model:visible="visible"
        modal
        :closable="true"
        :style="{ width: '850px' }"
        :pt="{
            root: { class: 'message-dialog' },
            header: { class: 'message-dialog-header' },
            closeButton: { class: 'message-dialog-close' },
            content: { style: { padding: '0', overflow: 'hidden' } },
        }"
    >
        <template #header>
            <span class="header-title">
                Comments on Application {{ applicationId }}
            </span>
        </template>

        <template #closeicon>
            <i class="fa-solid fa-xmark custom-close-icon"></i>
        </template>

        <!-- SPLIT LAYOUT CONTAINER -->
        <div class="dialog-body-split">
            <!-- SIDEBAR -->
            <div class="thread-sidebar">
                <div
                    v-for="thread in threads"
                    :key="thread.id"
                    class="sidebar-item"
                    :class="{
                        active: selectedThreadId === thread.id,
                        unread: thread.hasUnread,
                        resolved: thread.isResolved,
                    }"
                    @click="selectThread(thread.id)"
                >
                    <span class="thread-topic-label">{{ thread.topic }}</span>
                    <span class="thread-count">
                        ({{ thread.messages.length }})
                    </span>
                </div>

                <div
                    class="sidebar-item new-message-item"
                    :class="{ active: selectedThreadId === 'new' }"
                    @click="selectThread('new')"
                >
                    + New Message
                </div>
            </div>
            <div class="thread-content">
                <!-- NEW MESSAGE VIEW -->
                <div
                    v-if="!isReplyMode"
                    class="new-question-view"
                >
                    <div
                        class="field-container"
                        style="margin-bottom: 1rem"
                    >
                        <Dropdown
                            v-model="selectedRecipient"
                            :options="recipients"
                            :loading="isLoadingRecipients"
                            option-label="label"
                            option-value="value"
                            placeholder="Select Recipient"
                            class="w-full"
                            :pt="{
                                root: {
                                    style: {
                                        height: '3.5rem',
                                        alignItems: 'center',
                                        borderRadius: '6px',
                                    },
                                },
                                item: { style: { padding: '1rem' } },
                            }"
                        >
                            <template #value="slotProps">
                                <div
                                    v-if="
                                        slotProps.value !== null &&
                                        slotProps.value !== undefined
                                    "
                                    class="dropdown-value-template"
                                >
                                    <i class="fa-regular fa-envelope"></i>
                                    <span>
                                        {{
                                            recipients.find(
                                                (r) =>
                                                    r.value === slotProps.value,
                                            )?.label
                                        }}
                                    </span>
                                </div>
                                <span
                                    v-else
                                    style="font-size: 1.25rem; color: #6c757d"
                                >
                                    {{ slotProps.placeholder }}
                                </span>
                            </template>
                            <template #option="slotProps">
                                <div class="dropdown-value-template">
                                    <i class="fa-regular fa-envelope"></i>
                                    <span>{{ slotProps.option.label }}</span>
                                </div>
                            </template>
                        </Dropdown>
                    </div>

                    <div
                        class="field-container"
                        style="margin-bottom: 1rem"
                    >
                        <div class="context-display-box">
                            <span class="context-label">Regarding:</span>
                            <span class="context-value">{{ context }}</span>
                        </div>
                    </div>

                    <div
                        class="field-container"
                        style="margin-bottom: 1.5rem"
                    >
                        <Dropdown
                            v-model="selectedTopic"
                            :options="topics"
                            option-label="label"
                            option-value="value"
                            class="w-full"
                            :pt="{
                                root: {
                                    style: {
                                        height: '3.5rem',
                                        alignItems: 'center',
                                        borderRadius: '6px',
                                    },
                                },
                                input: {
                                    style: {
                                        fontSize: '1.35rem',
                                        color: '#495057',
                                        paddingLeft: '1rem',
                                    },
                                },
                                item: {
                                    style: {
                                        padding: '1rem',
                                        fontSize: '1.35rem',
                                        color: '#495057',
                                    },
                                },
                            }"
                        />
                    </div>

                    <div class="field-container textarea-wrapper">
                        <label class="field-label">Message:</label>
                        <Textarea
                            ref="messageInput"
                            v-model="messageText"
                            rows="5"
                            class="full-width-textarea"
                            auto-resize
                        />
                    </div>

                    <div class="action-footer">
                        <Button
                            label="Send"
                            class="send-btn"
                            :loading="isSubmitting"
                            @click="submitMessage"
                        />
                    </div>
                </div>

                <!-- REPLY VIEW -->
                <div
                    v-else
                    class="reply-view"
                >
                    <div
                        ref="threadContainer"
                        class="message-thread"
                    >
                        <div
                            v-for="(msg, index) in activeThread?.messages"
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
                        </div>
                    </div>

                    <div class="field-container textarea-wrapper">
                        <label class="field-label">Write a Reply:</label>
                        <Textarea
                            ref="messageInput"
                            v-model="messageText"
                            rows="4"
                            class="full-width-textarea"
                            auto-resize
                        />
                    </div>

                    <div class="action-footer">
                        <Button
                            label="Mark as Resolved"
                            class="send-btn"
                            @click="markAsResolved"
                        />
                        <Button
                            label="Send"
                            class="send-btn"
                            :loading="isSubmitting"
                            @click="submitMessage"
                        />
                    </div>
                </div>
            </div>
        </div>
    </Dialog>
</template>

<style>
/* --- Trigger Button Styles --- */
/* BC Gov secondary button: navy outline on white. */
/* Filled navy so the primary action leads over the muted "Submitted" chip. */
.trigger-btn {
    background-color: var(--bc-navy);
    color: #ffffff;
    border: 2px solid var(--bc-navy);
    border-radius: 4px;
    padding: 0.5rem 1rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    position: relative;
}

.trigger-btn:hover {
    background-color: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
}

.message-badge {
    position: absolute;
    top: -8px;
    right: -8px;
    background-color: #d32f2f;
    color: #ffffff;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 0.75rem;
    font-weight: bold;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* --- Dialog Container & Header --- */
.message-dialog {
    border-radius: 8px;
    overflow: hidden;
}

.message-dialog-header {
    background-color: #003366 !important;
    color: white !important;
    padding: 1rem 1.5rem !important;
    border-bottom: none !important;
}

.message-dialog-header .header-title {
    font-weight: 700;
    font-size: 1.1rem;
}

.custom-close-icon {
    font-size: 1.5rem;
    color: white;
}

.message-dialog-close {
    color: white !important;
    width: 2.5rem !important;
    height: 2.5rem !important;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 4px;
}

.message-dialog-close:hover {
    background-color: rgba(255, 255, 255, 0.2) !important;
}

/* --- Split Layout Body (FIXED HEIGHT) --- */
.dialog-body-split {
    display: flex;
    height: 450px;
    background-color: #f8f9fa;
}

/* --- Sidebar Styles --- */
.thread-sidebar {
    width: 260px;
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

.sidebar-item {
    padding: 1.25rem;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;
    font-size: 1.15rem;
    color: #333;
    transition: background-color 0.2s ease;
}

.sidebar-item:hover {
    background-color: #f1f3f5;
}

/* UNREAD STATE: Bolds the topic text */
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

.sidebar-item.active.unread .thread-topic-label,
.sidebar-item.active.resolved {
    color: #ffffff;
}

.new-message-item {
    margin-top: auto;
    font-weight: 500;
}

/* --- Main Content Area --- */
.thread-content {
    flex: 1;
    padding: 1.5rem;
    background-color: #ffffff;
    display: flex;
    flex-direction: column;
    overflow: hidden; /* Prevent internal elements from breaking layout */
}

.new-question-view,
.reply-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

.field-container {
    width: 100%;
}

.textarea-wrapper {
    display: flex;
    flex-direction: column;
    margin-top: auto; /* Pushes to bottom */
}

.field-label {
    display: block;
    margin-bottom: 0.5rem;
    color: #333;
}

/* --- Full Width Textarea --- */
.full-width-textarea {
    width: 100% !important;
    box-sizing: border-box;
    border-radius: 6px;
    border-color: #ced4da;
}

/* --- Dynamic Thread History Area --- */
.message-thread {
    flex-grow: 1; /* Eats remaining vertical space */
    overflow-y: auto; /* Adds scrollbar strictly to this box */
    margin-bottom: 1.5rem;
    padding: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    background-color: #fafafa;
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
}

.message-date {
    font-size: 0.85rem;
    color: #6c757d;
}

.historical-message p {
    margin: 0;
    line-height: 1.5;
}

/* --- Footer Buttons --- */
.action-footer {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
}

.send-btn {
    background-color: #007bff;
    border: none;
    padding: 0.5rem 1.5rem;
    border-radius: 6px;
}

.send-btn:hover {
    background-color: #0069d9;
}

.dropdown-value-template {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 1.25rem;
    color: #495057;
}

.dropdown-value-template i {
    font-size: 1.3rem;
}

/* Context Display */
.context-label {
    font-weight: 500;
}

.context-value {
    font-weight: 600;
    padding-left: 0.5rem;
}
</style>
