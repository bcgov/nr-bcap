<script setup lang="ts">
import { reactive } from 'vue';
import { z } from 'zod';
import arches from 'arches';
import {
    zApiPermitApplicationCreateResponse,
    zBcapMessage,
    zBcapMessageWritable,
    zPaginatedBcapMessageList,
    zPaginatedContributorList,
} from '@/bcap/client/zod.gen.ts';
import { formatDateTime, getCsrfToken, getDisplayValue } from '@/bcap/util.ts';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

// A throwaway harness for the BCAP message endpoints: one button creates a
// permit, posts two threads of five messages each against it, then reads the
// threads and each thread's messages back, validating every response with the
// generated Zod schemas.

type BcapMessage = z.infer<typeof zBcapMessage>;
type BcapMessageWritable = z.infer<typeof zBcapMessageWritable>;

interface DemoSummary {
    permitId: string;
    threadCount: number;
    messageCounts: number[];
    totalMessages: number;
}

interface DemoMessage {
    id: string;
    content: string;
    author: string;
    recipient: string;
    creationDate: string | null;
    isRoot: boolean;
}

interface DemoThread {
    rootId: string;
    subject: string;
    creationDate: string | null;
    messages: DemoMessage[];
}

const state = reactive({
    running: false,
    steps: [] as string[],
    error: '',
    summary: null as DemoSummary | null,
    threads: [] as DemoThread[],
});

const log = (message: string): void => {
    state.steps.push(message);
};

const contentOf = (message: BcapMessage) =>
    message.aliased_data?.message_content?.aliased_data;

const displayText = (
    node: { display_value?: string } | null | undefined,
): string => getDisplayValue(node as AliasedNodeData | null | undefined) ?? '';

const postJson = async <T,>(
    url: string,
    body: unknown,
    schema: z.ZodType<T>,
): Promise<T> => {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        throw new Error(`${response.status} ${await response.text()}`);
    }
    return schema.parse(await response.json());
};

