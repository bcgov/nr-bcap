<script setup lang="ts">
import { reactive, ref, computed, nextTick, onMounted } from 'vue';
import Dialog from 'primevue/dialog';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';
import { getContributorsForResources } from '@/bcap/apps/Permit/api.ts';
import { formatTimestamp, downloadFile } from '@/bcap/util.ts';
import { useMessageStore } from '@/bcap/stores/message.ts';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';

// The dialog shows the threads on one resource, scoped by its id: the permit for
// the permit view, or a module's own resource for that module's view. context is a
// label only: it prefixes a new message's subject so a thread reads as "which
// resource" in the list. It does not filter what the dialog shows.
const props = defineProps<{
    applicationId: string;
    resourceId: string;
    context?: string;
    // The resource's own id (e.g. a module id), appended to the title.
    contextId?: string;
}>();

const messageStore = useMessageStore();

// Dialog state grouped in one reactive object. The two template refs below bind
// to DOM nodes, so they stay refs.
const state = reactive({
    visible: false,
    showArchived: false,
    messageText: '',
    subjectText: '',
    isSubmitting: false,
    isResolving: false,
    selectedRecipient: '',
    recipients: [] as Array<{ label: string; value: string }>,
    isLoadingRecipients: false,
    isLoadingMessages: false,
    selectedTopic: '',
    selectedThreadId: 'new',
    files: [] as File[],
});

const messageInput = ref();
const threadContainer = ref<HTMLElement | null>(null);

// The widget emits the Message Type list item's display label, single-select.
const onTopicSelected = (displayValues: string[]) => {
    state.selectedTopic = displayValues[0] ?? '';
};

// The file widget emits an entry per staged file; the raw File rides in .file.
// Keep those, so createBcapMessage can post them as multipart.
const onFilesSelected = (value: Array<{ file?: File }>) => {
    state.files = (value ?? [])
        .map((entry) => entry.file)
        .filter((file): file is File => Boolean(file));
};

const removeFile = (index: number) => {
    state.files.splice(index, 1);
};

const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const visibleThreads = computed(() =>
    messageStore.threadsFor(props.resourceId, state.showArchived),
);

const unreadCount = computed(() => messageStore.unreadCount(props.resourceId));

const activeThread = computed(
    () =>
        visibleThreads.value.find(
            (thread) => thread.id === state.selectedThreadId,
        ) || null,
);

const isReplyMode = computed(() => {
    return state.selectedThreadId !== 'new' && activeThread.value !== null;
});

// A message needs text; a new thread also needs a message type. Replies inherit
// their thread's type, so they only need text.
const canSend = computed(
    () => !!state.messageText && (isReplyMode.value || !!state.selectedTopic),
);

const showTab = async (archived: boolean) => {
    state.showArchived = archived;
    state.selectedThreadId = 'new';
    messageStore.openMessages = [];
    await messageStore.load(props.resourceId, archived);
};

const loadRecipients = async () => {
    state.isLoadingRecipients = true;
    try {
        state.recipients = await getContributorsForResources(props.resourceId);
        // A module resource may have no contributors of its own; the message
        // still files against it, unaddressed.
        state.selectedRecipient = state.recipients[0]?.value ?? '';
    } catch (error) {
        console.error('Error loading recipients:', error);
        state.recipients = [];
        state.selectedRecipient = '';
    } finally {
        state.isLoadingRecipients = false;
    }
};

const openDialog = () => {
    state.selectedThreadId = 'new';
    state.visible = true;
    messageStore.load(props.resourceId, state.showArchived);
};

const closeDialog = () => {
    state.visible = false;
    state.messageText = '';
    state.subjectText = '';
    state.selectedTopic = '';
    state.files = [];
    messageStore.openMessages = [];
};

const selectThread = async (threadId: string) => {
    state.selectedThreadId = threadId;
    state.messageText = '';
    state.files = [];

    const thread = activeThread.value;
    if (thread) {
        state.isLoadingMessages = true;
        try {
            await messageStore.loadThreadMessages(threadId);
            await messageStore.markThreadRead(thread);
        } finally {
            state.isLoadingMessages = false;
        }
    }

    await nextTick();
    if (messageInput.value) {
        messageInput.value.$el.focus({ preventScroll: true });
    }
    requestAnimationFrame(() => {
        if (threadContainer.value) {
            threadContainer.value.scrollTop =
                threadContainer.value.scrollHeight;
        }
    });
};

