import { ref } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';
import type { ProcessRequirement } from '@/bcap/client/types.gen.ts';

// Route query is controlled per-test via this ref.
const mockQuery = ref<Record<string, string | undefined>>({});
vi.mock('vue-router', () => ({
    useRoute: () => ({ query: mockQuery.value }),
}));

vi.mock('@/bcap/api.ts', () => ({ apiFetchJson: vi.fn() }));
vi.mock('@/bcap/apps/Permit/api.ts', () => ({
    saveChecklist: vi.fn(),
    // The header band loads through the permit header store.
    fetchPermitDetails: vi.fn(),
}));

import { apiFetchJson } from '@/bcap/api.ts';
import { saveChecklist, fetchPermitDetails } from '@/bcap/apps/Permit/api.ts';
import EditChecklist from './EditChecklist.vue';

const mockFetchJson = vi.mocked(apiFetchJson);
const mockSave = vi.mocked(saveChecklist);
const mockPermitDetails = vi.mocked(fetchPermitDetails);

const localized = (value: string) => ({ node_value: { en: { value } } });

// A loaded requirement with the given step names, in the aliased_data shape the
// component reads.
const requirementWith = (
    title: string,
    steps: { tileid: string; name: string; description?: string }[],
): ProcessRequirement =>
    ({
        aliased_data: {
            requirement_identification: {
                aliased_data: { requirement_name: localized(title) },
            },
            requirement_data: {
                aliased_data: {
                    sub_requirement_n1: steps.map((step, index) => ({
                        tileid: step.tileid,
                        aliased_data: {
                            checklist_item_name: localized(step.name),
                            checklist_item_description: localized(
                                step.description ?? '',
                            ),
                            checklist_item_sort_order: {
                                node_value: index + 1,
                            },
                        },
                    })),
                },
            },
        },
    }) as unknown as ProcessRequirement;

const stepNameInputs = (wrapper: ReturnType<typeof mount>) =>
    // The first .req-title-input is the list title; the rest are step names.
    wrapper.findAll<HTMLInputElement>('input.req-title-input').slice(1);

beforeEach(() => {
    mockQuery.value = {};
    mockFetchJson.mockReset();
    mockSave.mockReset().mockResolvedValue(undefined);
    mockPermitDetails.mockReset().mockResolvedValue(null as never);
});

