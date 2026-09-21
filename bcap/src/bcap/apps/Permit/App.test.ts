import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import { apiFetchJson } from '@/bcap/api.ts';
import App from './App.vue';
import type { UserProfile } from '@/bcap/stores/user.ts';

// Partial: the guard checks the real ApiError with instanceof.
vi.mock('@/bcap/api.ts', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/bcap/api.ts')>()),
    apiFetchJson: vi.fn(),
}));

const mockFetchJson = vi.mocked(apiFetchJson);

const profile = (isInternal: boolean) =>
    ({
        username: 'someone',
        first_name: '',
        last_name: '',
        groups: [],
        is_internal: isInternal,
    }) as unknown as UserProfile;

const routes = [
    {
        path: '/',
        name: 'root',
        component: { template: '<div class="applicant-page" />' },
    },
    {
        path: '/staff',
        name: 'internal-root',
        component: { template: '<div class="staff-page" />' },
        meta: { requiresInternal: true },
    },
];

// Mirrors the plugin bootstrap, where the router's first navigation runs before
// the app mounts. Landing on the route before mounting is what makes sure a
// guard registered in setup is never the thing being tested here.
const mountApp = async (landingPath = '/') => {
    const router = createRouter({ history: createMemoryHistory(), routes });
    router.push(landingPath);
    await router.isReady();
    const wrapper = mount(App, {
        global: { plugins: [router], stubs: { Toast: true } },
    });
    await flushPromises();
    return { wrapper, router };
};

// An aborted navigation rejects; the assertions cover the outcome.
const navigate = (router: ReturnType<typeof createRouter>, path: string) =>
    router.push(path).catch(() => undefined);

beforeEach(() => {
    mockFetchJson.mockReset();
});

describe('route guard', () => {
    it('renders the landing page for a signed-in applicant', async () => {
        mockFetchJson.mockResolvedValue(profile(false));

        const { wrapper } = await mountApp();

        expect(wrapper.find('.applicant-page').exists()).toBe(true);
        expect(wrapper.find('.access-error').exists()).toBe(false);
    });

    it('refuses the landing page when the profile cannot be loaded', async () => {
        // The endpoint refuses anyone not signed in, so this is the signed-out
        // path. The landing route is the one a guard is easiest to miss.
        mockFetchJson.mockRejectedValue(new Error('403'));

        const { wrapper } = await mountApp();

        expect(wrapper.find('.applicant-page').exists()).toBe(false);
        expect(wrapper.find('.access-error').text()).toContain(
            'You need to be signed in',
        );
    });

    it('refuses a staff-only landing page to an applicant', async () => {
        mockFetchJson.mockResolvedValue(profile(false));

        const { wrapper } = await mountApp('/staff');

        expect(wrapper.find('.staff-page').exists()).toBe(false);
        expect(wrapper.find('.access-error').text()).toContain(
            'Archaeology Branch staff',
        );
    });

    it('lets staff into a staff-only page', async () => {
        mockFetchJson.mockResolvedValue(profile(true));

        const { wrapper } = await mountApp('/staff');

        expect(wrapper.find('.staff-page').exists()).toBe(true);
        expect(wrapper.find('.access-error').exists()).toBe(false);
    });

    it('refuses an applicant who navigates to a staff-only page', async () => {
        mockFetchJson.mockResolvedValue(profile(false));
        const { wrapper, router } = await mountApp();

        await navigate(router, '/staff');
        await flushPromises();

        // Refused in place rather than redirected: the staff pages are their own
        // arches plugin, so there is nowhere sensible to send them.
        expect(wrapper.find('.staff-page').exists()).toBe(false);
        expect(wrapper.find('.access-error').exists()).toBe(true);
    });

    it('asks for the profile once across several navigations', async () => {
        mockFetchJson.mockResolvedValue(profile(true));
        const { router } = await mountApp();

        await navigate(router, '/staff');
        await navigate(router, '/');
        await flushPromises();

        expect(mockFetchJson).toHaveBeenCalledTimes(1);
    });
});
