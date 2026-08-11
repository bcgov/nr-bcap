// Stand in for the runtime-injected `arches.urls` so these tests don't depend
// on the real arches.js bundle resolving. Mirrors the patterns in bcap/urls.py.

import {
    getUnlinkedContributors,
    getAssignableGroups,
    issueRegistrationLink,
} from './api';

function mockFetchOk(body: unknown) {
    return vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(body),
        text: vi.fn().mockResolvedValue(''),
    });
}

function mockFetchError(status: number, statusText: string, body = '') {
    return vi.fn().mockResolvedValue({
        ok: false,
        status,
        statusText,
        json: vi.fn().mockResolvedValue({}),
        text: vi.fn().mockResolvedValue(body),
    });
}

beforeEach(() => {
    vi.restoreAllMocks();
});

describe('getUnlinkedContributors', () => {
    it('appends the search query when provided', async () => {
        vi.stubGlobal('fetch', mockFetchOk([]));

        await getUnlinkedContributors('jane doe');

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/unlinked_contributors?search=jane%20doe',
            expect.anything(),
        );
    });

    it('omits the query when no search term', async () => {
        vi.stubGlobal('fetch', mockFetchOk([]));

        await getUnlinkedContributors();

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/unlinked_contributors',
            expect.anything(),
        );
    });
});

describe('issueRegistrationLink error flattening', () => {
    it('surfaces a DRF { detail } message', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(
                400,
                'Bad Request',
                JSON.stringify({ detail: 'Already linked.' }),
            ),
        );

        await expect(issueRegistrationLink({ groups: [] })).rejects.toThrow(
            'Already linked.',
        );
    });

    it('flattens nested field errors instead of dumping JSON', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchError(
                400,
                'Bad Request',
                JSON.stringify({
                    new_contributor: {
                        email: ['Enter a valid email address.'],
                    },
                }),
            ),
        );

        await expect(issueRegistrationLink({ groups: [] })).rejects.toThrow(
            'Enter a valid email address.',
        );
    });

    it('falls back to raw text when the body is not JSON', async () => {
        vi.stubGlobal('fetch', mockFetchError(500, 'Server Error', 'boom'));

        await expect(issueRegistrationLink({ groups: [] })).rejects.toThrow(
            'boom',
        );
    });
});

describe('getAssignableGroups', () => {
    it('returns the group list on success', async () => {
        vi.stubGlobal('fetch', mockFetchOk(['Submitter', 'Permit Decider']));

        const result = await getAssignableGroups();

        expect(fetch).toHaveBeenCalledWith(
            '/bcap/api/assignable_groups',
            expect.anything(),
        );
        expect(result).toEqual(['Submitter', 'Permit Decider']);
    });
});
