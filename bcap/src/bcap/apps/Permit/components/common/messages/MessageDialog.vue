<script setup lang="ts">
import { reactive, ref, computed, nextTick, onMounted, watch } from 'vue';
import Dialog from 'primevue/dialog';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';
import { getContributorsForResources } from '@/bcap/apps/Permit/api.ts';
import { formatTimestamp } from '@/bcap/util.ts';
import { useMessageStore } from '@/bcap/stores/message.ts';
import { useUserStore } from '@/bcap/stores/user.ts';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import MessageThreadSidebar from '@/bcap/apps/Permit/components/common/messages/MessageThreadSidebar.vue';
import MessageHistory from '@/bcap/apps/Permit/components/common/messages/MessageHistory.vue';
import MessageAttachmentsField from '@/bcap/apps/Permit/components/common/messages/MessageAttachmentsField.vue';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';
import type { ReferenceAliasedNodeDataWritable } from '@/bcap/client/types.gen.ts';
import { NEW_THREAD_ID } from '@/bcap/types.ts';
import type { RecipientOption } from '@/bcap/types.ts';
import { inlineMessage } from '@/bcap/notify.ts';
import InlineError from '@/bcap/components/InlineError.vue';

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
    // The host has just loaded this resource's threads, so skip it on mount.
    prefetched?: boolean;
}>();

const messageStore = useMessageStore();
const userStore = useUserStore();

const state = reactive({
    visible: false,
    showArchived: false,
    messageText: '',
    subjectText: '',
    isSubmitting: false,
    isArchiving: false,
    isResolving: false,
    selectedRecipient: '',
    recipients: [] as RecipientOption[],
    isLoadingRecipients: false,
    isLoadingMessages: false,
    selectedTopic: '',
    selectedTopicValue: [] as ReferenceAliasedNodeDataWritable['node_value'],
    selectedThreadId: NEW_THREAD_ID,
    files: [] as File[],
    error: '',
    // Shown beside the Send button, where the user is looking, until they
    // change the attachments, switch threads or try again.
    sendError: '',
    // Reply box height set by dragging its handle; 0 keeps the default.
    composerHeight: 0,
});

watch(
    () => [state.files, state.selectedThreadId, state.visible],
    () => (state.sendError = ''),
);

// One slot at the top for whatever failed to load; sending reports itself at
// the bottom, next to the button that triggered it.
const dialogError = computed(() => state.error || messageStore.error);

const messageInput = ref();

// The topic is used as a label, so read display_value: node_value is a list of
// reference objects, not strings.
const onTopicSelected = (node: AliasedNodeData) => {
    state.selectedTopic = node.display_value ?? '';
    state.selectedTopicValue = (node.node_value ??
        []) as ReferenceAliasedNodeDataWritable['node_value'];
};

const visibleThreads = computed(() =>
    messageStore.threadsFor(props.resourceId, state.showArchived),
);

const unresolvedCount = computed(() =>
    messageStore.unresolvedCount(props.resourceId),
);

const activeThread = computed(
    () =>
        visibleThreads.value.find(
            (thread) => thread.id === state.selectedThreadId,
        ) || null,
);

const isReplyMode = computed(() => activeThread.value !== null);

const selectedRecipient = computed(() =>
    state.recipients.find((r) => r.value === state.selectedRecipient),
);

const sendModifier = /Mac|iPhone|iPad/.test(navigator.userAgent) ? '⌘' : 'Ctrl';

const recipientIcon = (option?: RecipientOption) =>
    option?.isInternal ? 'fa-solid fa-lock' : 'fa-solid fa-users';

const canSend = computed(
    () =>
        !!state.messageText &&
        (isReplyMode.value ||
            (!!state.selectedTopic &&
                !!state.selectedRecipient &&
                !!state.subjectText.trim())),
);

const showTab = async (archived: boolean) => {
    state.showArchived = archived;
    state.selectedThreadId = NEW_THREAD_ID;
    messageStore.openMessages = [];
    await messageStore.load(props.resourceId, archived);
};

