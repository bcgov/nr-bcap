import { apiFetchJson } from '@/bcap/api.ts';
import { useUserStore } from './user.ts';
import type { UserProfile } from './user.ts';

vi.mock('@/bcap/api.ts', () => ({ apiFetchJson: vi.fn() }));

const mockFetchJson = vi.mocked(apiFetchJson);

const profile = (isInternal: boolean) =>
    ({
        username: 'someone',
        first_name: '',
        last_name: '',
        groups: isInternal ? ['Archaeology Branch'] : ['Submitter'],
        is_internal: isInternal,
    }) as UserProfile;

beforeEach(() => {
    mockFetchJson.mockReset();
});

describe('user store', () => {
    it('loads the profile once and keeps it', async () => {
        mockFetchJson.mockResolvedValue(profile(true));
        const store = useUserStore();

        expect(await store.load()).toEqual(profile(true));
        await store.load();

        expect(mockFetchJson).toHaveBeenCalledTimes(1);
        expect(mockFetchJson).toHaveBeenCalledWith('/bcap/user_profile');
        expect(store.isInternal).toBe(true);
    });

    it('reports an applicant as external', async () => {
        mockFetchJson.mockResolvedValue(profile(false));
        const store = useUserStore();

        await store.load();

        expect(store.isInternal).toBe(false);
    });

    it('retries after a failure rather than caching it', async () => {
        // The endpoint refuses anyone not signed in, so this is also the path a
        // signed-out user takes; the route guard turns it into a refusal.
        mockFetchJson.mockRejectedValueOnce(new Error('403'));
        const store = useUserStore();

        await expect(store.load()).rejects.toThrow('403');
        expect(store.isInternal).toBe(false);

        mockFetchJson.mockResolvedValue(profile(true));
        expect(await store.load()).toEqual(profile(true));
    });

    it('treats a profile that fails validation as no profile', async () => {
        vi.spyOn(console, 'warn').mockImplementation(() => {});
        mockFetchJson.mockResolvedValue({ username: 'someone' });
        const store = useUserStore();

        expect(await store.load()).toBeNull();
        expect(store.isInternal).toBe(false);
    });
});
