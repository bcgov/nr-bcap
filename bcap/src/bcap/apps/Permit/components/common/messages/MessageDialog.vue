<script setup lang="ts">
import { reactive, ref, computed, nextTick, onMounted } from 'vue';
import Dialog from 'primevue/dialog';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';
import { getContributorsForResources } from '@/bcap/apps/Permit/api.ts';
import { useMessageStore } from '@/bcap/stores/message.ts';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import MessageThreadSidebar from '@/bcap/apps/Permit/components/common/messages/MessageThreadSidebar.vue';
import MessageHistory from '@/bcap/apps/Permit/components/common/messages/MessageHistory.vue';
import MessageAttachmentsField from '@/bcap/apps/Permit/components/common/messages/MessageAttachmentsField.vue';
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
    loadRecipients();
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

        <div class="dialog-body-split">
            <MessageThreadSidebar
                :threads="visibleThreads"
                :show-archived="state.showArchived"
                :selected-thread-id="state.selectedThreadId"
                @select-tab="showTab"
                @select-thread="selectThread"
            />

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

                    <MessageAttachmentsField
                        v-model:files="state.files"
                        :reset-key="state.selectedThreadId"
                    />

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
                    <MessageHistory
                        ref="threadContainer"
                        :messages="messageStore.openMessages"
                        :is-loading="state.isLoadingMessages"
                    />

                    <div class="field-container textarea-wrapper">
                        <label class="field-label">Write a Reply:</label>
                        <Textarea
                            ref="messageInput"
                            v-model="state.messageText"
                            rows="4"
                            class="full-width-textarea"
                        />
                    </div>

                    <MessageAttachmentsField
                        v-model:files="state.files"
                        :reset-key="state.selectedThreadId"
                    />

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
</style>
