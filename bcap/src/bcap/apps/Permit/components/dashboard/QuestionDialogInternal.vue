<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';
import Dialog from 'primevue/dialog';
import Dropdown from 'primevue/dropdown';
import Textarea from 'primevue/textarea';
import Button from 'primevue/button';
import type { ContributorSchema } from '@/bcap/schema/ContributorSchema';

const props = defineProps<{
    applicationId: string;
    permitResourceId: string;
    existingMessages?: Array<{ author: string; text: string }>;
}>();

const emit = defineEmits(['message-sent']);
const visible = ref(false);
const messageText = ref('');
const isSubmitting = ref(false);
const selectedRecipient = ref<string | null>(null);
const contributors = ref<Array<{ label: string; value: string }>>([]);
const isLoadingContributors = ref(false);
const messageInput = ref();

const isReplyMode = computed(() => {
    return props.existingMessages && props.existingMessages.length > 0;
});

const loadContributors = async () => {
    isLoadingContributors.value = true;
    try {
        const response = await fetch(
            '/bcap/api/contributor?limit=100&offset=0',
            {
                method: 'GET',
                headers: {
                    Accept: 'application/json',
                },
            },
        );

        if (!response.ok) throw new Error('Failed to fetch contributors');

        const data = await response.json();

        if (data.results && data.results.length > 0) {
            contributors.value = data.results.map(
                (
                    resource: ContributorSchema & {
                        resourceinstanceid?: string;
                    },
                ) => {
                    const contributorData =
                        resource.aliased_data?.contributor?.aliased_data;

                    const firstNameNode = contributorData?.first_name
                        ?.node_value as
                        Record<string, { value: string }> | undefined;
                    const firstName =
                        contributorData?.first_name?.display_value ||
                        firstNameNode?.en?.value ||
                        '';

                    const lastNameNode = contributorData?.contributor_name
                        ?.node_value as
                        Record<string, { value: string }> | undefined;
                    const lastName =
                        contributorData?.contributor_name?.display_value ||
                        lastNameNode?.en?.value ||
                        '';

                    const label =
                        [firstName, lastName].filter(Boolean).join(' ') ||
                        'Unknown Contributor';

                    return {
                        label: label as string,
                        value: (resource.resourceinstanceid ||
                            resource.resourceinstance) as string,
                    };
                },
            );
        } else {
            contributors.value = [];
        }
    } catch (error) {
        console.error('Error fetching contributors:', error);
        contributors.value = [];
    } finally {
        isLoadingContributors.value = false;
    }
};

onMounted(() => {
    loadContributors();
});

const openDialog = () => {
    visible.value = true;
};

const closeDialog = () => {
    visible.value = false;
    messageText.value = '';
    selectedRecipient.value = null;
};

const focusInput = async () => {
    await nextTick();
    if (messageInput.value) {
        messageInput.value.$el.focus();
    }
};

const submitMessage = async () => {
    if (!messageText.value) return;

    if (!isReplyMode.value && !selectedRecipient.value) {
        alert('Please select a recipient.');
        return;
    }

    isSubmitting.value = true;

    const payload = {
        aliased_data: {
            message_content: {
                aliased_data: {
                    message_content: {
                        node_value: {
                            en: {
                                value: messageText.value,
                                direction: 'ltr',
                            },
                        },
                    },
                    message_creation_date: {
                        node_value: new Date().toISOString(),
                    },
                    recipient: {
                        node_value: {
                            resourceId: selectedRecipient.value,
                            ontologyProperty: '',
                            resourceXresourceId: '',
                            inverseOntologyProperty: '',
                        },
                    },
                },
            },
        },
    };

    try {
        console.log('Submitting Payload:', JSON.stringify(payload, null, 2));

        emit('message-sent', payload);
        closeDialog();
    } catch (error) {
        console.error('Error submitting message:', error);
    } finally {
        isSubmitting.value = false;
    }
};
</script>

<template>
    <div class="ask-question-trigger">
        <Button
            severity="secondary"
            class="trigger-btn"
            @click="openDialog"
        >
            <span class="trigger-label">Send a message</span>
            <i class="fa-regular fa-comment-dots"></i>
        </Button>
    </div>

    <Dialog
        v-model:visible="visible"
        modal
        :closable="true"
        @show="focusInput"
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
                <div class="field-container">
                    <Dropdown
                        v-model="selectedRecipient"
                        :options="contributors"
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Select Recipient"
                        :loading="isLoadingContributors"
                        class="w-full recipient-dropdown"
                    >
                        <template #value="slotProps">
                            <div
                                v-if="slotProps.value"
                                class="dropdown-value"
                            >
                                <i class="fa-regular fa-envelope"></i>
                                <span>
                                    {{
                                        contributors.find(
                                            (r) => r.value === slotProps.value,
                                        )?.label
                                    }}
                                </span>
                            </div>
                            <span v-else>{{ slotProps.placeholder }}</span>
                        </template>
                        <template #option="slotProps">
                            <div class="dropdown-option">
                                <i class="fa-regular fa-envelope"></i>
                                <span>{{ slotProps.option.label }}</span>
                            </div>
                        </template>
                    </Dropdown>
                </div>

                <div class="field-container">
                    <label class="field-label">Message:</label>
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
                <div class="message-thread">
                    <div
                        v-for="(msg, index) in existingMessages"
                        :key="index"
                        class="historical-message"
                    >
                        <strong>{{ msg.author }}:</strong>
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
}

.trigger-btn:hover {
    background-color: #e0e0e0;
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
    margin-bottom: 2rem;
    width: 100%;
}

.field-label {
    display: block;
    margin-bottom: 0.5rem;
    color: #333;
}

/* --- Dropdown Customizations --- */
.recipient-dropdown {
    border-color: #ced4da;
    height: 3.5rem; /* Bumps up the physical height of the box */
    border-radius: 6px;
}

/* Forces the inner container to stretch the full height so the text centers */
.recipient-dropdown .p-dropdown-label {
    display: flex;
    align-items: center;
    height: 100%;
    padding-left: 1rem;
}

.dropdown-value,
.dropdown-option {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: #495057;
    font-size: 1.25rem !important;
}

/* Make sure the icons scale up with the text */
.dropdown-value i,
.dropdown-option i {
    font-size: 1.3rem !important;
}

/* Optional: Give the popup menu items a little more breathing room */
.p-dropdown-item {
    padding: 1rem !important;
}

/* --- Full Width Textarea --- */
.full-width-textarea {
    width: 100% !important;
    box-sizing: border-box;
}

/* --- Thread / Reply Styles --- */
.message-thread {
    margin-bottom: 2rem;
}

.historical-message {
    margin-bottom: 1rem;
    color: #333;
}

.historical-message strong {
    display: block;
    margin-bottom: 0.5rem;
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
