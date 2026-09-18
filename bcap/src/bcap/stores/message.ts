import { reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import {
    createBcapMessage,
    getMessagesForThread,
    getSubmissionModulesUnreadCounts,
    getThreadsForResource,
    markMessageAsRead,
    setThreadArchived,
} from '@/bcap/apps/Permit/api.ts';
import { inlineMessage, notifyError } from '@/bcap/notify.ts';
import type {
    MessageThread,
    FormattedMessage,
    NewBcapMessage,
} from '@/bcap/types.ts';

// Threads cached per resource, active and archived kept in their own maps, so the
// dialogs on a permit page share one fetch per resource. Each dialog scopes to its
// own resource id; there is no cross-resource filtering.
export const useMessageStore = defineStore('bcapMessages', () => {
    const active = reactive(new Map<string, MessageThread[]>());
    const archived = reactive(new Map<string, MessageThread[]>());
    const inFlight = new Map<string, Promise<MessageThread[]>>();
    const moduleUnread = reactive(new Map<string, number>());
    const openMessages = ref<FormattedMessage[]>([]);
    // An empty thread list is indistinguishable from a failed one, so the
    // dialog reads this to say which it is. One slot: the dialog shows a single
    // error, and whichever load failed last is the one worth reading.
    const error = ref('');

    const cacheFor = (isArchived: boolean) => (isArchived ? archived : active);

    function threadsFor(
        resourceId: string,
        isArchived = false,
    ): MessageThread[] {
        return cacheFor(isArchived).get(resourceId) ?? [];
    }

    function unreadCount(resourceId: string): number {
        return threadsFor(resourceId).reduce(
            (sum, thread) => sum + (thread.unreadCount || 0),
            0,
        );
    }

    async function loadModuleUnread(submissionId: string) {
        try {
            const rows = await getSubmissionModulesUnreadCounts(submissionId);
            for (const { module_id, unread_count } of rows) {
                moduleUnread.set(module_id, unread_count);
            }
        } catch (failure) {
            error.value = `Unread message counts could not be loaded. ${inlineMessage(failure)}`;
        }
    }

    const moduleUnreadCount = (moduleTileId: string): number =>
        moduleUnread.get(moduleTileId) ?? 0;

    async function load(resourceId: string, isArchived = false) {
        const key = `${resourceId}:${isArchived}`;
        // Dialogs mount together; share the in-flight fetch instead of racing.
        let pending = inFlight.get(key);
        if (!pending) {
            pending = getThreadsForResource(resourceId, isArchived);
            inFlight.set(key, pending);
        }
        try {
            cacheFor(isArchived).set(resourceId, await pending);
            error.value = '';
        } catch (failure) {
            error.value = `Messages could not be loaded. ${inlineMessage(failure)}`;
            cacheFor(isArchived).set(resourceId, []);
        } finally {
            inFlight.delete(key);
        }
    }

    async function send(message: NewBcapMessage) {
        await createBcapMessage(message);
        await load(message.resourceId);
    }

    async function setArchived(
        threadId: string,
        archived: boolean,
        resourceId: string,
    ) {
        try {
            await setThreadArchived(threadId, archived);
        } catch (failure) {
            error.value = `This thread could not be archived. ${inlineMessage(failure)}`;
            return;
        }
        await Promise.all([load(resourceId), load(resourceId, true)]);
    }

    // Fetch a thread's messages into openMessages, clearing first so the open
    // thread shows a loading gap rather than the previous thread's messages.
    async function loadThreadMessages(threadId: string) {
        openMessages.value = [];
        error.value = '';
        try {
            openMessages.value = await getMessagesForThread(threadId);
        } catch (failure) {
            error.value = `This conversation could not be loaded. ${inlineMessage(failure)}`;
        }
    }

    // Mark the open thread's unread messages read, updating its badge counts.
    async function markThreadRead(thread: MessageThread) {
        if (!thread.hasUnread) return;

        for (const message of openMessages.value.filter(
            (m) => m.isUnread && m.id,
        )) {
            try {
                await markMessageAsRead(message.id);
                message.isUnread = false;
                if (thread.unreadCount) thread.unreadCount--;
            } catch (error) {
                notifyError('Failed to mark message as read', error);
            }
        }

        thread.hasUnread = false;
    }

    return {
        threadsFor,
        unreadCount,
        loadModuleUnread,
        moduleUnreadCount,
        openMessages,
        error,
        load,
        send,
        setArchived,
        loadThreadMessages,
        markThreadRead,
    };
});
