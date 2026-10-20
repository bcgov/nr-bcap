import { useMessageStore } from '@/bcap/stores/message.ts';
import {
    createBcapMessage,
    getMessagesForThread,
    getSubmissionModulesUnresolvedCounts,
    getThreadsForResources,
    patchThread,
} from '@/bcap/apps/Permit/api.ts';
import type { MessageThread } from '@/bcap/types.ts';

// One resource's list, which the batched fetch hands back under that id.
const { resourceThreads } = vi.hoisted(() => ({ resourceThreads: vi.fn() }));
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createBcapMessage: vi.fn(),
    getMessagesForThread: vi.fn(),
    getSubmissionModulesUnresolvedCounts: vi.fn(),
    getThreadsForResources: vi.fn(
        async (ids: string[], archived = false) =>
            new Map([[ids[0], await resourceThreads(ids[0], archived)]]),
    ),
    patchThread: vi.fn(),
}));

const thread = (over: Partial<MessageThread> = {}): MessageThread => ({
    id: 't1',
    topic: 'General Question',
    startedBy: 'Amy',
    lastMessageDate: '',
    isResolved: false,
    onSide: true,
    needsAction: !over.isResolved,
    resolvedBy: '',
    resolvedDate: '',
    isInternal: false,
    to: 'Sam Staff',
    ...over,
});

const reloadedBoth = () =>
    expect(vi.mocked(resourceThreads).mock.calls).toEqual(
        expect.arrayContaining([
            ['permit-1', false],
            ['permit-1', true],
        ]),
    );