describe('permit context', () => {
    it('shows no crumbs and loads no header when opened standalone', () => {
        const wrapper = mount(EditChecklist);

        expect(wrapper.find('.crumbs').exists()).toBe(false);
        expect(mockPermitDetails).not.toHaveBeenCalled();
    });

    it('crumbs back to the permit and loads its header band', async () => {
        mockQuery.value = { id: 'req-1', permit: 'permit-1' };
        mockFetchJson.mockResolvedValue(
            requirementWith('My Checklist', [{ tileid: 't1', name: 'Step A' }]),
        );

        const wrapper = mount(EditChecklist);
        await flushPromises();

        expect(mockPermitDetails).toHaveBeenCalledWith('permit-1');
        expect(wrapper.find('.crumb-link').text()).toBe('Project Summary');
        expect(wrapper.find('.crumb-current').text()).toBe('My Checklist');
    });

    it('keeps the staff view on the return trip', async () => {
        mockQuery.value = { permit: 'permit-1', staff: '1' };

        const wrapper = mount(EditChecklist);
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

describe('create mode (no route id)', () => {
    it('shows the create heading and one empty step, and does not fetch', () => {
        const wrapper = mount(EditChecklist);
        expect(wrapper.find('h2').text()).toBe('Create Process Requirement');
        expect(wrapper.findAll('.requirement-item')).toHaveLength(1);
        expect(wrapper.find('.btn-delete').exists()).toBe(false);
        expect(mockFetchJson).not.toHaveBeenCalled();
    });
});

describe('add and remove steps', () => {
    it('appends a step and shows delete buttons once there are several', async () => {
        const wrapper = mount(EditChecklist);
        await wrapper.find('.btn-secondary').trigger('click');
        expect(wrapper.findAll('.requirement-item')).toHaveLength(2);
        expect(wrapper.findAll('.btn-delete')).toHaveLength(2);
    });

    it('renumbers step labels after a removal', async () => {
        const wrapper = mount(EditChecklist);
        await wrapper.find('.btn-secondary').trigger('click');
        await wrapper.find('.btn-secondary').trigger('click');
        await wrapper.findAll('.btn-delete')[0].trigger('click');
        const labels = wrapper.findAll('label[for^="name-"]');
        expect(labels.map((l) => l.text())).toEqual([
            'Step 1 Title',
            'Step 2 Title',
        ]);
    });
});

describe('name validation', () => {
    it('blocks saving until every step has a title', async () => {
        const wrapper = mount(EditChecklist);
        const saveButton = wrapper.find<HTMLButtonElement>('.btn-primary');

        // One blank step: save disabled, hint shown, step-name input flagged.
        expect(saveButton.element.disabled).toBe(true);
        expect(wrapper.find('.validation-hint').exists()).toBe(true);
        expect(stepNameInputs(wrapper)[0].classes()).toContain('input-error');

        await stepNameInputs(wrapper)[0].setValue('Submit application');
        expect(saveButton.element.disabled).toBe(false);
        expect(wrapper.find('.validation-hint').exists()).toBe(false);
    });
});

describe('drag reorder', () => {
    it('reorders steps on drop and clears the dragging state', async () => {
        const wrapper = mount(EditChecklist);
        await wrapper.find('.btn-secondary').trigger('click');
        const inputs = stepNameInputs(wrapper);
        await inputs[0].setValue('First');
        await inputs[1].setValue('Second');

        const items = wrapper.findAll('.requirement-item');
        await items[0].trigger('dragstart');
        expect(wrapper.find('.is-dragging').exists()).toBe(true);
        await items[1].trigger('drop');
        await items[0].trigger('dragend');

        const after = stepNameInputs(wrapper);
        expect(after[0].element.value).toBe('Second');
        expect(after[1].element.value).toBe('First');
        expect(wrapper.find('.is-dragging').exists()).toBe(false);
    });
});

describe('edit mode (route id present)', () => {
    beforeEach(() => {
        mockQuery.value = { id: 'req-1' };
    });

    it('fetches by the aliased resource url and populates title and steps', async () => {
        mockFetchJson.mockResolvedValue(
            requirementWith('My Checklist', [
                { tileid: 't1', name: 'Step A' },
                { tileid: 't2', name: 'Step B' },
            ]),
        );
        const wrapper = mount(EditChecklist);
        await flushPromises();

        expect(wrapper.find('h2').text()).toBe('Edit Process Requirement');
        expect(mockFetchJson).toHaveBeenCalledWith(
            '/bcap/api/resource/process_requirement/req-1',
        );
        const names = stepNameInputs(wrapper).map((i) => i.element.value);
        expect(names).toEqual(['Step A', 'Step B']);
    });

    it('shows an error message when the load fails', async () => {
        mockFetchJson.mockRejectedValue(new Error('boom'));
        const wrapper = mount(EditChecklist);
        await flushPromises();
        expect(wrapper.find('.status-state').text()).toContain(
            'Error loading existing checklist data.',
        );
    });
});

describe('saving', () => {
    beforeEach(() => {
        mockQuery.value = { id: 'req-1' };
    });

    it('sends the current steps and shows a success message', async () => {
        mockFetchJson.mockResolvedValue(
            requirementWith('My Checklist', [{ tileid: 't1', name: 'Step A' }]),
        );
        const wrapper = mount(EditChecklist);
        await flushPromises();

        await wrapper.find('.btn-primary').trigger('click');
        await flushPromises();

        expect(mockSave).toHaveBeenCalledWith('req-1', 'My Checklist', [
            { tileid: 't1', name: 'Step A', description: '' },
        ]);
        expect(wrapper.find('.status-state').text()).toContain(
            'Checklist updated successfully!',
        );
    });

    it('refreshes after saving without flashing the loading state', async () => {
        mockFetchJson.mockResolvedValue(
            requirementWith('My Checklist', [{ tileid: 't1', name: 'Step A' }]),
        );
        const wrapper = mount(EditChecklist);
        await flushPromises();

        // A save that never resolves the refresh must not blank the form.
        let resolveReload: (value: ProcessRequirement) => void = () => {};
        mockFetchJson.mockImplementationOnce(
            () =>
                new Promise<ProcessRequirement>((resolve) => {
                    resolveReload = resolve;
                }),
        );
        await wrapper.find('.btn-primary').trigger('click');
        await flushPromises();

        // The step list is still on screen; no loading placeholder appeared.
        expect(wrapper.text()).not.toContain('Loading requirement data...');
        expect(wrapper.findAll('.requirement-item')).toHaveLength(1);
        resolveReload(
            requirementWith('My Checklist', [{ tileid: 't1', name: 'Step A' }]),
        );
    });
});