const loadRecipients = async () => {
    state.isLoadingRecipients = true;
    state.error = '';
    try {
        state.recipients = await getContributorsForResources(props.resourceId);
        // A module resource may have no contributors of its own; the message
        // still files against it, unaddressed.
        state.selectedRecipient = state.recipients[0]?.value ?? '';
    } catch (error) {
        state.error = `The list of recipients could not be loaded. ${inlineMessage(error)}`;
        state.recipients = [];
        state.selectedRecipient = '';
    } finally {
        state.isLoadingRecipients = false;
    }
};

const openDialog = () => {
    state.selectedThreadId = NEW_THREAD_ID;
    state.visible = true;
    loadRecipients();
    messageStore.load(props.resourceId, state.showArchived);
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
        } finally {
            state.isLoadingMessages = false;
        }
        // For now an applicant resolves their side just by reading it.
        if (!userStore.isInternal && thread.onSide && !thread.isResolved) {
            await messageStore.updateThread(
                threadId,
                { resolved: true },
                props.resourceId,
            );
        }
    }

    await nextTick();
    if (messageInput.value) {
        messageInput.value.$el.focus({ preventScroll: true });
    }
};

const COMPOSER_MIN = 80;
const COMPOSER_MAX = 480;
const setComposerHeight = (px: number) => {
    state.composerHeight = Math.min(COMPOSER_MAX, Math.max(COMPOSER_MIN, px));
};

// Dragging the handle up grows the reply box and shrinks the history above.
const startComposerResize = (event: PointerEvent) => {
    const startY = event.clientY;
    const startHeight = messageInput.value?.$el.offsetHeight ?? COMPOSER_MIN;
    const onMove = (move: PointerEvent) =>
        setComposerHeight(startHeight + startY - move.clientY);
    const onUp = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
};

const nudgeComposer = (px: number) =>
    setComposerHeight(
        (state.composerHeight ||
            messageInput.value?.$el.offsetHeight ||
            COMPOSER_MIN) + px,
    );

const submitMessage = async () => {
    if (!canSend.value) return;

    state.isSubmitting = true;
    state.sendError = '';

    try {
        const targetThreadId = isReplyMode.value
            ? activeThread.value?.id
            : undefined;

        const subject = state.subjectText.trim();

        const created = await messageStore.send({
            messageText: state.messageText,
            recipientId: state.selectedRecipient,
            resourceId: props.resourceId,
            threadId: targetThreadId,
            topic: isReplyMode.value ? undefined : subject || undefined,
            messageType: isReplyMode.value
                ? undefined
                : state.selectedTopicValue,
            files: state.files,
        });

        const threadId = targetThreadId ?? created?.resourceinstanceid;
        state.messageText = '';
        state.subjectText = '';
        state.selectedTopic = '';
        state.selectedTopicValue = [];
        state.files = [];
        if (threadId) {
            state.showArchived = false;
            state.selectedThreadId = threadId;
            await messageStore.loadThreadMessages(threadId);
        }
    } catch (error) {
        state.sendError = inlineMessage(error);
    } finally {
        state.isSubmitting = false;
    }
};

// Archiving is this viewer's only, so the thread moves to the archived tab
// rather than disappearing.
const toggleArchived = async () => {
    if (!activeThread.value) return;
    const threadId = activeThread.value.id;
    state.isArchiving = true;
    try {
        await messageStore.updateThread(
            threadId,
            { archived: !state.showArchived },
            props.resourceId,
        );
        state.selectedThreadId = NEW_THREAD_ID;
    } finally {
        state.isArchiving = false;
    }
};

// Resolution is per side, so it clears the alert for everyone on the viewer's.
const toggleResolved = async () => {
    if (!activeThread.value) return;
    state.isResolving = true;
    try {
        await messageStore.updateThread(
            activeThread.value.id,
            { resolved: !activeThread.value.isResolved },
            props.resourceId,
        );
    } finally {
        state.isResolving = false;
    }
};