describe('message store', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(resourceThreads).mockResolvedValue([]);
    });

    it('fills each resource from one batched load', async () => {
        vi.mocked(getThreadsForResources).mockResolvedValueOnce(
            new Map([
                ['req-1', [thread({ id: 'a' })]],
                ['req-2', []],
            ]),
        );
        const store = useMessageStore();

        await store.load(['req-1', 'req-2']);

        expect(getThreadsForResources).toHaveBeenCalledTimes(1);
        expect(store.unresolvedCount('req-1')).toBe(1);
        expect(store.threadsFor('req-2')).toEqual([]);
    });

    it("counts a resource's unresolved threads", async () => {
        vi.mocked(resourceThreads).mockResolvedValue([
            thread({ id: 'a' }),
            thread({ id: 'b' }),
            thread({ id: 'c', isResolved: true }),
        ]);
        const store = useMessageStore();

        await store.load('permit-1');

        expect(store.threadsFor('permit-1')).toHaveLength(3);
        expect(store.unresolvedCount('permit-1')).toBe(2);
        // A resource never loaded is empty, not an error.
        expect(store.threadsFor('permit-2')).toEqual([]);
        expect(store.unresolvedCount('permit-2')).toBe(0);
    });

    it('does not count a thread the viewer takes no part in', async () => {
        vi.mocked(resourceThreads).mockResolvedValue([
            thread({ id: 'a' }),
            thread({ id: 'b', needsAction: false }),
        ]);
        const store = useMessageStore();

        await store.load('permit-1');

        expect(store.unresolvedCount('permit-1')).toBe(1);
    });

    it('keeps active and archived threads in separate lists', async () => {
        vi.mocked(resourceThreads).mockImplementation(
            (_id: string, archived?: boolean) =>
                Promise.resolve([thread({ id: archived ? 'arch' : 'active' })]),
        );
        const store = useMessageStore();

        await store.load('permit-1');
        await store.load('permit-1', true);

        expect(store.threadsFor('permit-1')[0].id).toBe('active');
        expect(store.threadsFor('permit-1', true)[0].id).toBe('arch');
    });

    it('does not count archived threads', async () => {
        vi.mocked(resourceThreads).mockImplementation(
            (_id: string, archived?: boolean) =>
                Promise.resolve(archived ? [thread({ id: 'arch' })] : []),
        );
        const store = useMessageStore();

        await store.load('permit-1', true);

        expect(store.unresolvedCount('permit-1')).toBe(0);
    });

    it('falls back to an empty list when the fetch fails', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(resourceThreads).mockRejectedValueOnce(new Error('nope'));
        const store = useMessageStore();

        await store.load('permit-1');

        // An empty list and a failed one look the same, hence the message.
        expect(store.threadsFor('permit-1')).toEqual([]);
        expect(store.error).toContain('Messages could not be loaded.');
    });

    it('sends a message then reloads that resource', async () => {
        const store = useMessageStore();

        await store.send({
            messageText: 'hi',
            recipientId: 'r1',
            resourceId: 'permit-1',
        });

        expect(createBcapMessage).toHaveBeenCalledOnce();
        expect(resourceThreads).toHaveBeenCalledWith('permit-1', false);
    });

    it('updates the thread then reloads both lists', async () => {
        const store = useMessageStore();

        await store.updateThread('t1', { archived: true }, 'permit-1');

        expect(patchThread).toHaveBeenCalledWith('t1', { archived: true });
        reloadedBoth();
    });

    it('reports a failed update without reloading the threads', async () => {
        vi.mocked(patchThread).mockRejectedValueOnce(new Error('nope'));
        const store = useMessageStore();

        await store.updateThread('t1', { resolved: true }, 'permit-1');

        expect(store.error).toContain('This thread could not be updated.');
        // Nothing moved, and a reload would clear the message just set.
        expect(resourceThreads).not.toHaveBeenCalled();
    });

    it('maps module tile ids to their unresolved counts', async () => {
        vi.mocked(getSubmissionModulesUnresolvedCounts).mockResolvedValue([
            { module_id: 'mod-a', unresolved_count: 3 },
            { module_id: 'mod-b', unresolved_count: 0 },
        ]);
        const store = useMessageStore();

        await store.loadModuleUnresolved('submission-1');

        expect(store.moduleUnresolvedCount('mod-a')).toBe(3);
        expect(store.moduleUnresolvedCount('mod-b')).toBe(0);
        // An unknown module reads as zero, not undefined.
        expect(store.moduleUnresolvedCount('mod-x')).toBe(0);
    });

    it('reloads module counts for the last loaded submission only', async () => {
        vi.mocked(getSubmissionModulesUnresolvedCounts).mockResolvedValue([]);
        const store = useMessageStore();

        await store.reloadModuleUnresolved();
        expect(getSubmissionModulesUnresolvedCounts).not.toHaveBeenCalled();

        await store.loadModuleUnresolved('submission-1');
        await store.reloadModuleUnresolved();
        expect(
            vi.mocked(getSubmissionModulesUnresolvedCounts).mock.calls,
        ).toEqual([['submission-1'], ['submission-1']]);
    });

    const page = (ids: string[], hasMore: boolean) => ({
        messages: ids.map((id) => ({
            id,
            author: 'Amy',
            authorIsStaff: false,
            text: 'hi',
            date: 'x',
            attachments: [],
        })),
        hasMore,
    });

    it("loads a thread's latest page into openMessages", async () => {
        vi.mocked(getMessagesForThread).mockResolvedValue(page(['m1'], true));
        const store = useMessageStore();

        await store.loadThreadMessages('thread-1');

        expect(getMessagesForThread).toHaveBeenCalledWith('thread-1', 0);
        expect(store.openMessages.map((m) => m.id)).toEqual(['m1']);
        expect(store.hasEarlierMessages).toBe(true);
    });

    it('puts earlier pages on top, skipping any already shown', async () => {
        vi.mocked(getMessagesForThread)
            .mockResolvedValueOnce(page(['m3', 'm4'], true))
            .mockResolvedValueOnce(page(['m1', 'm2', 'm3'], false));
        const store = useMessageStore();

        await store.loadThreadMessages('thread-1');
        await store.loadEarlierMessages('thread-1');

        expect(getMessagesForThread).toHaveBeenLastCalledWith('thread-1', 2);
        expect(store.openMessages.map((m) => m.id)).toEqual([
            'm1',
            'm2',
            'm3',
            'm4',
        ]);
        expect(store.hasEarlierMessages).toBe(false);
    });

    it('reports a failed earlier page and keeps what is shown', async () => {
        vi.mocked(getMessagesForThread)
            .mockResolvedValueOnce(page(['m3'], true))
            .mockRejectedValueOnce(new Error('down'));
        const store = useMessageStore();

        await store.loadThreadMessages('thread-1');
        await store.loadEarlierMessages('thread-1');

        expect(store.error).toContain('could not be loaded');
        expect(store.openMessages.map((m) => m.id)).toEqual(['m3']);
        expect(store.hasEarlierMessages).toBe(true);
    });
});