const submitMessage = async () => {
    if (!canSend.value) return;

    state.isSubmitting = true;

    try {
        const targetThreadId = isReplyMode.value
            ? activeThread.value?.id
            : undefined;

        // "General Question - setback dimensions": the message type, with the
        // optional free-text subject appended when one was entered.
        const detail = state.subjectText.trim();
        const subject = detail
            ? `${state.selectedTopic} - ${detail}`
            : state.selectedTopic;

        await messageStore.send({
            messageText: state.messageText,
            recipientId: state.selectedRecipient as string,
            applicationId: props.applicationId,
            resourceId: props.resourceId,
            threadId: targetThreadId,
            topic: isReplyMode.value ? undefined : subject || undefined,
            files: state.files,
        });

        closeDialog();
    } catch (error) {
        console.error('Error submitting message:', error);
        alert('There was an error sending your message. Please try again.');
    } finally {
        state.isSubmitting = false;
    }
};

// Resolving archives the thread for this viewer only, so it moves to the
// archived tab rather than disappearing.
const markAsResolved = async () => {
    if (!activeThread.value) return;
    const threadId = activeThread.value.id;
    state.isResolving = true;
    try {
        await messageStore.setArchived(
            threadId,
            !state.showArchived,
            props.resourceId,
        );
        state.selectedThreadId = 'new';
    } finally {
        state.isResolving = false;
    }
};

onMounted(() => {
    loadRecipients();
    // To show the counts.
    messageStore.load(props.resourceId, state.showArchived);
});
</script>

