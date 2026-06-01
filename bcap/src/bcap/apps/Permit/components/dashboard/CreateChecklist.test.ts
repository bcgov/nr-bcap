import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { nextTick } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';

// Route query is controlled per-test via this ref
import { ref } from 'vue';
const mockQuery = ref<Record<string, string | undefined>>({});

vi.mock('vue-router', () => ({
    useRoute: () => ({ query: mockQuery.value }),
}));

import CreateChecklist from './CreateChecklist.vue';

function mockFetchOk(body: unknown) {
    return vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(body),
    });
}

function mockFetchError() {
    return vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
    });
}

beforeEach(() => {
    mockQuery.value = {};
    vi.restoreAllMocks();
});

afterEach(() => {
    vi.unstubAllGlobals();
});

// ─── Create mode ─────────────────────────────────────────────────────────────

describe('create mode (no route id)', () => {
    it('shows "Create Process Requirement" heading', () => {
        const wrapper = mount(CreateChecklist);
        expect(wrapper.find('h2').text()).toBe('Create Process Requirement');
    });

    it('starts with one empty requirement row', () => {
        const wrapper = mount(CreateChecklist);
        expect(wrapper.findAll('.requirement-item')).toHaveLength(1);
    });

    it('does not show delete button when only one requirement', () => {
        const wrapper = mount(CreateChecklist);
        expect(wrapper.find('.btn-delete').exists()).toBe(false);
    });

    it('does not fetch on mount', () => {
        const fetchSpy = vi.fn();
        vi.stubGlobal('fetch', fetchSpy);
        mount(CreateChecklist);
        expect(fetchSpy).not.toHaveBeenCalled();
    });
});

// ─── addRequirement / removeRequirement ───────────────────────────────────────

describe('addRequirement', () => {
    it('appends a new empty requirement', async () => {
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-secondary').trigger('click');
        const items = wrapper.findAll('.requirement-item');
        expect(items).toHaveLength(2);
    });

    it('shows delete buttons once there are multiple requirements', async () => {
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-secondary').trigger('click');
        expect(wrapper.findAll('.btn-delete')).toHaveLength(2);
    });

    it('assigns incrementing sortOrder values', async () => {
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-secondary').trigger('click');
        const labels = wrapper.findAll('label[for^="name-"]');
        expect(labels[0].text()).toBe('Step 1 Title');
        expect(labels[1].text()).toBe('Step 2 Title');
    });
});

describe('removeRequirement', () => {
    it('removes the clicked requirement', async () => {
        const wrapper = mount(CreateChecklist);
        // Add a second item so the delete buttons become visible
        await wrapper.find('.btn-secondary').trigger('click');
        expect(wrapper.findAll('.requirement-item')).toHaveLength(2);
        await wrapper.findAll('.btn-delete')[0].trigger('click');
        expect(wrapper.findAll('.requirement-item')).toHaveLength(1);
    });

    it('re-numbers sortOrder after removal', async () => {
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-secondary').trigger('click');
        await wrapper.find('.btn-secondary').trigger('click');
        // Remove the first item
        await wrapper.findAll('.btn-delete')[0].trigger('click');
        const labels = wrapper.findAll('label[for^="name-"]');
        expect(labels[0].text()).toBe('Step 1 Title');
        expect(labels[1].text()).toBe('Step 2 Title');
    });
});

// ─── Drag and drop ────────────────────────────────────────────────────────────

describe('drag and drop', () => {
    it('onDrop reorders items and updates sortOrder', async () => {
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-secondary').trigger('click');

        // inputs[0] is the main title; inputs[1] and [2] are the two step names
        const inputs = wrapper.findAll<HTMLInputElement>(
            'input.req-title-input',
        );
        await inputs[1].setValue('First');
        await inputs[2].setValue('Second');

        const items = wrapper.findAll('.requirement-item');
        // Simulate dragging index 0 onto index 1
        await items[0].trigger('dragstart', {
            dataTransfer: { effectAllowed: '' },
        });
        await items[1].trigger('drop');

        const reordered = wrapper.findAll<HTMLInputElement>(
            'input.req-title-input',
        );
        // Step inputs start at index 1
        expect(reordered[1].element.value).toBe('Second');
        expect(reordered[2].element.value).toBe('First');

        const labels = wrapper.findAll('label[for^="name-"]');
        expect(labels[0].text()).toBe('Step 1 Title');
        expect(labels[1].text()).toBe('Step 2 Title');
    });

    it('onDrop is a no-op when source and target are the same index', async () => {
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-secondary').trigger('click');

        const inputs = wrapper.findAll<HTMLInputElement>(
            'input.req-title-input',
        );
        await inputs[0].setValue('Alpha');
        await inputs[1].setValue('Beta');

        const items = wrapper.findAll('.requirement-item');
        await items[0].trigger('dragstart', {
            dataTransfer: { effectAllowed: '' },
        });
        await items[0].trigger('drop');

        const after = wrapper.findAll<HTMLInputElement>(
            'input.req-title-input',
        );
        expect(after[0].element.value).toBe('Alpha');
        expect(after[1].element.value).toBe('Beta');
    });

    it('onDragEnd clears the dragging state', async () => {
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-secondary').trigger('click');

        const items = wrapper.findAll('.requirement-item');
        await items[0].trigger('dragstart', {
            dataTransfer: { effectAllowed: '' },
        });
        expect(wrapper.find('.is-dragging').exists()).toBe(true);

        await items[0].trigger('dragend');
        expect(wrapper.find('.is-dragging').exists()).toBe(false);
    });
});

