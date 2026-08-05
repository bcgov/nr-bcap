import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { ref, nextTick } from 'vue';
import type { ProcessRequirement } from '@/bcap/client/types.gen.ts';

// Dynamic route query so individual tests can override the resource ID.
const mockRouteQuery = ref<Record<string, string | undefined>>({
    id: 'res-1',
});

vi.mock('vue-router', () => ({
    useRoute: () => ({ query: mockRouteQuery.value }),
}));

vi.mock('arches', () => ({
    default: {
        urls: {
            plugin: (slug: string) => `/plugins/${slug}`,
            api_process_requirements: (id: string) =>
                `/bcap/api/process_requirements/${id}`,
        },
    },
}));

// Only the header and requirement fetches are stubbed; the save path still goes
// through the real apiFetch so the PATCH assertions stay honest.
const { fetchPermitDetails } = vi.hoisted(() => ({
    fetchPermitDetails: vi.fn(),
}));
vi.mock('@/bcap/apps/Permit/api.ts', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@/bcap/apps/Permit/api.ts')>()),
    getProcessRequirementData: vi.fn(),
    fetchPermitDetails,
}));

import { getProcessRequirementData } from '@/bcap/apps/Permit/api.ts';
import TaskChecklist from './TaskChecklist.vue';

const mockedGet = vi.mocked(getProcessRequirementData);

const buildDuration = (
    startDate: string | null = null,
    completedDate: string | null = null,
) => ({
    tileid: 'duration-tile',
    aliased_data: {
        requirement_process_start_date: { node_value: startDate },
        requirement_process_completion_date: { node_value: completedDate },
        requirement_process_due_date: { node_value: null },
    },
});

const buildSubReq = (
    opts: {
        tileid?: string;
        name?: string;
        description?: string;
        satisfied?: boolean;
        notes?: unknown;
    } = {},
) => ({
    tileid: opts.tileid ?? 'sub-req-1',
    aliased_data: {
        checklist_item_name: {
            display_value: opts.name ?? 'Step One',
        },
        checklist_item_description: {
            display_value:
                opts.description !== undefined ? opts.description : 'A step',
        },
        checklist_item_completed: { node_value: opts.satisfied ?? false },
        checklist_item_assessment_notes: { node_value: opts.notes ?? null },
    },
});

const buildAssessment = (opts: { status?: boolean; notes?: unknown } = {}) => ({
    tileid: 'assessment-tile',
    aliased_data: {
        requirement_status: { node_value: opts.status ?? false },
        assessment_notes: { node_value: opts.notes ?? null },
    },
});

// Base builder. Pass `assessment: null` to hide the assessment section;
// omit it to include a default assessment tile.
const buildRequirement = (
    opts: {
        name?: string;
        startDate?: string | null;
        completedDate?: string | null;
        subRequirements?: ReturnType<typeof buildSubReq>[];
        assessment?: ReturnType<typeof buildAssessment> | null;
    } = {},
): ProcessRequirement => {
    const hasAssessment = 'assessment' in opts;
    return {
        descriptors: {
            en: {
                name: opts.name ?? 'APP-001 Heritage Permit',
                map_popup: '',
                description: '',
            },
        },
        aliased_data: {
            requirement_execution_duration: buildDuration(
                opts.startDate ?? null,
                opts.completedDate ?? null,
            ),
            requirement_data: {
                aliased_data: {
                    sub_requirement_n1: opts.subRequirements ?? [],
                },
            },
            ...(hasAssessment
                ? {
                      sub_requirement_assessment_n1:
                          opts.assessment ?? undefined,
                  }
                : { sub_requirement_assessment_n1: buildAssessment() }),
        },
        graph_has_different_publication: false,
        name: opts.name ?? 'APP-001 Heritage Permit',
        legacyid: '',
        createdtime: '',
        graph: '',
        graph_publication: '',
        resource_instance_lifecycle_state: '',
        principaluser: null,
    } as unknown as ProcessRequirement;
};

// Helper: simulate checking/unchecking a native checkbox via v-model.
const check = async (
    el: { element: HTMLInputElement; trigger: (e: string) => Promise<void> },
    checked: boolean,
) => {
    el.element.checked = checked;
    await el.trigger('change');
};