onMounted(() => {
    // To show the counts.
    if (!props.prefetched)
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
                v-if="unresolvedCount"
                class="message-badge"
            >
                {{ unresolvedCount }}
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
            content: { class: 'message-dialog-content' },
        }"
        @hide="messageStore.reloadModuleUnresolved()"
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

        <InlineError
            v-if="dialogError"
            title="Something went wrong."
            :detail="dialogError"
            class="dialog-error"
        />

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
                    <div class="thread-header">
                        <h3 class="thread-title">New message</h3>
                    </div>
                    <div class="field-row">
                        <div class="field-col">
                            <label class="field-label">
                                Recipient
                                <span
                                    class="field-required"
                                    aria-hidden="true"
                                >
                                    *
                                </span>
                            </label>
                            <Dropdown
                                v-model="state.selectedRecipient"
                                :options="state.recipients"
                                :loading="state.isLoadingRecipients"
                                option-label="label"
                                option-value="value"
                                placeholder="Select Recipient"
                                append-to="body"
                                class="w-full"
                            >
                                <template #value="slotProps">
                                    <div
                                        v-if="
                                            slotProps.value !== null &&
                                            slotProps.value !== undefined
                                        "
                                        class="dropdown-value-template"
                                    >
                                        <i
                                            v-if="userStore.isInternal"
                                            :class="
                                                recipientIcon(selectedRecipient)
                                            "
                                        ></i>
                                        <span>
                                            {{ selectedRecipient?.label }}
                                        </span>
                                    </div>
                                    <span
                                        v-else
                                        class="recipient-placeholder"
                                    >
                                        {{ slotProps.placeholder }}
                                    </span>
                                </template>
                                <template #option="slotProps">
                                    <div class="dropdown-value-template">
                                        <i
                                            v-if="userStore.isInternal"
                                            :class="
                                                recipientIcon(slotProps.option)
                                            "
                                        ></i>
                                        <span>
                                            {{ slotProps.option.label }}
                                            <template
                                                v-if="userStore.isInternal"
                                            >
                                                {{
                                                    slotProps.option.isInternal
                                                        ? '(Internal)'
                                                        : '(External)'
                                                }}
                                            </template>
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
                                    @update:aliased-node-data="onTopicSelected"
                                />
                            </div>
                        </div>
                    </div>

                    <!-- Staff only: an applicant's threads are always external. -->
                    <div
                        v-if="userStore.isInternal && selectedRecipient"
                        class="internal-note"
                        :class="
                            selectedRecipient.isInternal
                                ? 'is-internal'
                                : 'is-external'
                        "
                    >
                        <i :class="recipientIcon(selectedRecipient)"></i>
                        <span v-if="selectedRecipient.isInternal">
                            <strong>Internal thread.</strong>
                            Only staff can see this conversation. The applicant
                            will not be notified.
                        </span>
                        <span v-else>
                            <strong>External thread.</strong>
                            This conversation is shared with the applicant.
                        </span>
                    </div>

                    <div class="field-block">
                        <label class="field-label">
                            Subject
                            <span
                                class="field-required"
                                aria-hidden="true"
                            >
                                *
                            </span>
                        </label>
                        <input
                            v-model="state.subjectText"
                            type="text"
                            class="subject-input"
                            placeholder="e.g. Setback dimensions on sheet A-2"
                        />
                    </div>

                    <label class="field-label">
                        Message
                        <span
                            class="field-required"
                            aria-hidden="true"
                        >
                            *
                        </span>
                    </label>
                    <div class="composer">
                        <Textarea
                            ref="messageInput"
                            v-model="state.messageText"
                            maxlength="4000"
                            placeholder="Type your message…"
                            class="composer-input new-message-input"
                            @keydown.ctrl.enter.prevent="submitMessage"
                            @keydown.meta.enter.prevent="submitMessage"
                        />
                        <div class="composer-footer">
                            <MessageAttachmentsField
                                v-model:files="state.files"
                                :reset-key="state.selectedThreadId"
                            />
                            <span class="send-hint">
                                <kbd>{{ sendModifier }}</kbd>
                                +
                                <kbd>Enter</kbd>
                            </span>
                            <Button
                                label="Send"
                                class="send-btn"
                                :loading="state.isSubmitting"
                                :disabled="!canSend"
                                @click="submitMessage"
                            />
                        </div>
                    </div>
                    <InlineError
                        v-if="state.sendError"
                        title="Your message could not be sent."
                        :detail="state.sendError"
                        class="send-error"
                    />
                </div>

                <!-- REPLY VIEW -->
                <div
                    v-else
                    class="reply-view"
                >
                    <div
                        v-if="activeThread"
                        class="thread-header"
                    >
                        <div class="thread-status">
                            <h3 class="thread-title">
                                {{ activeThread.topic }}
                            </h3>
                            <div class="thread-meta">
                                <span
                                    v-if="activeThread.to"
                                    class="thread-to"
                                >
                                    <!-- Someone on neither side sees both parties. -->
                                    <template v-if="activeThread.onSide">
                                        With
                                        <strong>{{ activeThread.to }}</strong>
                                    </template>
                                    <template v-else>
                                        Between
                                        <strong>
                                            {{ activeThread.startedBy }}
                                        </strong>
                                        and
                                        <strong>{{ activeThread.to }}</strong>
                                    </template>
                                </span>
                                <!-- Staff only: an applicant sees neither kind nor resolution. -->
                                <div
                                    v-if="userStore.isInternal"
                                    class="thread-tags"
                                >
                                    <span
                                        v-if="activeThread.isInternal"
                                        class="thread-tag internal-tag"
                                    >
                                        <i class="fa-solid fa-lock"></i>
                                        Internal · staff only
                                    </span>
                                    <span
                                        v-else
                                        class="thread-tag external-tag"
                                    >
                                        <i class="fa-solid fa-users"></i>
                                        External · shared with applicant
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="thread-actions">
                            <!-- Archive sits left so the resolve button never moves. -->
                            <Button
                                v-if="
                                    state.showArchived ||
                                    activeThread?.isResolved ||
                                    !activeThread?.onSide
                                "
                                :label="
                                    state.showArchived ? 'Unarchive' : 'Archive'
                                "
                                :icon="
                                    state.showArchived
                                        ? 'fa-solid fa-box-open'
                                        : 'fa-solid fa-box-archive'
                                "
                                class="resolve-btn archive-btn"
                                :loading="state.isArchiving"
                                @click="toggleArchived"
                            />
                            <template
                                v-if="
                                    !state.showArchived &&
                                    userStore.isInternal &&
                                    activeThread?.onSide
                                "
                            >
                                <Button
                                    :label="
                                        activeThread?.isResolved
                                            ? 'Reopen'
                                            : 'Mark as resolved'
                                    "
                                    :icon="
                                        activeThread?.isResolved
                                            ? 'fa-solid fa-rotate-left'
                                            : 'fa-solid fa-check'
                                    "
                                    class="resolve-btn"
                                    :class="{
                                        'is-primary': !activeThread?.isResolved,
                                    }"
                                    :loading="state.isResolving"
                                    @click="toggleResolved"
                                />
                            </template>
                        </div>
                    </div>

                    <div
                        v-if="userStore.isInternal && activeThread?.isResolved"
                        class="resolved-banner"
                    >
                        <i class="fa-solid fa-circle-check"></i>
                        <span>
                            Resolved
                            <template v-if="activeThread.resolvedBy">
                                by
                                <strong>{{ activeThread.resolvedBy }}</strong>
                            </template>
                            <template v-if="activeThread.resolvedDate">
                                on
                                {{ formatTimestamp(activeThread.resolvedDate) }}
                            </template>
                        </span>
                    </div>

                    <MessageHistory
                        :thread-id="state.selectedThreadId"
                        :is-loading="
                            state.isLoadingMessages || state.isSubmitting
                        "
                    />

                    <div
                        class="composer-resizer"
                        role="separator"
                        aria-orientation="horizontal"
                        aria-label="Resize the reply box"
                        tabindex="0"
                        @pointerdown.prevent="startComposerResize"
                        @keydown.up.prevent="nudgeComposer(20)"
                        @keydown.down.prevent="nudgeComposer(-20)"
                    >
                        <span class="composer-grip"></span>
                    </div>

                    <div class="composer reply-composer">
                        <Textarea
                            ref="messageInput"
                            v-model="state.messageText"
                            rows="4"
                            placeholder="Write a reply…"
                            aria-label="Write a reply"
                            class="composer-input"
                            :style="
                                state.composerHeight
                                    ? { height: `${state.composerHeight}px` }
                                    : undefined
                            "
                            @keydown.ctrl.enter.prevent="submitMessage"
                            @keydown.meta.enter.prevent="submitMessage"
                        />
                        <div class="composer-footer">
                            <MessageAttachmentsField
                                v-model:files="state.files"
                                :reset-key="state.selectedThreadId"
                            />
                            <span class="send-hint">
                                <kbd>{{ sendModifier }}</kbd>
                                +
                                <kbd>Enter</kbd>
                            </span>
                            <Button
                                label="Send"
                                class="send-btn"
                                :loading="state.isSubmitting"
                                :disabled="!canSend"
                                @click="submitMessage"
                            />
                        </div>
                    </div>
                    <InlineError
                        v-if="state.sendError"
                        title="Your message could not be sent."
                        :detail="state.sendError"
                        class="send-error"
                    />
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