// ─── Edit mode ────────────────────────────────────────────────────────────────

describe('edit mode (route id present)', () => {
    beforeEach(() => {
        mockQuery.value = { id: 'resource-abc' };
    });

    it('shows "Edit Process Requirement" heading', async () => {
        vi.stubGlobal('fetch', mockFetchOk({ displayname: '', resource: {} }));
        const wrapper = mount(CreateChecklist);
        await flushPromises();
        expect(wrapper.find('h2').text()).toBe('Edit Process Requirement');
    });

    it('fetches data from the correct URL', async () => {
        const fetchSpy = mockFetchOk({ displayname: '', resource: {} });
        vi.stubGlobal('fetch', fetchSpy);
        mount(CreateChecklist);
        await flushPromises();
        expect(fetchSpy).toHaveBeenCalledWith(
            '/bcap/resources/resource-abc?format=json',
        );
    });

    it('populates requirements from Sub Requirement with @value node values', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchOk({
                displayname: 'My Checklist',
                resource: {
                    'Sub Requirement': [
                        {
                            'Sub Requirement Name': { '@value': 'Step A' },
                            'Sub Requirement Description': { '@value': 'Do A' },
                        },
                        {
                            'Sub Requirement Name': { '@value': 'Step B' },
                            'Sub Requirement Description': { '@value': 'Do B' },
                        },
                    ],
                },
            }),
        );
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        const inputs = wrapper.findAll<HTMLInputElement>(
            'input.req-title-input',
        );
        // First input is the requirement title field; subsequent ones are step names
        const nameInputs = inputs.slice(1);
        expect(nameInputs[0].element.value).toBe('Step A');
        expect(nameInputs[1].element.value).toBe('Step B');
    });

    it('populates requirements from Sub Requirement with plain string values', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchOk({
                displayname: '',
                resource: {
                    'Sub Requirement': [
                        {
                            'Sub Requirement Name': 'Plain Name',
                            'Sub Requirement Description': 'Plain Desc',
                        },
                    ],
                },
            }),
        );
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        const inputs = wrapper.findAll<HTMLInputElement>(
            'input.req-title-input',
        );
        expect(inputs[1].element.value).toBe('Plain Name');
    });

    it('falls back to Description field when Sub Requirement Description is absent', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchOk({
                displayname: '',
                resource: {
                    'Sub Requirement': [
                        {
                            'Sub Requirement Name': { '@value': 'Step X' },
                            Description: { '@value': 'Fallback desc' },
                        },
                    ],
                },
            }),
        );
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        const textareas = wrapper.findAll<HTMLTextAreaElement>('textarea');
        expect(textareas[0].element.value).toBe('Fallback desc');
    });

    it('sets requiresSubmission when Is Template Requirement equals "True"', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchOk({
                displayname: '',
                resource: {
                    'Requirement Identification': {
                        'Is Template Requirement': 'True',
                    },
                },
            }),
        );
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        const checkbox = wrapper.find<HTMLInputElement>('#require-submission');
        expect(checkbox.element.checked).toBe(true);
    });

    it('leaves requiresSubmission false for any other value', async () => {
        vi.stubGlobal(
            'fetch',
            mockFetchOk({
                displayname: '',
                resource: {
                    'Requirement Identification': {
                        'Is Template Requirement': 'False',
                    },
                },
            }),
        );
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        const checkbox = wrapper.find<HTMLInputElement>('#require-submission');
        expect(checkbox.element.checked).toBe(false);
    });

    it('shows an error message when fetch fails', async () => {
        vi.stubGlobal('fetch', mockFetchError());
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        expect(wrapper.find('.status-state').text()).toContain(
            'Error loading existing checklist data.',
        );
    });

    it('shows an error message when fetch throws', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockRejectedValue(new Error('Network failure')),
        );
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        expect(wrapper.find('.status-state').text()).toContain(
            'Error loading existing checklist data.',
        );
    });
});

// ─── saveRequirements ─────────────────────────────────────────────────────────

describe('saveRequirements', () => {
    it('shows success message after save', async () => {
        // originalData must be set for the save payload not to throw
        mockQuery.value = { id: 'resource-abc' };
        vi.stubGlobal(
            'fetch',
            mockFetchOk({
                displayname: 'Title',
                resource: { 'Requirement Identification': {} },
            }),
        );
        const wrapper = mount(CreateChecklist);
        await flushPromises();

        await wrapper.find('.btn-primary').trigger('click');
        await flushPromises();

        expect(wrapper.find('.status-state').text()).toContain(
            'Checklist updated successfully!',
        );
    });

    it('shows error message when save throws (originalData is null)', async () => {
        // In create mode originalData stays null, so JSON.parse(JSON.stringify(null))
        // succeeds but payload.resource access throws
        const wrapper = mount(CreateChecklist);
        await wrapper.find('.btn-primary').trigger('click');
        await flushPromises();

        expect(wrapper.find('.status-state').text()).toContain(
            'Error saving checklist to backend.',
        );
    });

    it('disables Save button while loading data in edit mode', async () => {
        mockQuery.value = { id: 'resource-abc' };
        // A fetch that never resolves keeps isLoading true indefinitely
        vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})));
        const wrapper = mount(CreateChecklist);
        await nextTick(); // let onMounted set isLoading = true

        expect(
            wrapper.find<HTMLButtonElement>('.btn-primary').element.disabled,
        ).toBe(true);
    });
});
