import type { PermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';

const { fetchPermitDetails } = vi.hoisted(() => ({
    fetchPermitDetails: vi.fn(),
}));
vi.mock('@/bcap/apps/Permit/api.ts', () => ({ fetchPermitDetails }));

import { usePermitHeaderStore } from './permitHeader.ts';

const aliased = (
    opts: {
        projectName?: string;
        applicationNumber?: string;
        submissionType?: string;
        sector?: string;
        submittedDate?: string;
    } = {},
) =>
    ({
        application_identification: {
            aliased_data: {
                project_name: { display_value: opts.projectName },
                application_id: { display_value: opts.applicationNumber },
                filing_type: { display_value: opts.submissionType },
            },
        },
        proposed_project: {
            aliased_data: {
                development_project_details: {
                    aliased_data: {
                        industrial_sector: { display_value: opts.sector },
                    },
                },
            },
        },
        application_admin: {
            aliased_data: {
                application_submission_date: {
                    display_value: opts.submittedDate,
                },
            },
        },
    }) as unknown as PermitApplicationResourceAliasedData;

beforeEach(() => {
    fetchPermitDetails.mockReset();
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('setFromAliased', () => {
    it('maps every header field off the permit', () => {
        const store = usePermitHeaderStore();

        const header = store.setFromAliased(
            'permit-1',
            aliased({
                projectName: 'My Project',
                applicationNumber: 'APP-1',
                submissionType: 'Site Visit',
                sector: 'Forestry',
                submittedDate: '2026-01-01',
            }),
        );

        expect(header).toEqual({
            projectName: 'My Project',
            applicationNumber: 'APP-1',
            submissionType: 'Site Visit',
            sector: 'Forestry',
            submittedDate: '2026-01-01',
        });
        expect(store.state.permitId).toBe('permit-1');
    });

    it('names an unnamed permit and marks an unissued number pending', () => {
        const store = usePermitHeaderStore();

        expect(store.setFromAliased('permit-1', aliased())).toEqual({
            projectName: 'Unnamed Project',
            applicationNumber: 'Pending',
            submissionType: '',
            // Left empty rather than stating a sector that was never given.
            sector: '',
            submittedDate: null,
        });
    });
});

describe('load', () => {
    it('fetches a permit it does not already hold', async () => {
        fetchPermitDetails.mockResolvedValue(
            aliased({ projectName: 'Fetched' }),
        );
        const store = usePermitHeaderStore();

        const header = await store.load('permit-1');

        expect(fetchPermitDetails).toHaveBeenCalledWith('permit-1');
        expect(header?.projectName).toBe('Fetched');
    });

    it('does not refetch the permit it already holds', async () => {
        const store = usePermitHeaderStore();
        store.setFromAliased('permit-1', aliased({ projectName: 'Cached' }));

        const header = await store.load('permit-1');

        expect(fetchPermitDetails).not.toHaveBeenCalled();
        expect(header?.projectName).toBe('Cached');
    });

    it('returns the stale header rather than throwing when the fetch fails', async () => {
        const store = usePermitHeaderStore();
        store.setFromAliased('permit-1', aliased({ projectName: 'Cached' }));
        fetchPermitDetails.mockRejectedValue(new Error('boom'));

        const header = await store.load('permit-2');

        expect(header?.projectName).toBe('Cached');
        // The permit id is left on the old one, so a retry still fetches.
        expect(store.state.permitId).toBe('permit-1');
    });

    it('does nothing without a permit id', async () => {
        const store = usePermitHeaderStore();

        expect(await store.load('')).toBeNull();
        expect(fetchPermitDetails).not.toHaveBeenCalled();
    });
});