.p-dialog.message-dialog .message-dialog-content {
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: min(80vh, 760px);
}

.dialog-body-split {
    display: flex;
    flex: 1;
    min-height: 0;
    background-color: #f8f9fa;
}

.thread-content {
    flex: 1;
    padding: 1.5rem 1.5rem 0;
    background-color: var(--bc-panel);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.new-question-view,
.reply-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow-y: auto;
    padding-bottom: 1.25rem;
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

.field-col .p-select-label {
    font-size: 1.25rem;
    line-height: 1.4;
}

.field-col .p-select-dropdown,
.field-col .p-treeselect-dropdown {
    color: var(--bc-muted) !important;
}

.field-col .p-select.p-focus,
.field-col .p-select:focus-within,
.field-col .p-treeselect.p-focus,
.field-col .p-treeselect:focus-within {
    border-color: var(--bc-border) !important;
    box-shadow: none !important;
    outline: none !important;
}

.type-widget label {
    display: none !important;
}

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

.field-label {
    display: block;
    margin-bottom: 0.5rem;
    color: #333;
    font-size: 1.3rem;
    font-weight: 600;
}

.composer {
    display: flex;
    flex-direction: column;
    flex: 0 0 auto;
    background: #ffffff;
    border: 1px solid #ced4da;
    border-radius: 6px;
}

.composer:focus-within {
    border-color: var(--bc-navy);
    outline: 1px solid var(--bc-navy);
    outline-offset: -2px;
}

.composer .composer-input:focus,
.composer .composer-input:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}

