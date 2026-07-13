<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import Dialog from 'primevue/dialog';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';
import { createBcapMessage } from '@/bcap/apps/Permit/api.ts';

const props = defineProps<{
    applicationId: string;
    permitResourceId: string;
    existingMessages?: Array<{ author: string; text: string; date?: string }>;
    threadId?: string | null;
}>();

const emit = defineEmits(['message-sent']);
const visible = ref(false);
const messageText = ref('');
const isSubmitting = ref(false);
const messageInput = ref();
const threadContainer = ref<HTMLElement | null>(null);
const selectedRecipient = ref('');
const recipients = ref<Array<{ label: string; value: string }>>([]);
const isLoadingRecipients = ref(false);

const isReplyMode = computed(() => {
    return props.existingMessages && props.existingMessages.length > 0;
});

const loadRecipients = async () => {
    isLoadingRecipients.value = true;
    try {
        const response = await fetch('/bcap/api/contributor', {
            headers: {
                accept: 'application/json',
            },
        });

        if (!response.ok) throw new Error('Failed to fetch contributors');
        const data = await response.json();

        interface ContributorItem {
            name?: string;
            resourceinstanceid: string;
        }

        if (data.results && Array.isArray(data.results)) {
            recipients.value = data.results.map((item: ContributorItem) => ({
                label: item.name || 'Unknown Contributor',
                value: item.resourceinstanceid,
            }));
        } else {
            recipients.value = [];
        }

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
    visible.value = true;
};

const closeDialog = () => {
    visible.value = false;
    messageText.value = '';
};

const handleDialogShow = async () => {
    await nextTick();

    if (messageInput.value) {
        messageInput.value.$el.focus();
    }

    // Scroll the thread container to the very bottom
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
        const responseData = await createBcapMessage(
            messageText.value,
            selectedRecipient.value as string,
            props.applicationId,
            props.permitResourceId,
            props.threadId || undefined,
        );

        console.log('Message successfully created:', responseData);
        emit('message-sent', responseData);
        closeDialog();
    } catch (error) {
        console.error('Error submitting message:', error);
        alert('There was an error sending your message. Please try again.');
    } finally {
        isSubmitting.value = false;
    }
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
            <span class="trigger-label">
                {{ isReplyMode ? 'View message' : 'Ask a question' }}
            </span>
            <i class="fa-regular fa-comment-dots"></i>

            <span
                v-if="isReplyMode"
                class="message-badge"
            >
                !
            </span>
        </Button>
    </div>

    <Dialog
        v-model:visible="visible"
        modal
        :closable="true"
        @show="handleDialogShow"
        :style="{ width: '500px' }"
        :pt="{
            root: { class: 'message-dialog' },
            header: { class: 'message-dialog-header' },
            closeButton: { class: 'message-dialog-close' },
        }"
    >
        <template #header>
            <span class="header-title">
                Comment on Application {{ applicationId }}
            </span>
        </template>

        <template #closeicon>
            <i class="fa-solid fa-xmark custom-close-icon"></i>
        </template>

        <div class="dialog-body">
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
                        optionLabel="label"
                        optionValue="value"
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
                                style="
                                    display: flex;
                                    align-items: center;
                                    gap: 0.75rem;
                                    font-size: 1.25rem;
                                    color: #495057;
                                "
                            >
                                <i
                                    class="fa-regular fa-envelope"
                                    style="font-size: 1.3rem"
                                ></i>
                                <span>
                                    {{
                                        recipients.find(
                                            (r) => r.value === slotProps.value,
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
                            <div
                                style="
                                    display: flex;
                                    align-items: center;
                                    gap: 0.75rem;
                                    font-size: 1.25rem;
                                    color: #495057;
                                "
                            >
                                <i
                                    class="fa-regular fa-envelope"
                                    style="font-size: 1.3rem"
                                ></i>
                                <span>{{ slotProps.option.label }}</span>
                            </div>
                        </template>
                    </Dropdown>
                </div>

                <div class="field-container">
                    <label class="field-label">Question:</label>
                    <Textarea
                        ref="messageInput"
                        v-model="messageText"
                        rows="4"
                        class="full-width-textarea"
                        autoResize
                    />
                </div>
            </div>

            <div
                v-else
                class="reply-view"
            >
                <div
                    class="message-thread"
                    ref="threadContainer"
                >
                    <div
                        v-for="(msg, index) in existingMessages"
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

                <div class="field-container">
                    <label class="field-label">Write a Reply:</label>
                    <Textarea
                        ref="messageInput"
                        v-model="messageText"
                        rows="4"
                        class="full-width-textarea"
                        autoResize
                    />
                </div>
            </div>
        </div>

        <template #footer>
            <div class="dialog-footer">
                <Button
                    label="Send"
                    class="send-btn"
                    :loading="isSubmitting"
                    @click="submitMessage"
                />
            </div>
        </template>
    </Dialog>
</template>

<style>
/* --- Trigger Button Styles --- */
.trigger-btn {
    background-color: #d0d0d0;
    color: #333;
    border: none;
    border-radius: 4px;
    padding: 0.5rem 1rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    position: relative;
}

.trigger-btn:hover {
    background-color: #e0e0e0;
}

/* --- Notification Badge --- */
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

/* --- Dialog Container --- */
.message-dialog {
    border-radius: 8px;
    overflow: hidden;
}

/* --- Dialog Header --- */
.message-dialog-header {
    background-color: #003366 !important;
    color: white !important;
    padding: 1rem 1.5rem !important;
    border-bottom: none !important;
}

.message-dialog-header .header-title {
    font-weight: 700;
    font-size: 1.3rem;
}

/* --- Custom Close Icon --- */
.custom-close-icon {
    font-size: 1.5rem;
    color: white;
}

/* Ensure the button container centers the new icon */
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

/* --- Dialog Body --- */
.dialog-body {
    padding: 1.5rem 0 0 0;
}

/* --- Field Layout --- */
.field-container {
    margin-bottom: 3.5rem;
    width: 100%;
}

.field-label {
    display: block;
    margin-bottom: 0.5rem;
    color: #333;
}

/* --- Static Recipient Display (No Box) --- */
.recipient-display {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    color: #333;
    margin-top: 0.5rem;
    margin-left: 1rem;
    margin-bottom: 2.5rem;
    font-size: 1.5rem;
    font-weight: 400;
}

/* --- Full Width Textarea --- */
.full-width-textarea {
    width: 100% !important;
    box-sizing: border-box;
}

/* --- Thread / Reply Styles --- */
.message-thread {
    margin-bottom: 2rem;
    max-height: 200px !important;
    overflow-y: auto !important;
    padding: 1rem;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    background-color: #fafafa;
    display: block;
    flex-shrink: 0;
}

/* --- Individual messages --- */
.historical-message {
    margin-bottom: 1rem;
    color: #333;
    padding-bottom: 1rem;
    border-bottom: 1px solid #eee;
}

.historical-message:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

/* --- Message Header & Date --- */
.message-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.25rem;
}

.historical-message strong {
    color: #003366;
    margin: 0;
}

.message-date {
    font-size: 1rem;
    color: #6c757d;
    font-style: italic;
}

.historical-message p {
    margin: 0;
    line-height: 1.5;
}

/* --- Footer & Send Button --- */
.dialog-footer {
    display: flex;
    justify-content: flex-end;
    padding-top: 1rem;
}

.send-btn {
    background-color: #007bff;
    border: none;
    padding: 0.5rem 2rem;
    border-radius: 6px;
}

.send-btn:hover {
    background-color: #0069d9;
}
</style>