const getJson = async <T,>(url: string, schema: z.ZodType<T>): Promise<T> => {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${await response.text()}`);
    }
    return schema.parse(await response.json());
};

// The Contributor the demo addresses its messages to. Looked up by name so the
// demo has a real recipient to show without hard-coding an id. The backend will
// override this in the future to route an external user's message to the proper
// recipient.
const ARCHAEOLOGY_ORG = 'Archaeology Branch';

const fetchRecipientId = async (): Promise<string | undefined> => {
    // Filter server-side by name so one request returns just the org.
    const url = `${arches.urls.api_resource_list('contributor')}?aliased_data__contributor_name__en__value=${encodeURIComponent(
        ARCHAEOLOGY_ORG,
    )}`;
    const page = await getJson(url, zPaginatedContributorList);
    return page.results[0]?.resourceinstanceid ?? undefined;
};

// Create a message on the permit; pass rootId to make it a reply in that thread.
const createMessage = (
    permitId: string,
    subject: string,
    content: string,
    recipientId: string,
    rootId?: string,
): Promise<BcapMessage> => {
    const aliasedData: NonNullable<BcapMessageWritable['aliased_data']> = {
        message_content: {
            aliased_data: {
                resource_context: { node_value: [{ resourceId: permitId }] },
                // In the future external users won't choose the recipient; the
                // backend will route their message to the proper recipient.
                recipient: { node_value: [{ resourceId: recipientId }] },
                message_subject: {
                    node_value: { en: { value: subject, direction: 'ltr' } },
                },
                message_content: {
                    node_value: { en: { value: content, direction: 'ltr' } },
                },
                // Passed along and applied server-side after save (the REST date
                // field would otherwise drop the UTC offset).
                message_creation_date: { node_value: new Date().toISOString() },
            },
        },
    };
    // A reply also points back at its thread's root message.
    if (rootId) {
        aliasedData.related_source_message = {
            aliased_data: {
                related_source_message: {
                    node_value: [{ resourceId: rootId }],
                },
            },
        };
    }
    return postJson(
        arches.urls.bcap_message_list_create,
        { aliased_data: aliasedData },
        zBcapMessage,
    );
};

const runDemo = async (): Promise<void> => {
    state.running = true;
    state.error = '';
    state.steps = [];
    state.summary = null;
    state.threads = [];
    try {
        log('Creating a permit application...');
        const permit = await postJson(
            arches.urls.permit_application_create,
            {
                aliased_data: {
                    application_identification: {
                        aliased_data: { project_name: 'Message Demo Permit' },
                    },
                },
            },
            zApiPermitApplicationCreateResponse,
        );
        const permitId = permit.resourceinstanceid as string;
        log(`Permit created: ${permitId}`);

        const recipientId = await fetchRecipientId();
        if (!recipientId) {
            throw new Error(
                `No ${ARCHAEOLOGY_ORG} contributor found to address messages to.`,
            );
        }
        log(`Addressing messages to ${ARCHAEOLOGY_ORG}`);

        log('Creating 2 threads with 5 messages each...');
        for (let thread = 1; thread <= 2; thread += 1) {
            const root = await createMessage(
                permitId,
                `Thread ${thread}`,
                `Thread ${thread} root`,
                recipientId,
            );
            for (let reply = 1; reply <= 4; reply += 1) {
                await createMessage(
                    permitId,
                    `Thread ${thread}`,
                    `Thread ${thread} reply ${reply}`,
                    recipientId,
                    root.resourceinstanceid as string,
                );
            }
            log(`Thread ${thread}: 1 root + 4 replies`);
        }

        log('Fetching the message threads for the permit...');
        const threads = await getJson(
            arches.urls.bcap_message_resource_threads(permitId),
            zPaginatedBcapMessageList,
        );
        log(`Got ${threads.count} thread(s)`);

        const messageCounts: number[] = [];
        for (const root of threads.results) {
            const rootId = root.resourceinstanceid as string;
            const messages = await getJson(
                arches.urls.bcap_message_thread_messages(rootId),
                zPaginatedBcapMessageList,
            );
            messageCounts.push(messages.count);
            state.threads.push({
                rootId,
                creationDate:
                    contentOf(root)?.message_creation_date?.node_value ?? null,
                subject:
                    displayText(contentOf(root)?.message_subject) || 'Thread',
                messages: messages.results.map((message) => ({
                    id: message.resourceinstanceid as string,
                    content: displayText(contentOf(message)?.message_content),
                    author: displayText(contentOf(message)?.message_author),
                    recipient: displayText(contentOf(message)?.recipient),
                    creationDate:
                        contentOf(message)?.message_creation_date?.node_value ??
                        null,
                    isRoot: message.resourceinstanceid === rootId,
                })),
            });
        }
        log(`Messages per thread: ${messageCounts.join(', ')}`);

        state.summary = {
            permitId,
            threadCount: threads.count,
            messageCounts,
            totalMessages: messageCounts.reduce((sum, n) => sum + n, 0),
        };
    } catch (error) {
        state.error = error instanceof Error ? error.message : String(error);
    } finally {
        state.running = false;
    }
};
</script>

<template>
    <div class="message-demo">
        <h2>BCAP Message endpoint demo</h2>
        <p class="hint">
            Creates a permit, posts two threads of five messages each, then
            reads the threads and each thread's messages back.
        </p>

        <button
            type="button"
            class="run-btn"
            :disabled="state.running"
            @click="runDemo"
        >
            {{ state.running ? 'Running...' : 'Run demo' }}
        </button>

        <ol
            v-if="state.steps.length"
            class="steps"
        >
            <li
                v-for="(step, i) in state.steps"
                :key="i"
            >
                {{ step }}
            </li>
        </ol>

        <p
            v-if="state.error"
            class="error"
        >
            {{ state.error }}
        </p>

        <dl
            v-if="state.summary"
            class="summary"
        >
            <div>
                <dt>Permit</dt>
                <dd>{{ state.summary.permitId }}</dd>
            </div>
            <div>
                <dt>Threads on permit</dt>
                <dd>{{ state.summary.threadCount }}</dd>
            </div>
            <div>
                <dt>Messages per thread</dt>
                <dd>{{ state.summary.messageCounts.join(', ') }}</dd>
            </div>
            <div>
                <dt>Total messages</dt>
                <dd>{{ state.summary.totalMessages }}</dd>
            </div>
        </dl>

        <div
            v-if="state.threads.length"
            class="threads"
        >
            <details
                v-for="thread in state.threads"
                :key="thread.rootId"
                class="thread"
            >
                <summary>
                    {{ thread.subject }}
                    <span class="count">
                        ({{ thread.messages.length }} messages)
                    </span>
                    <span class="thread-date">
                        {{ formatDateTime(thread.creationDate) }}
                    </span>
                </summary>
                <ul class="thread-messages">
                    <li
                        v-for="message in thread.messages"
                        :key="message.id"
                        :class="{ root: message.isRoot }"
                    >
                        <div class="msg-head">
                            <span class="msg-from">
                                {{ message.author || 'Unknown author' }}
                                <template v-if="message.recipient">
                                    &rarr; {{ message.recipient }}
                                </template>
                            </span>
                            <span class="msg-date">
                                {{ formatDateTime(message.creationDate) }}
                            </span>
                        </div>
                        <span class="msg-content">{{ message.content }}</span>
                    </li>
                </ul>
            </details>
        </div>
    </div>
</template>

<style scoped>
.message-demo {
    max-width: 40rem;
    margin: 2rem auto;
    padding: 1.5rem;
    font-family: sans-serif;
}
.hint {
    color: #555;
    margin-bottom: 1rem;
}
.run-btn {
    padding: 0.5rem 1rem;
    font-weight: 600;
    cursor: pointer;
}
.run-btn:disabled {
    opacity: 0.6;
    cursor: default;
}
.steps {
    margin-top: 1rem;
    line-height: 1.6;
}
.error {
    margin-top: 1rem;
    color: #b00020;
    white-space: pre-wrap;
}
.summary {
    margin-top: 1.5rem;
}
.summary div {
    display: flex;
    gap: 0.5rem;
}
.summary dt {
    width: 12rem;
    font-weight: 600;
}
.summary dd {
    margin: 0;
    font-family: monospace;
}
.threads {
    margin-top: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.thread {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 0.5rem 0.75rem;
}
.thread > summary {
    cursor: pointer;
    font-weight: 600;
}
.thread > summary .count {
    font-weight: 400;
    color: #555;
}
.thread > summary .thread-date {
    font-weight: 400;
    color: #777;
    font-size: 0.85em;
    margin-left: 0.5rem;
}
.thread-messages {
    list-style: none;
    margin: 0.75rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.thread-messages li {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.4rem 0.6rem;
    border-left: 3px solid #ddd;
    background: #f7f7f7;
}
.thread-messages li.root {
    border-left-color: #4a6;
}
.msg-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-size: 0.85em;
}
.msg-from {
    font-weight: 600;
    color: #333;
}
.msg-date {
    color: #777;
    white-space: nowrap;
}
</style>