<template>
    <div class="ask-question-trigger">
        <Button
            severity="secondary"
            class="trigger-btn"
            @click="openDialog"
        >
            <i class="fa-regular fa-comment-dots"></i>
            <span class="trigger-label">Messages</span>

            <span
                v-if="unreadCount"
                class="message-badge"
            >
                {{ unreadCount }}
            </span>
        </Button>
    </div>

    <Dialog
        v-model:visible="state.visible"
        modal
        :closable="true"
        :style="{ width: '1050px', maxWidth: '95vw' }"
        :pt="{
            root: { class: 'message-dialog' },
            header: { class: 'message-dialog-header' },
            closeButton: { class: 'message-dialog-close' },
            content: { style: { padding: '0', overflow: 'hidden' } },
        }"
    >
        <template #header>
            <span class="header-block">
                <span class="header-title">Messages</span>
                <span class="header-subtitle">
                    {{ context || 'Permit Application' }}
                    <template v-if="contextId">· {{ contextId }}</template>
                </span>
            </span>
        </template>

        <template #closeicon>
            <i class="fa-solid fa-xmark custom-close-icon"></i>
        </template>

        <!-- SPLIT LAYOUT CONTAINER -->
        <div class="dialog-body-split">
            <!-- SIDEBAR -->
            <div class="thread-sidebar">
                <div class="sidebar-tabs">
                    <button
                        type="button"
                        class="sidebar-tab"
                        :class="{ active: !state.showArchived }"
                        @click="showTab(false)"
                    >
                        Active
                    </button>
                    <button
                        type="button"
                        class="sidebar-tab"
                        :class="{ active: state.showArchived }"
                        @click="showTab(true)"
                    >
                        Archived
                    </button>
                </div>

                <div class="thread-list">
                    <div
                        v-for="thread in visibleThreads"
                        :key="thread.id"
                        class="sidebar-item"
                        :class="{
                            active: state.selectedThreadId === thread.id,
                            unread: thread.hasUnread,
                            resolved: thread.isResolved,
                        }"
                        @click="selectThread(thread.id)"
                    >
                        <span class="thread-topic-label">
                            {{ thread.topic }}
                        </span>
                        <span class="thread-started-by">
                            {{ thread.startedBy }}
                        </span>
                        <span
                            v-if="thread.lastMessageDate"
                            class="thread-date"
                        >
                            {{ formatTimestamp(thread.lastMessageDate) }}
                        </span>
                    </div>

                    <div
                        v-if="visibleThreads.length === 0"
                        class="sidebar-item empty-note"
                    >
                        {{
                            state.showArchived
                                ? 'No archived messages.'
                                : 'No messages.'
                        }}
                    </div>
                </div>

                <div
                    class="sidebar-item new-message-item"
                    :class="{ active: state.selectedThreadId === 'new' }"
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
                    <div class="field-row">
                        <div class="field-col">
                            <label class="field-label">Recipient</label>
                            <Dropdown
                                v-model="state.selectedRecipient"
                                :options="state.recipients"
                                :loading="state.isLoadingRecipients"
                                option-label="label"
                                option-value="value"
                                placeholder="Select Recipient"
                                append-to="body"
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
                                                state.recipients.find(
                                                    (r) =>
                                                        r.value ===
                                                        slotProps.value,
                                                )?.label
                                            }}
                                        </span>
                                    </div>
                                    <span
                                        v-else
                                        style="
                                            font-size: 1.25rem;
                                            color: #6c757d;
                                        "
                                    >
                                        {{ slotProps.placeholder }}
                                    </span>
                                </template>
                                <template #option="slotProps">
                                    <div class="dropdown-value-template">
                                        <i class="fa-regular fa-envelope"></i>
                                        <span>
                                            {{ slotProps.option.label }}
                                        </span>
                                    </div>
                                </template>
                            </Dropdown>
                        </div>

                        <div class="field-col">
                            <label class="field-label">
                                Message type
                                <span
                                    class="field-required"
                                    aria-hidden="true"
                                >
                                    *
                                </span>
                            </label>
                            <div class="type-widget">
                                <GenericWidget
                                    :graph-slug="GraphSlug.BcapMessage"
                                    node-alias="message_type"
                                    mode="edit"
                                    should-emit-simplified-value
                                    @update:value="onTopicSelected"
                                />
                            </div>
                        </div>
                    </div>

                    <div class="field-block">
                        <label class="field-label">
                            Subject
                            <span class="field-optional">(optional)</span>
                        </label>
                        <input
                            v-model="state.subjectText"
                            type="text"
                            class="subject-input"
                            placeholder="e.g. Setback dimensions on sheet A-2"
                        />
                    </div>

                    <div class="field-block textarea-wrapper">
                        <label class="field-label">Message</label>
                        <Textarea
                            ref="messageInput"
                            v-model="state.messageText"
                            maxlength="4000"
                            placeholder="Type your message…"
                            class="full-width-textarea"
                        />
                    </div>

                    <div class="field-block attachments-field">
                        <label class="field-label">
                            Attachments
                            <span class="field-optional">(optional)</span>
                        </label>
                        <div class="attachments-widget">
                            <GenericWidget
                                :key="state.selectedThreadId"
                                :graph-slug="GraphSlug.BcapMessage"
                                node-alias="attachments"
                                mode="edit"
                                should-emit-simplified-value
                                @update:value="onFilesSelected"
                            />
                        </div>

                        <ul
                            v-if="state.files.length"
                            class="staged-attachments"
                        >
                            <li
                                v-for="(file, index) in state.files"
                                :key="`${file.name}-${index}`"
                            >
                                <i class="fa-regular fa-paperclip"></i>
                                <span class="staged-name">{{ file.name }}</span>
                                <span class="staged-size">
                                    {{ formatFileSize(file.size) }}
                                </span>
                                <button
                                    type="button"
                                    class="staged-remove"
                                    aria-label="Remove attachment"
                                    @click="removeFile(index)"
                                >
                                    <i class="fa-solid fa-xmark"></i>
                                </button>
                            </li>
                        </ul>
                    </div>

                    <div class="action-footer">
                        <Button
                            label="Send"
                            class="send-btn"
                            :loading="state.isSubmitting"
                            :disabled="!canSend"
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
                            v-if="state.isLoadingMessages"
                            class="messages-loading"
                        >
                            <i class="fa-solid fa-spinner fa-spin"></i>
                            Loading messages…
                        </div>
                        <template v-else>
                            <div
                                v-for="(
                                    msg, index
                                ) in messageStore.openMessages"
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
                                                    downloadFile(
                                                        file.url,
                                                        file.name,
                                                    )
                                                "
                                            >
                                                <i
                                                    class="fa-regular fa-paperclip"
                                                ></i>
                                                <span class="attachment-name">
                                                    {{ file.name }}
                                                </span>
                                                <span
                                                    v-if="file.size"
                                                    class="attachment-size"
                                                >
                                                    {{
                                                        formatFileSize(
                                                            file.size,
                                                        )
                                                    }}
                                                </span>
                                            </a>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </template>
                    </div>

                    <div class="field-container textarea-wrapper">
                        <label class="field-label">Write a Reply:</label>
                        <Textarea
                            ref="messageInput"
                            v-model="state.messageText"
                            rows="4"
                            class="full-width-textarea"
                        />
                    </div>

                    <div class="field-block attachments-field">
                        <label class="field-label">
                            Attachments
                            <span class="field-optional">(optional)</span>
                        </label>
                        <div class="attachments-widget">
                            <GenericWidget
                                :key="state.selectedThreadId"
                                :graph-slug="GraphSlug.BcapMessage"
                                node-alias="attachments"
                                mode="edit"
                                should-emit-simplified-value
                                @update:value="onFilesSelected"
                            />
                        </div>

                        <ul
                            v-if="state.files.length"
                            class="staged-attachments"
                        >
                            <li
                                v-for="(file, index) in state.files"
                                :key="`${file.name}-${index}`"
                            >
                                <i class="fa-regular fa-paperclip"></i>
                                <span class="staged-name">{{ file.name }}</span>
                                <span class="staged-size">
                                    {{ formatFileSize(file.size) }}
                                </span>
                                <button
                                    type="button"
                                    class="staged-remove"
                                    aria-label="Remove attachment"
                                    @click="removeFile(index)"
                                >
                                    <i class="fa-solid fa-xmark"></i>
                                </button>
                            </li>
                        </ul>
                    </div>

                    <div class="action-footer">
                        <Button
                            :label="
                                state.showArchived
                                    ? 'Restore'
                                    : 'Mark as Resolved'
                            "
                            class="resolve-btn"
                            :loading="state.isResolving"
                            @click="markAsResolved"
                        />
                        <Button
                            label="Send"
                            class="send-btn"
                            :loading="state.isSubmitting"
                            :disabled="!canSend"
                            @click="submitMessage"
                        />
                    </div>
                </div>
            </div>
        </div>
    </Dialog>
