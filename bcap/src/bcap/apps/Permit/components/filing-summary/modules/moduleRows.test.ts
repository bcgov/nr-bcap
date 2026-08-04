import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { PermitApplicationProcessModuleTile } from '@/bcap/client/types.gen.ts';

vi.mock('arches', () => ({
    default: {
        urls: {
            plugin: (slug: string) => `/plugins/${slug}`,
        },
    },
}));

const { fetchRequirementDetails } = vi.hoisted(() => ({
    fetchRequirementDetails: vi.fn(),
}));
vi.mock('@/bcap/apps/Permit/api.ts', () => ({ fetchRequirementDetails }));

// The detail cache is module-level and never cleared, so each test re-imports
// the module for a fresh one rather than inheriting the previous test's rows.
let rows: typeof import('./moduleRows.ts');

beforeEach(async () => {
    vi.resetModules();
    fetchRequirementDetails.mockReset();
    fetchRequirementDetails.mockResolvedValue({});
    rows = await import('./moduleRows.ts');
});

type Req = { name?: string; resourceId?: string; order?: number };

const moduleTile = (
    opts: {
        tileid?: string;
        name?: string;
        moduleId?: string;
        moduleIdValue?: number;
        order?: number;
        completedDate?: string;
        isCompleted?: boolean;
        requirements?: Req[];
    } = {},
): PermitApplicationProcessModuleTile =>
    ({
        tileid: opts.tileid,
        aliased_data: {
            module_name: opts.name ? { display_value: opts.name } : undefined,
            module_id:
                opts.moduleId || opts.moduleIdValue !== undefined
                    ? {
                          display_value: opts.moduleId,
                          node_value: opts.moduleIdValue,
                      }
                    : undefined,
            module_order:
                opts.order === undefined
                    ? undefined
                    : { node_value: opts.order },
            module_completed_date: opts.completedDate
                ? { display_value: opts.completedDate }
                : undefined,
            is_module_completed: { node_value: opts.isCompleted ?? false },
            process_requirement: (opts.requirements ?? []).map((req) => ({
                aliased_data: {
                    process_requirement_order:
                        req.order === undefined
                            ? undefined
                            : { node_value: req.order },
                    process_requirement: {
                        display_value: req.name,
                        node_value: req.resourceId
                            ? [{ resourceId: req.resourceId }]
                            : undefined,
                    },
                    ministry_assignee: undefined,
                },
            })),
        },
    }) as unknown as PermitApplicationProcessModuleTile;

const detail = (opts: {
    name?: string;
    type?: string;
    satisfied?: boolean;
    internal?: boolean;
    host?: string;
}) => ({
    aliased_data: {
        requirement_identification: {
            aliased_data: {
                requirement_name: { display_value: opts.name ?? '' },
                is_template_requirement: {
                    aliased_data: {
                        process_requirement_type: {
                            display_value: opts.type ?? 'Standard',
                        },
                        is_internal_requirement: {
                            node_value: opts.internal ?? false,
                        },
                    },
                },
            },
        },
        sub_requirement_assessment_n1: {
            aliased_data: {
                requirement_status: { node_value: opts.satisfied ?? false },
            },
        },
        requirement_data: {
            aliased_data: {
                submission_data: {
                    aliased_data: {
                        submission_data: {
                            node_value: opts.host
                                ? [{ resourceId: opts.host }]
                                : undefined,
                        },
                    },
                },
            },
        },
    },
});

describe('type predicates', () => {
    it('matches the submission-bearing types regardless of case', () => {
        expect(rows.hasSubmission('Workflow')).toBe(true);
        expect(rows.hasSubmission('DOCUMENT SUBMISSION')).toBe(true);
        expect(rows.hasSubmission('Checklist')).toBe(false);
    });

    it('matches any type containing "checklist"', () => {
        expect(rows.isChecklist('Site Visit Checklist')).toBe(true);
        expect(rows.isChecklist('Workflow')).toBe(false);
    });
});

describe('checklist links', () => {
    it('builds the fill-out and edit hrefs off the dashboard plugin', () => {
        expect(rows.checklistHref('r-1')).toBe(
            '/plugins/internal-permit-dashboard/checklist?id=r-1',
        );
        expect(rows.editChecklistHref('r-1')).toBe(
            '/plugins/internal-permit-dashboard/EditChecklist?id=r-1',
        );
    });

    it('appends the permit, and the staff flag only when truthy', () => {
        // Assumes the href already carries a query.
        expect(rows.withPermitContext('/x?a=1', 'permit-1', '')).toBe(
            '/x?a=1&permit=permit-1',
        );
        expect(rows.withPermitContext('/x?a=1', 'permit-1', '1')).toBe(
            '/x?a=1&permit=permit-1&staff=1',
        );
    });
});

