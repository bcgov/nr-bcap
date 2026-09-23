import { reactive, ref } from 'vue';
import { defineStore } from 'pinia';
import {
    createBcapMessage,
    getMessagesForThread,
    getSubmissionModulesUnresolvedCounts,
    getThreadsForResources,
    patchThread,
} from '@/bcap/apps/Permit/api.ts';
import type { PatchedBcapMessagePatch } from '@/bcap/client/types.gen.ts';
import { inlineMessage } from '@/bcap/notify.ts';
import type {
    MessageThread,
    FormattedMessage,
    NewBcapMessage,
} from '@/bcap/types.ts';

// Each resource's latest thread lists, active and archived in their own maps, so
// the dialogs and badges on a permit page share them. Each dialog scopes to its
// own resource id; there is no cross-resource filtering.
export const useMessageStore = defineStore('bcapMessages', () => {
    const active = reactive(new Map<string, MessageThread[]>());
    const archived = reactive(new Map<string, MessageThread[]>());
    const moduleUnresolved = reactive(new Map<string, number>());
    const openMessages = ref<FormattedMessage[]>([]);
    const hasEarlierMessages = ref(false);
    // An empty thread list is indistinguishable from a failed one, so the
    // dialog reads this to say which it is. One slot: the dialog shows a single
    // error, and whichever load failed last is the one worth reading.
    const error = ref('');
    let moduleSubmissionId = '';

    const listsFor = (isArchived: boolean) => (isArchived ? archived : active);

    const threadsFor = (resourceId: string, isArchived = false) =>
        listsFor(isArchived).get(resourceId) ?? [];

    const unresolvedCount = (resourceId: string) =>
        threadsFor(resourceId).filter((thread) => thread.needsAction).length;

    const moduleUnresolvedCount = (moduleTileId: string) =>
        moduleUnresolved.get(moduleTileId) ?? 0;

    async function load(ids: string | string[], isArchived = false) {
        const resourceIds = [ids].flat();
        if (!resourceIds.length) return;
        const lists = listsFor(isArchived);
        try {
            const byResource = await getThreadsForResources(
                resourceIds,
                isArchived,
            );
            for (const [id, threads] of byResource) lists.set(id, threads);
            error.value = '';
        } catch (failure) {
            error.value = `Messages could not be loaded. ${inlineMessage(failure)}`;
            for (const id of resourceIds) lists.set(id, []);
        }
    }

    async function loadModuleUnresolved(submissionId: string) {
        moduleSubmissionId = submissionId;
        try {
            const rows =
                await getSubmissionModulesUnresolvedCounts(submissionId);
            for (const { module_id, unresolved_count } of rows) {
                moduleUnresolved.set(module_id, unresolved_count);
            }
        } catch (failure) {
            error.value = `Unresolved message counts could not be loaded. ${inlineMessage(failure)}`;
        }
    }

    const reloadModuleUnresolved = async () => {
        if (moduleSubmissionId) await loadModuleUnresolved(moduleSubmissionId);
    };

    // Open a thread on its latest page, clearing first so it shows a loading gap
    // rather than the previous thread's messages.
    async function loadThreadMessages(threadId: string) {
        openMessages.value = [];
        await loadEarlierMessages(threadId);
    }

    async function loadEarlierMessages(threadId: string) {
        error.value = '';
        try {
            const page = await getMessagesForThread(
                threadId,
                openMessages.value.length,
            );
            // Messages posted since the last page push this one back, so it can
            // repeat ones already shown; skip those.
            const shown = new Set(openMessages.value.map((m) => m.id));
            openMessages.value = [
                ...page.messages.filter((m) => !shown.has(m.id)),
                ...openMessages.value,
            ];
            hasEarlierMessages.value = page.hasMore;
        } catch (failure) {
            error.value = `This conversation could not be loaded. ${inlineMessage(failure)}`;
        }
    }

    async function send(message: NewBcapMessage) {
        const created = await createBcapMessage(message);
        await load(message.resourceId);
        return created;
    }

    // Archive or resolve a thread, then reload both of the resource's lists.
    async function updateThread(
        threadId: string,
        change: PatchedBcapMessagePatch,
        resourceId: string,
    ) {
        try {
            await patchThread(threadId, change);
        } catch (failure) {
            error.value = `This thread could not be updated. ${inlineMessage(failure)}`;
            return;
        }
        await Promise.all([load(resourceId), load(resourceId, true)]);
    }

    return {
        openMessages,
        hasEarlierMessages,
        error,
        threadsFor,
        unresolvedCount,
        moduleUnresolvedCount,
        load,
        loadModuleUnresolved,
        reloadModuleUnresolved,
        loadThreadMessages,
        loadEarlierMessages,
        send,
        updateThread,
    };
});