.composer .composer-input {
    width: 100%;
    min-height: 9rem;
    resize: vertical;
    font-size: 1.25rem;
    border: none !important;
    border-radius: 6px 6px 0 0;
    box-shadow: none !important;
}

.new-question-view .composer {
    flex: 1 1 auto;
    min-height: 18rem;
}

.composer .new-message-input {
    flex: 1 1 auto;
    min-height: 12rem;
    resize: none;
}

.reply-composer {
    margin-top: auto;
}

.reply-composer .composer-input {
    resize: none;
}

.composer-resizer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 1.5rem;
    cursor: row-resize;
    touch-action: none;
}

.composer-grip {
    width: 4rem;
    height: 4px;
    border-radius: 2px;
    background-color: #cbd5e1;
}

.composer-resizer:hover .composer-grip,
.composer-resizer:focus-visible .composer-grip {
    background-color: var(--bc-muted);
}

.send-hint {
    flex-shrink: 0;
    font-size: 1.05rem;
    color: var(--bc-muted);
}

.composer-footer {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 0.75rem;
    border-top: 1px solid #e5e7eb;
    border-radius: 0 0 6px 6px;
    background: #fafbfc;
}

.composer-footer .attachments-field {
    flex: 1;
    min-width: 0;
    margin: 0;
}

