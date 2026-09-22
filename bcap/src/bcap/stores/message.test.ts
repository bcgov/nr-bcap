import { useMessageStore } from '@/bcap/stores/message.ts';
import {
    createBcapMessage,
    getMessagesForThread,
    getSubmissionModulesUnresolvedCounts,
    getThreadsForResource,
    setThreadArchived,
    setThreadResolved,
} from '@/bcap/apps/Permit/api.ts';
import type { MessageThread } from '@/bcap/types.ts';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createBcapMessage: vi.fn(),
    getMessagesForThread: vi.fn(),
    getSubmissionModulesUnresolvedCounts: vi.fn(),
    getThreadsForResource: vi.fn(),
    setThreadArchived: vi.fn(),
    setThreadResolved: vi.fn(),
}));

const thread = (over: Partial<MessageThread> = {}): MessageThread => ({
    id: 't1',
    topic: 'General Question',
    startedBy: 'Amy',
    lastMessageDate: '',
    isResolved: false,
    onSide: true,
    resolvedBy: '',
    resolvedDate: '',
    isInternal: false,
    ...over,
});

const reloadedBoth = () =>
    expect(vi.mocked(getThreadsForResource).mock.calls).toEqual(
        expect.arrayContaining([
            ['permit-1', false],
            ['permit-1', true],
        ]),
    );

describe('message store', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(getThreadsForResource).mockResolvedValue([]);
    });

    it("counts a resource's unresolved threads", async () => {
        vi.mocked(getThreadsForResource).mockResolvedValue([
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

    it('does not count a thread the viewer is on neither side of', async () => {
        vi.mocked(getThreadsForResource).mockResolvedValue([
            thread({ id: 'a' }),
            thread({ id: 'b', onSide: false }),
        ]);
        const store = useMessageStore();

        await store.load('permit-1');

        expect(store.unresolvedCount('permit-1')).toBe(1);
    });

    it('keeps active and archived threads in separate lists', async () => {
        vi.mocked(getThreadsForResource).mockImplementation(
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
        vi.mocked(getThreadsForResource).mockImplementation(
            (_id: string, archived?: boolean) =>
                Promise.resolve(archived ? [thread({ id: 'arch' })] : []),
        );
        const store = useMessageStore();

        await store.load('permit-1', true);

        expect(store.unresolvedCount('permit-1')).toBe(0);
    });

    it('shares one in-flight fetch when the same list is loaded concurrently', async () => {
        const store = useMessageStore();

        await Promise.all([store.load('permit-1'), store.load('permit-1')]);

        expect(getThreadsForResource).toHaveBeenCalledTimes(1);
    });

    it('falls back to an empty list when the fetch fails', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.mocked(getThreadsForResource).mockRejectedValueOnce(
            new Error('nope'),
        );
        const store = useMessageStore();

        await store.load('permit-1');

        // An empty list and a failed one look the same, hence the message.
        expect(store.threadsFor('permit-1')).toEqual([]);
        expect(store.error).toContain('Messages could not be loaded.');
    });

    it('reports a failed archive without reloading the threads', async () => {
        vi.mocked(setThreadArchived).mockRejectedValueOnce(new Error('nope'));
        const store = useMessageStore();

        await store.setArchived('t1', true, 'permit-1');

        expect(store.error).toContain('This thread could not be archived.');
        // Nothing moved, and a reload would clear the message just set.
        expect(getThreadsForResource).not.toHaveBeenCalled();
    });

    it('sends a message then reloads that resource', async () => {
        const store = useMessageStore();

        await store.send({
            messageText: 'hi',
            recipientId: 'r1',
            resourceId: 'permit-1',
        });

        expect(createBcapMessage).toHaveBeenCalledOnce();
        expect(getThreadsForResource).toHaveBeenCalledWith('permit-1', false);
    });

    it('reloads both the active and archived lists after archiving', async () => {
        const store = useMessageStore();

        await store.setArchived('t1', true, 'permit-1');

        expect(setThreadArchived).toHaveBeenCalledWith('t1', true);
        reloadedBoth();
    });

    it('resolves or reopens a thread then reloads both lists', async () => {
        const store = useMessageStore();

        await store.setResolved('t1', true, 'permit-1');
        await store.setResolved('t1', false, 'permit-1');

        expect(setThreadResolved).toHaveBeenCalledWith('t1', true);
        expect(setThreadResolved).toHaveBeenCalledWith('t1', false);
        reloadedBoth();
    });

    it('reports a failed resolve without reloading the threads', async () => {
        vi.mocked(setThreadResolved).mockRejectedValueOnce(new Error('nope'));
        const store = useMessageStore();

        await store.setResolved('t1', true, 'permit-1');

        expect(store.error).toContain('This thread could not be updated.');
        expect(getThreadsForResource).not.toHaveBeenCalled();
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

    it("loads a thread's messages into openMessages", async () => {
        vi.mocked(getMessagesForThread).mockResolvedValue([
            { id: 'm1', author: 'Amy', text: 'hi', date: 'x', attachments: [] },
        ]);
        const store = useMessageStore();

        await store.loadThreadMessages('thread-1');

        expect(getMessagesForThread).toHaveBeenCalledWith('thread-1');
        expect(store.openMessages).toHaveLength(1);
    });
});