beforeEach(() => {
    mockRouteQuery.value = { id: 'res-1' };
    vi.clearAllMocks();
    fetchPermitDetails.mockResolvedValue(null);
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('TaskChecklist', () => {
    describe('loading and error states', () => {
        it('shows loading state while fetch is in-flight', () => {
            mockedGet.mockReturnValue(new Promise(() => {}));
            const wrapper = mount(TaskChecklist);
            expect(wrapper.find('.status-state').text()).toContain(
                'Loading checklist...',
            );
        });

        it('shows error when no resource ID is in the URL', async () => {
            mockRouteQuery.value = {};
            const wrapper = mount(TaskChecklist);
            await nextTick();
            expect(wrapper.find('.status-state.error').text()).toContain(
                'No resource ID provided in the URL.',
            );
        });

        it('shows an error message when the API call fails', async () => {
            mockedGet.mockRejectedValue(new Error('boom'));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.status-state.error').exists()).toBe(true);
            expect(wrapper.text()).toContain('Failed to load checklist data');
        });

        it('passes the resource ID from the URL to the API', async () => {
            mockRouteQuery.value = { id: 'resource-xyz' };
            mockedGet.mockResolvedValue(buildRequirement());
            mount(TaskChecklist);
            await flushPromises();
            expect(mockedGet).toHaveBeenCalledWith('resource-xyz');
        });
    });

    describe('permit context', () => {
        it('shows no crumbs and loads no header when opened standalone', async () => {
            mockedGet.mockResolvedValue(buildRequirement());

            const wrapper = mount(TaskChecklist);
            await flushPromises();

            expect(wrapper.find('.crumbs').exists()).toBe(false);
            expect(fetchPermitDetails).not.toHaveBeenCalled();
        });

        it('crumbs back to the permit and loads its header band', async () => {
            mockRouteQuery.value = {
                id: 'res-1',
                permit: 'permit-1',
            };
            mockedGet.mockResolvedValue(
                buildRequirement({ name: 'Site Checklist' }),
            );

            const wrapper = mount(TaskChecklist);
            await flushPromises();

            expect(fetchPermitDetails).toHaveBeenCalledWith('permit-1');
            expect(wrapper.find('.crumb-link').text()).toBe('Project Summary');
            expect(wrapper.find('.crumb-current').text()).toBe(
                'Site Checklist',
            );
        });

        it('keeps the staff view on the return trip', async () => {
            mockRouteQuery.value = {
                id: 'res-1',
                permit: 'permit-1',
                staff: '1',
            };
            mockedGet.mockResolvedValue(buildRequirement());

            const wrapper = mount(TaskChecklist);
            await flushPromises();

            expect(
                wrapper.findComponent({ name: 'RouterLinkStub' }).props('to'),
            ).toEqual({
                name: 'permitDetails',
                params: { id: 'permit-1' },
                query: { staff: '1' },
            });
        });
    });

    describe('page title', () => {
        it('displays the requirement name from descriptors', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({ name: 'APP-001 Heritage Permit' }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.page-title').text()).toContain(
                'APP-001 Heritage Permit',
            );
        });

        it('falls back to "Process Requirement" when the name is empty', async () => {
            mockedGet.mockResolvedValue(buildRequirement({ name: '' }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.page-title').text()).toBe(
                'Process Requirement',
            );
        });
    });

    describe('date pills', () => {
        it('shows "Pending" in both pills when no dates are set', async () => {
            mockedGet.mockResolvedValue(buildRequirement());
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            const pills = wrapper.findAll('.date-pill');
            expect(pills[0].text()).toContain('Pending');
            expect(pills[1].text()).toContain('Pending');
            expect(pills[0].classes()).not.toContain('active');
            expect(pills[1].classes()).not.toContain('complete');
        });

        it('shows start date with active class when start date is set', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({ startDate: '2024-01-15' }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            const startPill = wrapper.findAll('.date-pill')[0];
            expect(startPill.text()).toContain('2024-01-15');
            expect(startPill.classes()).toContain('active');
        });

        it('does not apply active class when start date is absent', async () => {
            mockedGet.mockResolvedValue(buildRequirement({ startDate: null }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.findAll('.date-pill')[0].classes()).not.toContain(
                'active',
            );
        });

        it('shows completion date with complete class when set', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    startDate: '2024-01-15',
                    completedDate: '2024-02-20',
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            const compPill = wrapper.findAll('.date-pill')[1];
            expect(compPill.text()).toContain('2024-02-20');
            expect(compPill.classes()).toContain('complete');
        });

        it('does not apply complete class when completion date is absent', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({ completedDate: null }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.findAll('.date-pill')[1].classes()).not.toContain(
                'complete',
            );
        });
    });

    describe('rendering sub-requirements', () => {
        it('renders the requirement name and each sub-requirement', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({ name: 'Submit application forms' }),
                        buildSubReq({
                            tileid: 'sub-2',
                            name: 'Pay processing fee',
                        }),
                    ],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.text()).toContain('APP-001 Heritage Permit');
            expect(wrapper.text()).toContain('Submit application forms');
            expect(wrapper.text()).toContain('Pay processing fee');
        });

        it('reflects each sub-requirement satisfied state in its checkbox', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({
                            tileid: 'sub-1',
                            name: 'Done',
                            satisfied: true,
                        }),
                        buildSubReq({
                            tileid: 'sub-2',
                            name: 'Pending',
                            satisfied: false,
                        }),
                    ],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            const boxes = wrapper.findAll<HTMLInputElement>('.req-checkbox');
            expect(boxes[0].element.checked).toBe(true);
            expect(boxes[1].element.checked).toBe(false);
        });

        it('renders description when present', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({ description: 'Examine all files' }),
                    ],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.req-desc').text()).toContain(
                'Examine all files',
            );
        });

        it('omits description element when description is empty', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ description: '' })],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.req-desc').exists()).toBe(false);
        });

        it('shows empty state when there are no sub-requirements', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({ subRequirements: [], assessment: null }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.checklist-items').text()).toContain(
                'No sub-requirements found for this process.',
            );
        });
    });

    describe('readText (notes rendering)', () => {
        it('renders empty string for a null notes node_value', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ notes: null })],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(
                wrapper.find<HTMLTextAreaElement>('.req-notes-input').element
                    .value,
            ).toBe('');
        });

        it('renders a plain string notes value directly', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({ notes: 'Plain string note' }),
                    ],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(
                wrapper.find<HTMLTextAreaElement>('.req-notes-input').element
                    .value,
            ).toBe('Plain string note');
        });

        it('extracts value from a localized {en: {value}} notes object', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({
                            notes: { en: { value: 'Localized note' } },
                        }),
                    ],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(
                wrapper.find<HTMLTextAreaElement>('.req-notes-input').element
                    .value,
            ).toBe('Localized note');
        });

        it('falls back to empty string when the en key is absent', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({ notes: { fr: { value: 'Bonjour' } } }),
                    ],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(
                wrapper.find<HTMLTextAreaElement>('.req-notes-input').element
                    .value,
            ).toBe('');
        });
    });

    describe('assessment section', () => {
        it('shows assessment section when assessment data exists', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    assessment: buildAssessment({ status: false }),
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.requirement-summary').exists()).toBe(true);
        });

        it('hides assessment section when assessment data is absent', async () => {
            mockedGet.mockResolvedValue(buildRequirement({ assessment: null }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.requirement-summary').exists()).toBe(false);
        });

        it('hides assessment section while loading', () => {
            mockedGet.mockReturnValue(new Promise(() => {}));
            const wrapper = mount(TaskChecklist);
            expect(wrapper.find('.requirement-summary').exists()).toBe(false);
        });

        it('reflects assessment status in the Requirement Review Completed checkbox', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    assessment: buildAssessment({ status: true }),
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(
                wrapper.find<HTMLInputElement>('#requirement_satisfied').element
                    .checked,
            ).toBe(true);
        });

        it('renders assessment notes via readText', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    assessment: buildAssessment({
                        notes: { en: { value: 'Overall looks good' } },
                    }),
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(
                wrapper.find<HTMLTextAreaElement>('#requirement-notes').element
                    .value,
            ).toBe('Overall looks good');
        });
    });

    describe('isDirty and actions bar', () => {
        it('hides the undo button before any edits', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({ subRequirements: [buildSubReq()] }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            expect(wrapper.find('.undo-btn').exists()).toBe(false);
        });

        it('shows the undo button after checking a sub-requirement checkbox', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            expect(wrapper.find('.undo-btn').exists()).toBe(true);
        });

        it('undo reverts a checkbox to its original state', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            expect(
                wrapper.find<HTMLInputElement>('.req-checkbox').element.checked,
            ).toBe(true);
            await wrapper.find('.undo-btn').trigger('click');
            await nextTick();
            expect(
                wrapper.find<HTMLInputElement>('.req-checkbox').element.checked,
            ).toBe(false);
        });

        it('the undo button disappears after undo', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.undo-btn').trigger('click');
            await nextTick();
            expect(wrapper.find('.undo-btn').exists()).toBe(false);
        });

        it('shows the undo button after editing the assessment checkbox', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    assessment: buildAssessment({ status: false }),
                }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(
                wrapper.find<HTMLInputElement>('#requirement_satisfied'),
                true,
            );
            expect(wrapper.find('.undo-btn').exists()).toBe(true);
        });
    });

    describe('saveChanges', () => {
        it('sends a PATCH to the correct URL', async () => {
            mockRouteQuery.value = { id: 'my-resource' };
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            const fetchMock = vi.fn().mockResolvedValue({ ok: true });
            vi.stubGlobal('fetch', fetchMock);
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            expect(fetchMock.mock.calls[0][0]).toContain(
                '/bcap/api/process_requirements/my-resource',
            );
            expect(fetchMock.mock.calls[0][1].method).toBe('PATCH');
        });

        it('includes aliased_data in the request body', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            const fetchMock = vi.fn().mockResolvedValue({ ok: true });
            vi.stubGlobal('fetch', fetchMock);
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            const body = JSON.parse(fetchMock.mock.calls[0][1].body);
            expect(body).toHaveProperty('aliased_data');
        });

        it('uses the CSRF token from the cookie', async () => {
            Object.defineProperty(document, 'cookie', {
                value: 'csrftoken=my-csrf; other=val',
                configurable: true,
            });
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            const fetchMock = vi.fn().mockResolvedValue({ ok: true });
            vi.stubGlobal('fetch', fetchMock);
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            expect(fetchMock.mock.calls[0][1].headers['X-CSRFToken']).toBe(
                'my-csrf',
            );
        });

        it('hides the undo button after a successful save', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            expect(wrapper.find('.undo-btn').exists()).toBe(false);
        });

        it('handles a failed save response without throwing', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({ ok: false, status: 500 }),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await expect(
                wrapper.find('.save-btn').trigger('click'),
            ).resolves.not.toThrow();
            await flushPromises();
        });

        it('disables save and undo buttons while a save is in-flight', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    assessment: null,
                }),
            );
            vi.stubGlobal(
                'fetch',
                vi.fn().mockReturnValue(new Promise(() => {})),
            );
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            wrapper.find('.save-btn').trigger('click');
            await nextTick();
            expect(
                wrapper.find<HTMLButtonElement>('.save-btn').element.disabled,
            ).toBe(true);
            expect(
                wrapper.find<HTMLButtonElement>('.undo-btn').element.disabled,
            ).toBe(true);
        });
    });

    describe('applyDerivedDates', () => {
        it('sets start date when the first sub-requirement is checked on save', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    startDate: null,
                    assessment: null,
                }),
            );
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            const startPill = wrapper.findAll('.date-pill')[0];
            expect(startPill.text()).toMatch(/\d{4}-\d{2}-\d{2}/);
            expect(startPill.classes()).toContain('active');
        });

        it('sets completion date when all sub-requirements are checked on save', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    completedDate: null,
                    assessment: null,
                }),
            );
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            const compPill = wrapper.findAll('.date-pill')[1];
            expect(compPill.text()).toMatch(/\d{4}-\d{2}-\d{2}/);
            expect(compPill.classes()).toContain('complete');
        });

        it('does not overwrite an existing start date', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [buildSubReq({ satisfied: false })],
                    startDate: '2024-01-01',
                    assessment: null,
                }),
            );
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(wrapper.find<HTMLInputElement>('.req-checkbox'), true);
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            expect(wrapper.findAll('.date-pill')[0].text()).toContain(
                '2024-01-01',
            );
        });

        it('clears completion date when a sub-requirement is unchecked on save', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({
                            tileid: 'sub-a',
                            name: 'Step A',
                            satisfied: true,
                        }),
                        buildSubReq({
                            tileid: 'sub-b',
                            name: 'Step B',
                            satisfied: true,
                        }),
                    ],
                    startDate: '2024-01-01',
                    completedDate: '2024-01-15',
                    assessment: null,
                }),
            );
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(
                wrapper.findAll<HTMLInputElement>('.req-checkbox')[0],
                false,
            );
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            const compPill = wrapper.findAll('.date-pill')[1];
            expect(compPill.text()).toContain('Pending');
            expect(compPill.classes()).not.toContain('complete');
        });

        it('does not set completion date when only some sub-requirements are checked', async () => {
            mockedGet.mockResolvedValue(
                buildRequirement({
                    subRequirements: [
                        buildSubReq({
                            tileid: 'sub-a',
                            name: 'Step A',
                            satisfied: false,
                        }),
                        buildSubReq({
                            tileid: 'sub-b',
                            name: 'Step B',
                            satisfied: false,
                        }),
                    ],
                    completedDate: null,
                    assessment: null,
                }),
            );
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
            const wrapper = mount(TaskChecklist);
            await flushPromises();
            await check(
                wrapper.findAll<HTMLInputElement>('.req-checkbox')[0],
                true,
            );
            await wrapper.find('.save-btn').trigger('click');
            await flushPromises();
            const compPill = wrapper.findAll('.date-pill')[1];
            expect(compPill.text()).toContain('Pending');
            expect(compPill.classes()).not.toContain('complete');
        });
    });
});