describe('toRow', () => {
    it('falls back to placeholders for a tile with nothing set', () => {
        const row = rows.toRow(moduleTile({ requirements: [{ order: 1 }] }));

        expect(row).toMatchObject({
            tileid: '',
            name: 'Untitled module',
            moduleId: '',
            completedDate: '',
            isCompleted: false,
            order: 0,
            hostResourceId: '',
        });
        expect(row.requirements[0]).toMatchObject({
            name: 'Requirement',
            resourceId: '',
            href: '',
        });
    });

    it('maps the module card nodes', () => {
        const row = rows.toRow(
            moduleTile({
                tileid: 't-1',
                name: 'Investigation',
                moduleId: 'INV-2',
                order: 3,
                completedDate: '2026-02-02',
                isCompleted: true,
            }),
        );

        expect(row).toMatchObject({
            tileid: 't-1',
            name: 'Investigation',
            moduleId: 'INV-2',
            order: 3,
            completedDate: '2026-02-02',
            isCompleted: true,
        });
        // A module id with no display value still shows its raw value.
        expect(rows.toRow(moduleTile({ moduleIdValue: 7 })).moduleId).toBe('7');
    });

    it('sorts requirements by flow order and defaults their status to unknown', () => {
        const row = rows.toRow(
            moduleTile({
                requirements: [
                    { name: 'Beta', resourceId: 'r-b', order: 2 },
                    { name: 'Alpha', resourceId: 'r-a', order: 1 },
                ],
            }),
        );

        expect(row.requirements.map((req) => req.name)).toEqual([
            'Alpha',
            'Beta',
        ]);
        // Nothing is cached yet, so status/type are unknown and the href is the
        // plain resource page.
        expect(row.requirements[0]).toMatchObject({
            title: 'Alpha',
            type: '',
            satisfied: null,
            internal: null,
            href: '/bcap/resource/r-a',
        });
    });
});

describe('hydrateRows', () => {
    const rowWith = (
        tileid: string,
        resourceId: string,
        name = 'Placeholder',
    ) =>
        rows.toRow(
            moduleTile({
                tileid,
                requirements: [{ name, resourceId, order: 1 }],
            }),
        );

    it('fetches the uncached ids and fills the rows in place', async () => {
        fetchRequirementDetails.mockResolvedValue({
            'r-1': detail({
                name: 'Real Name',
                type: 'Checklist',
                satisfied: true,
                internal: true,
                host: 'host-1',
            }),
        });
        const row = rowWith('t-1', 'r-1');
        const requirement = row.requirements[0];

        await rows.hydrateRows([row]);

        expect(fetchRequirementDetails).toHaveBeenCalledWith(['r-1']);
        // Mutated in place: the caller keeps its own row references.
        expect(row.requirements[0]).toBe(requirement);
        expect(requirement).toMatchObject({
            title: 'Real Name',
            type: 'Checklist',
            satisfied: true,
            internal: true,
            hostResourceId: 'host-1',
            href: '/plugins/internal-permit-dashboard/checklist?id=r-1',
        });
        // The module files against its first requirement's submission host.
        expect(row.hostResourceId).toBe('host-1');
    });

    it('asks for each id once and stops asking once it is cached', async () => {
        fetchRequirementDetails.mockResolvedValue({
            'r-1': detail({ name: 'One' }),
        });
        const first = rowWith('t-1', 'r-1');
        const second = rowWith('t-2', 'r-1');

        await rows.hydrateRows([first, second]);
        expect(fetchRequirementDetails).toHaveBeenCalledWith(['r-1']);
        // Cached now, so neither row asks again and neither needs details.
        expect(rows.rowsNeedingDetails([first, second])).toEqual([]);
    });

    it('leaves a requirement the fetch did not return alone', async () => {
        fetchRequirementDetails.mockResolvedValue({});
        const row = rowWith('t-1', 'r-1');

        await rows.hydrateRows([row]);

        expect(row.requirements[0].satisfied).toBeNull();
        expect(row.requirements[0].type).toBe('');
    });
});

describe('rowsNeedingDetails', () => {
    it('picks the rows holding an uncached requirement, ignoring hrefless ones', () => {
        const needy = rows.toRow(
            moduleTile({
                tileid: 't-1',
                requirements: [{ name: 'A', resourceId: 'r-1', order: 1 }],
            }),
        );
        const blank = rows.toRow(
            moduleTile({ tileid: 't-2', requirements: [{ order: 1 }] }),
        );

        expect(rows.rowsNeedingDetails([needy, blank])).toEqual([needy]);
    });
});

describe('cacheSatisfied', () => {
    it('keeps the cache in step so a rebuilt row seeds the new status', async () => {
        fetchRequirementDetails.mockResolvedValue({
            'r-1': detail({ name: 'Alpha', satisfied: false }),
        });
        const tile = moduleTile({
            tileid: 't-1',
            requirements: [{ name: 'A', resourceId: 'r-1', order: 1 }],
        });
        await rows.hydrateRows([rows.toRow(tile)]);

        rows.cacheSatisfied('r-1', true);

        expect(rows.toRow(tile).requirements[0].satisfied).toBe(true);
    });
});

describe('clearRequirementCache', () => {
    it('drops what was cached, so the next permit refetches', async () => {
        fetchRequirementDetails.mockResolvedValue({
            'r-1': detail({ name: 'Alpha', satisfied: true }),
        });
        const tile = moduleTile({
            tileid: 't-1',
            requirements: [{ name: 'A', resourceId: 'r-1', order: 1 }],
        });
        await rows.hydrateRows([rows.toRow(tile)]);

        rows.clearRequirementCache();

        const row = rows.toRow(tile);
        expect(row.requirements[0].satisfied).toBeNull();
        expect(rows.rowsNeedingDetails([row])).toEqual([row]);
    });
});