.composer-footer .attachments-field > .field-label {
    display: none;
}

.composer-footer .attachments-field .attachments-widget .upload-container {
    justify-content: flex-start;
    padding: 0.4rem 0.25rem;
    border: none;
    background: transparent;
}

.send-error {
    margin: 0.75rem 0 0;
}

.dialog-error {
    margin: 0.75rem 1.5rem;
}

.send-btn,
.resolve-btn {
    padding: 0.7rem 1.2rem;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.2;
}

.send-hint {
    margin-left: auto;
}

.send-hint kbd {
    padding: 0.1rem 0.5rem;
    border: 1px solid #c8ccd1;
    border-radius: 4px;
    background-color: #ffffff;
    font-family: inherit;
    font-size: 1.05rem;
    color: #333;
}

.send-btn .p-button-label,
.resolve-btn .p-button-label {
    font-size: 14px !important;
    font-weight: 600 !important;
    line-height: 1.2;
}

.send-btn {
    background-color: var(--bc-navy);
    border: 1px solid var(--bc-navy);
    color: #ffffff;
}

.send-btn:hover {
    background-color: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
}

.resolve-btn {
    background-color: #ffffff;
    border: 1px solid var(--bc-navy);
    color: var(--bc-navy);
}

.resolve-btn:hover {
    background-color: var(--bc-selected);
}

.resolve-btn.is-primary {
    background-color: var(--bc-navy);
    color: #ffffff;
}

.resolve-btn.is-primary:hover {
    background-color: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
}

.thread-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
}

.thread-status {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
    min-width: 0;
}

.thread-title {
    margin: 0;
    font-size: 1.7rem;
    font-weight: 700;
    color: var(--bc-navy);
    overflow-wrap: anywhere;
}

.thread-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1rem;
}

.thread-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.thread-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
}

.thread-to {
    font-size: 1.3rem;
    color: var(--bc-muted);
}

.thread-to strong {
    color: var(--bc-text);
}

.thread-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.8rem;
    border-radius: 4px;
    font-size: 1.15rem;
    font-weight: 600;
}

.internal-tag {
    background-color: var(--internal-bg);
    color: var(--internal-text);
}

.external-tag {
    background-color: var(--external-bg);
    color: var(--external-text);
}

.resolved-banner {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
    padding: 1rem 1.5rem;
    background-color: #f3faf4;
    border: 1px solid #b7dcbf;
    border-radius: 6px;
    font-size: 1.25rem;
    color: var(--bc-text);
}

.resolved-banner i {
    font-size: 1.9rem;
    color: var(--resolved-text);
}

.internal-note {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding: 1rem 1.5rem;
    border: 1px solid;
    border-radius: 6px;
    font-size: 1.25rem;
    color: var(--bc-text);
}

.internal-note i {
    font-size: 1.4rem;
}

.internal-note.is-internal {
    background-color: var(--internal-bg);
    border-color: #f5d48f;
}

.internal-note.is-internal i {
    color: var(--internal-text);
}

.internal-note.is-external {
    background-color: #f1f7fd;
    border-color: #b9d3ef;
}

.internal-note.is-external i {
    color: var(--external-text);
}

.recipient-placeholder {
    color: var(--bc-muted);
}

.dropdown-value-template {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.dropdown-value-template i {
    width: 1.25em;
    text-align: center;
    flex-shrink: 0;
}

.dropdown-value-template .fa-lock {
    color: var(--internal-text);
}

.dropdown-value-template .fa-users {
    color: var(--external-text);
}
</style>