</template>

<style>
.trigger-btn {
    background-color: var(--bc-navy);
    color: #ffffff;
    border: 2px solid var(--bc-navy);
    border-radius: 4px;
    padding: 0.7rem 1.6rem;
    font-size: 1.4rem;
    font-weight: 700;
    line-height: 1.2;
    display: flex;
    align-items: center;
    gap: 0.6rem;
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

.message-dialog-header .header-block {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    line-height: 1.25;
}

.message-dialog-header .header-title {
    font-weight: 700;
    font-size: 1.6rem;
    letter-spacing: 0.01em;
}

.message-dialog-header .header-subtitle {
    font-size: 1.15rem;
    font-weight: 400;
    color: rgba(255, 255, 255, 0.75);
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

.dialog-body-split {
    display: flex;
    height: min(80vh, 760px);
    background-color: #f8f9fa;
}

.thread-sidebar {
    width: 320px;
    background-color: #ffffff;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
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

.sidebar-item.active .thread-started-by {
    color: rgba(255, 255, 255, 0.9);
}

.thread-date {
    display: block;
    margin-top: 0.3rem;
    font-size: 1.1rem;
    color: #6c757d;
}

.sidebar-item.active .thread-date {
    color: rgba(255, 255, 255, 0.85);
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

.thread-content {
    flex: 1;
    padding: 1.5rem 1.5rem 0;
    background-color: var(--bc-panel);
    display: flex;
    flex-direction: column;
    overflow: hidden; /* Prevent internal elements from breaking layout */
}

.new-question-view,
.reply-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow-y: auto;
}

.field-container {
    width: 100%;
}

.field-row {
    display: flex;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}

.field-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.field-col .p-select,
.field-col .p-dropdown {
    width: 100%;
    height: 3.5rem;
    align-items: center;
    border-radius: 6px;
}

.type-widget label {
    display: none !important;
}

.attachments-widget label {
    display: none !important;
}

.attachments-widget input[type='file'] {
    display: none;
}

/* The message-type widget is a PrimeVue TreeSelect; match the Recipient
   dropdown's height, radius and font so the two columns line up. */
.type-widget .p-treeselect {
    width: 100%;
    height: 3.5rem !important;
    align-items: center;
    border-radius: 6px;
}

.type-widget,
.type-widget .p-treeselect,
.type-widget .p-treeselect-label,
.type-widget .p-placeholder {
    font-size: 1.25rem !important;
    line-height: 1.4;
}

.field-block {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}

.attachments-field {
    margin-top: 1.25rem;
}

.field-optional {
    font-weight: 400;
    color: #6c757d;
}

.field-required {
    color: #d32f2f;
    font-weight: 700;
}

.subject-input {
    width: 100%;
    box-sizing: border-box;
    height: 3.5rem;
    padding: 0 1rem;
    font-size: 1.25rem;
    color: #333;
    border: 1px solid #ced4da;
    border-radius: 6px;
}

.subject-input::placeholder {
    color: #9aa2ab;
}

.new-question-view .textarea-wrapper {
    margin-top: 0;
    flex: 0 0 auto;
}

.new-question-view .textarea-wrapper .full-width-textarea {
    min-height: 12rem;
    resize: vertical;
}

.reply-view .full-width-textarea {
    min-height: 9rem;
    resize: vertical;
}

.reply-view .textarea-wrapper {
    margin-top: 0;
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
    font-size: 1.3rem;
    font-weight: 600;
}

.full-width-textarea {
    width: 100% !important;
    box-sizing: border-box;
    border-radius: 6px;
    border-color: #ced4da;
    font-size: 1.25rem;
}

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

.attachments-widget .file-list {
    display: none !important;
}

.attachments-widget .p-fileupload,
.attachments-widget .p-fileupload-content {
    padding: 0;
    border: none;
    background: transparent;
}

.staged-attachments {
    list-style: none;
    margin: 0.6rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    flex: 0 0 auto;
}

.staged-attachments li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-shrink: 0;
    padding: 0.5rem 0.9rem;
    background-color: #eef2f7;
    border: 1px solid #d6dee8;
    border-radius: 8px;
    font-size: 1.2rem;
    color: var(--bc-navy);
}

.staged-name {
    flex: 1 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.staged-size {
    flex: 0 0 auto;
    font-size: 1.05rem;
    color: #6c757d;
}

.staged-remove {
    flex: 0 0 auto;
    border: none;
    background: none;
    cursor: pointer;
    padding: 0.2rem 0.4rem;
    font-size: 1.2rem;
    color: #6c757d;
}

.staged-remove:hover {
    color: #d32f2f;
}

.action-footer {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    /* auto pushes it to the bottom when content is short; sticky keeps it in
       view when the compose area scrolls. */
    margin-top: auto;
    position: sticky;
    bottom: 0;
    padding: 0.75rem 0;
    background-color: var(--bc-panel);
}

.send-btn,
.resolve-btn {
    padding: 0.8rem 1.8rem;
    border-radius: 4px;
    font-size: 1.25rem;
    font-weight: 700;
}

/* PrimeVue's label span carries its own weight/size, so set it on the label. */
.send-btn .p-button-label,
.resolve-btn .p-button-label {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
}

.send-btn {
    background-color: var(--bc-navy);
    border: 2px solid var(--bc-navy);
    color: #ffffff;
}

.send-btn:hover {
    background-color: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
}

.resolve-btn {
    background-color: #ffffff;
    border: 2px solid var(--bc-navy);
    color: var(--bc-navy);
}

.resolve-btn:hover {
    background-color: var(--bc-selected);
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

.sidebar-item.empty-note {
    color: #6c757d;
    cursor: default;
}
</style>
