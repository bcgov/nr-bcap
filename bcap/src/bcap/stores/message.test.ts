import { useMessageStore } from '@/bcap/stores/message.ts';
import {
    createBcapMessage,
    getMessagesForThread,
    getSubmissionModulesUnreadCounts,
    getThreadsForResource,
    markMessageAsRead,
    setThreadArchived,
} from '@/bcap/apps/Permit/api.ts';
import type { MessageThread, FormattedMessage } from '@/bcap/types.ts';

vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    createBcapMessage: vi.fn(),
    getMessagesForThread: vi.fn(),
    getSubmissionModulesUnreadCounts: vi.fn(),
    getThreadsForResource: vi.fn(),
    markMessageAsRead: vi.fn(),
    setThreadArchived: vi.fn(),
}));

const thread = (over: Partial<MessageThread> = {}): MessageThread => ({
    id: 't1',
    topic: 'General Question',
    startedBy: 'Amy',
    lastMessageDate: '',
    hasUnread: false,
    unreadCount: 0,
    ...over,
});

describe('message store', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(getThreadsForResource).mockResolvedValue([]);
    });

    it("loads a resource's threads and sums their unread counts", async () => {
        vi.mocked(getThreadsForResource).mockResolvedValue([
            thread({ id: 'a', unreadCount: 2, hasUnread: true }),
            thread({ id: 'b', unreadCount: 5, hasUnread: true }),
        ]);
        const store = useMessageStore();

        await store.load('permit-1');

        expect(store.threadsFor('permit-1')).toHaveLength(2);
        expect(store.unreadCount('permit-1')).toBe(7);
        // A resource never loaded is empty, not an error.
        expect(store.threadsFor('permit-2')).toEqual([]);
        expect(store.unreadCount('permit-2')).toBe(0);
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

    it('shares one in-flight fetch when the same list is loaded concurrently', async () => {
        const store = useMessageStore();

        await Promise.all([store.load('permit-1'), store.load('permit-1')]);

        expect(getThreadsForResource).toHaveBeenCalledTimes(1);
    });

    it('falls back to an empty list when the fetch fails', async () => {
        vi.mocked(getThreadsForResource).mockRejectedValueOnce(
            new Error('nope'),
        );
        const store = useMessageStore();

        await store.load('permit-1');

        expect(store.threadsFor('permit-1')).toEqual([]);
    });

    it('sends a message then reloads that resource', async () => {
        const store = useMessageStore();

        await store.send({
            messageText: 'hi',
            recipientId: 'r1',
            applicationId: 'APP-1',
            resourceId: 'permit-1',
        });

        expect(createBcapMessage).toHaveBeenCalledOnce();
        expect(getThreadsForResource).toHaveBeenCalledWith('permit-1', false);
    });

    it('reloads both the active and archived lists after archiving', async () => {
        const store = useMessageStore();

        await store.setArchived('t1', true, 'permit-1');

        expect(setThreadArchived).toHaveBeenCalledWith('t1', true);
        expect(vi.mocked(getThreadsForResource).mock.calls).toEqual(
            expect.arrayContaining([
                ['permit-1', false],
                ['permit-1', true],
            ]),
        );
    });

    it('maps module tile ids to their unread counts', async () => {
        vi.mocked(getSubmissionModulesUnreadCounts).mockResolvedValue([
            { module_id: 'mod-a', unread_count: 3 },
            { module_id: 'mod-b', unread_count: 0 },
        ]);
        const store = useMessageStore();

        await store.loadModuleUnread('submission-1');

        expect(store.moduleUnreadCount('mod-a')).toBe(3);
        expect(store.moduleUnreadCount('mod-b')).toBe(0);
        // An unknown module reads as zero, not undefined.
        expect(store.moduleUnreadCount('mod-x')).toBe(0);
    });

    it("loads a thread's messages into openMessages", async () => {
        vi.mocked(getMessagesForThread).mockResolvedValue([
            { id: 'm1', author: 'Amy', text: 'hi', date: 'x', isUnread: false },
        ]);
        const store = useMessageStore();

        await store.loadThreadMessages('thread-1');

        expect(getMessagesForThread).toHaveBeenCalledWith('thread-1');
        expect(store.openMessages).toHaveLength(1);
    });

    it('marks only the open thread unread messages read', async () => {
        vi.mocked(getMessagesForThread).mockResolvedValue([
            { id: 'm1', author: '', text: 'a', date: '', isUnread: true },
            { id: 'm2', author: '', text: 'b', date: '', isUnread: false },
            { id: 'm3', author: '', text: 'c', date: '', isUnread: true },
        ]);
        const store = useMessageStore();
        const t = thread({ hasUnread: true, unreadCount: 2 });

        // Messages live in the store, loaded for the open thread.
        await store.loadThreadMessages(t.id);
        await store.markThreadRead(t);

        expect(markMessageAsRead).toHaveBeenCalledTimes(2);
        expect(markMessageAsRead).toHaveBeenCalledWith('m1');
        expect(markMessageAsRead).toHaveBeenCalledWith('m3');
        expect(markMessageAsRead).not.toHaveBeenCalledWith('m2');
        expect(t.hasUnread).toBe(false);
        expect(t.unreadCount).toBe(0);
        expect(
            store.openMessages.every((m: FormattedMessage) => !m.isUnread),
        ).toBe(true);
    });

    it('does nothing when the thread has no unread messages', async () => {
        const store = useMessageStore();

        await store.markThreadRead(thread({ hasUnread: false }));

        expect(markMessageAsRead).not.toHaveBeenCalled();
    });
});
