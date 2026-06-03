import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import type { PermitRequirementSchema } from '@/bcap/schema/PermitRequirementSchema.ts';

vi.mock('vue-router', () => ({
    useRoute: () => ({ query: { id: 'res-1' } }),
}));

vi.mock('arches', () => ({
    default: {
        urls: {
            api_process_requirements: (id: string) =>
                `/bcap/api/resource/process_requirement/${id}`,
        },
    },
}));

vi.mock('@/bcap/components/pages/api.ts', () => ({
    getProcessRequirementData: vi.fn(),
}));

import { getProcessRequirementData } from '@/bcap/components/pages/api.ts';
import TaskChecklist from './TaskChecklist.vue';

const mockedGet = vi.mocked(getProcessRequirementData);

// Minimal requirement payload: a name, two sub-requirements (one satisfied,
// one not), and no dates yet. Cast loosely — the component only reads a slice.
function buildRequirement(): PermitRequirementSchema {
    return {
        aliased_data: {
            requirement_identification: {
                aliased_data: {
                    requirement_name: { display_value: 'Heritage Permit' },
                },
            },
            requirement_execution_duration: {
                aliased_data: {
                    requirement_process_start_date: { node_value: null },
                    requirement_process_completion_date: { node_value: null },
                },
            },
            sub_requirement: [
                {
                    tileid: 't1',
                    aliased_data: {
                        sub_requirement_name: {
                            display_value: 'Submit application forms',
                        },
                        sub_requirement_satisfied: { node_value: true },
                        sub_requirement_assessment_notes: { node_value: '' },
                    },
                },
                {
                    tileid: 't2',
                    aliased_data: {
                        sub_requirement_name: {
                            display_value: 'Pay processing fee',
                        },
                        sub_requirement_satisfied: { node_value: false },
                        sub_requirement_assessment_notes: { node_value: '' },
                    },
                },
            ],
        },
    } as unknown as PermitRequirementSchema;
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe('TaskChecklist', () => {
    it('renders the requirement name and each sub-requirement after loading', async () => {
        mockedGet.mockResolvedValue(buildRequirement());

        const wrapper = mount(TaskChecklist);
        await flushPromises();

        expect(mockedGet).toHaveBeenCalledWith('res-1');
        expect(wrapper.text()).toContain('Heritage Permit');
        expect(wrapper.text()).toContain('Submit application forms');
        expect(wrapper.text()).toContain('Pay processing fee');
    });

    it('reflects each sub-requirement satisfied state in its checkbox', async () => {
        mockedGet.mockResolvedValue(buildRequirement());

        const wrapper = mount(TaskChecklist);
        await flushPromises();

        const checkboxes = wrapper.findAll<HTMLInputElement>('.req-checkbox');
        expect(checkboxes).toHaveLength(2);
        expect(checkboxes[0].element.checked).toBe(true);
        expect(checkboxes[1].element.checked).toBe(false);
    });

    it('shows "Pending" date pills when no start/completion dates are set', async () => {
        mockedGet.mockResolvedValue(buildRequirement());

        const wrapper = mount(TaskChecklist);
        await flushPromises();

        const pills = wrapper.findAll('.date-pill');
        expect(pills).toHaveLength(2);
        expect(pills[0].text()).toContain('Pending');
        expect(pills[1].text()).toContain('Pending');
        // No dates yet, so neither pill is in its active/complete state.
        expect(pills[0].classes()).not.toContain('active');
        expect(pills[1].classes()).not.toContain('complete');
    });

    it('shows an error message when loading the requirement fails', async () => {
        mockedGet.mockRejectedValue(new Error('boom'));

        const wrapper = mount(TaskChecklist);
        await flushPromises();

        expect(wrapper.find('.status-state.error').exists()).toBe(true);
        expect(wrapper.text()).toContain('Failed to load checklist data');
    });
});
