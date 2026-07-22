import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defineComponent } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';
import type { PermitProcessModuleTile } from '@/bcap/types.ts';

vi.mock('arches', () => ({
    default: {
        urls: {
            plugin: (slug: string) => `/plugins/${slug}`,
        },
    },
}));

// ReviewSummary (a child) pulls in arches-component-lab, whose tsconfig has a
// broken extends that crashes the esbuild transform. Mock the two entry points
// so those files are never loaded.
vi.mock(
    '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue',
    () => ({
        default: { name: 'GenericWidget', template: '<div />' },
    }),
);

vi.mock('@/arches_component_lab/widgets/constants.ts', () => ({
    EDIT: 'edit',
    VIEW: 'view',
}));

const api = vi.hoisted(() => ({
    patchModuleOrder: vi.fn(),
    fetchRequirementDetails: vi.fn(),
    removeModuleAndRequirements: vi.fn(),
    submitModule: vi.fn(),
    reorderModuleRequirements: vi.fn(),
    addBlankRequirement: vi.fn(),
    removeRequirement: vi.fn(),
    setModuleCompleted: vi.fn(),
    setRequirementSatisfied: vi.fn(),
}));
vi.mock('@/bcap/apps/Permit/api.ts', () => api);

import CompletedModules from './CompletedModules.vue';

// PrimeVue accordion/dialog stubs that always render their slots, so content is
// asserted without driving the real open/close behavior.
const slotStub = (name: string) =>
    defineComponent({
        name,
        template: '<div><slot></slot></div>',
    });
const stubs = {
    Accordion: slotStub('Accordion'),
    AccordionPanel: slotStub('AccordionPanel'),
    AccordionHeader: slotStub('AccordionHeader'),
    AccordionContent: slotStub('AccordionContent'),
    Dialog: slotStub('Dialog'),
    Button: slotStub('Button'),
};

// A module tile in the aliased_data shape the component reads. requirements is a
// list of [name, resourceId, order, assignee] tuples.
type Req = {
    name: string;
    resourceId: string;
    order: number;
    assignee?: string;
};
const moduleTile = (opts: {
    tileid?: string;
    name?: string;
    moduleId?: string;
    order?: number;
    completedDate?: string;
    requirements?: Req[];
}): PermitProcessModuleTile =>
    ({
        tileid: opts.tileid ?? 't1',
        aliased_data: {
            module_name: opts.name ? { display_value: opts.name } : undefined,
            module_id: opts.moduleId
                ? { display_value: opts.moduleId }
                : undefined,
            module_order: { node_value: opts.order ?? 1 },
            module_completed_date: opts.completedDate
                ? { display_value: opts.completedDate }
                : undefined,
            process_requirement: (opts.requirements ?? []).map((r) => ({
                aliased_data: {
                    process_requirement_order: { node_value: r.order },
                    process_requirement: {
                        display_value: r.name,
                        node_value: [{ resourceId: r.resourceId }],
                    },
                    ministry_assignee: r.assignee
                        ? { display_value: r.assignee }
                        : undefined,
                },
            })),
        },
    }) as unknown as PermitProcessModuleTile;

// A loaded requirement resource, in the shape the detail-fetch reads.
const requirementDetail = (opts: {
    type?: string;
    satisfied?: boolean;
    internal?: boolean;
}) => ({
    aliased_data: {
        requirement_identification: {
            aliased_data: {
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
    },
});

function mountModules(props: Record<string, unknown>) {
    return mount(CompletedModules, {
        props: {
            permitId: 'permit-1',
            adminTileId: 'admin-1',
            ...props,
        },
        global: { stubs },
    });
}

beforeEach(() => {
    Object.values(api).forEach((fn) => fn.mockReset());
    api.fetchRequirementDetails.mockResolvedValue({});
    api.submitModule.mockResolvedValue(undefined);
    api.removeModuleAndRequirements.mockResolvedValue(undefined);
    api.addBlankRequirement.mockResolvedValue(undefined);
    api.removeRequirement.mockResolvedValue(undefined);
    api.patchModuleOrder.mockResolvedValue(undefined);
    api.setModuleCompleted.mockResolvedValue(undefined);
    api.setRequirementSatisfied.mockResolvedValue(undefined);
    sessionStorage.clear();
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('CompletedModules rendering', () => {
    it('renders nothing when there are no modules', () => {
        const wrapper = mountModules({ modules: [] });
        expect(wrapper.find('.submitted-modules').exists()).toBe(false);
    });

    it('skips tiles missing a tileid or module name', () => {
        const wrapper = mountModules({
            modules: [
                moduleTile({ tileid: 'ok', name: 'Good', order: 1 }),
                moduleTile({ tileid: '', name: 'NoTile', order: 2 }),
                moduleTile({ tileid: 'x', name: undefined, order: 3 }),
            ],
        });
        expect(wrapper.findAll('.module-panel')).toHaveLength(1);
        expect(wrapper.find('.module-name').text()).toBe('Good');
    });

    it('orders modules by module_order and shows id and date', () => {
        const wrapper = mountModules({
            modules: [
                moduleTile({
                    tileid: 'b',
                    name: 'Second',
                    order: 2,
                    moduleId: 'INV-2',
                    completedDate: '2026-02-02',
                }),
                moduleTile({ tileid: 'a', name: 'First', order: 1 }),
            ],
        });
        const names = wrapper.findAll('.module-name').map((n) => n.text());
        expect(names).toEqual(['First', 'Second']);
        expect(wrapper.find('.module-id').text()).toContain('INV-2');
        expect(wrapper.text()).toContain('Submitted 2026-02-02');
    });

    it('lists requirements sorted by order', async () => {
        const wrapper = mountModules({
            modules: [
                moduleTile({
                    tileid: 'm',
                    name: 'Mod',
                    requirements: [
                        { name: 'Beta', resourceId: 'r-b', order: 2 },
                        { name: 'Alpha', resourceId: 'r-a', order: 1 },
                    ],
                }),
            ],
            // Staff so the internal-visibility filter (which hides requirements
            // until their details load) doesn't suppress the list.
            isStaff: true,
        });
        // Let the detail fetch settle so the list renders instead of the
        // loading note.
        await flushPromises();
        const names = wrapper.findAll('.requirement-name').map((n) => n.text());
        expect(names).toEqual(['Alpha', 'Beta']);
    });

    it('shows an empty note for a module with no requirements', () => {
        const wrapper = mountModules({
            modules: [moduleTile({ tileid: 'm', name: 'Mod' })],
        });
        expect(wrapper.find('.empty-note').text()).toContain(
            'No process requirements on this module',
        );
    });
});

describe('CompletedModules requirement detail loading', () => {
    it('fetches details for referenced requirements and links checklists', async () => {
        api.fetchRequirementDetails.mockResolvedValue({
            'r-1': requirementDetail({ type: 'Checklist', satisfied: true }),
        });
        const wrapper = mountModules({
            modules: [
                moduleTile({
                    tileid: 'm',
                    name: 'Mod',
                    requirements: [
                        { name: 'Req', resourceId: 'r-1', order: 1 },
                    ],
                }),
            ],
            isStaff: true,
        });
        await flushPromises();

        expect(api.fetchRequirementDetails).toHaveBeenCalledWith(['r-1']);
        expect(wrapper.find('.req-type').text()).toBe('Checklist');
        // A checklist type surfaces the fill-out link built from arches.urls.
        // Scoped to the requirement so the summary's "View submission" link
        // (also a .req-action) isn't picked up first.
        const fill = wrapper.find('.requirement-item a.req-action');
        expect(fill.attributes('href')).toBe(
            '/plugins/internal-permit-dashboard/checklist?id=r-1',
        );
        // Satisfied status renders the ok icon.
        expect(wrapper.find('.status-icon').classes()).toContain('status-ok');
    });

    it('does not fetch when no requirement has a resource id', async () => {
        mountModules({
            modules: [
                moduleTile({
                    tileid: 'm',
                    name: 'Mod',
                    requirements: [{ name: 'Req', resourceId: '', order: 1 }],
                }),
            ],
        });
        await flushPromises();
        expect(api.fetchRequirementDetails).not.toHaveBeenCalled();
    });

    it('hides internal-only requirements from applicants', async () => {
        api.fetchRequirementDetails.mockResolvedValue({
            'r-pub': requirementDetail({ internal: false }),
            'r-int': requirementDetail({ internal: true }),
        });
        const wrapper = mountModules({
            modules: [
                moduleTile({
                    tileid: 'm',
                    name: 'Mod',
                    requirements: [
                        { name: 'Public', resourceId: 'r-pub', order: 1 },
                        { name: 'Internal', resourceId: 'r-int', order: 2 },
                    ],
                }),
            ],
            isStaff: false,
        });
        await flushPromises();

        const names = wrapper.findAll('.requirement-name').map((n) => n.text());
        expect(names).toEqual(['Public']);
    });

    it('shows internal requirements to staff', async () => {
        api.fetchRequirementDetails.mockResolvedValue({
            'r-pub2': requirementDetail({ internal: false }),
            'r-int2': requirementDetail({ internal: true }),
        });
        const wrapper = mountModules({
            modules: [
                moduleTile({
                    tileid: 'm',
                    name: 'Mod',
                    requirements: [
                        { name: 'Public', resourceId: 'r-pub2', order: 1 },
                        { name: 'Internal', resourceId: 'r-int2', order: 2 },
                    ],
                }),
            ],
            isStaff: true,
        });
        await flushPromises();

        expect(wrapper.findAll('.requirement-name')).toHaveLength(2);
    });
});

describe('CompletedModules staff controls', () => {
    const staffModule = () =>
        moduleTile({
            tileid: 'm1',
            name: 'Investigation',
            moduleId: 'INV-1',
            requirements: [{ name: 'Req', resourceId: 'r-9', order: 1 }],
        });

    it('hides staff-only controls for applicants', () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: false,
        });
        expect(wrapper.find('.drag-handle').exists()).toBe(false);
        expect(wrapper.find('.module-remove').exists()).toBe(false);
        expect(wrapper.find('.add-req-btn').exists()).toBe(false);
    });

    it('renders a chip for each addable module', () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: true,
            addableModules: [
                { id: 'investigation', label: 'Investigation' },
                { id: 'permit', label: 'Permit' },
            ],
        });
        const chips = wrapper.findAll('.add-module-chip');
        expect(chips).toHaveLength(2);
        // Chips are enabled unless a submit is in flight; the parent decides
        // which modules are offered.
        expect((chips[0].element as HTMLButtonElement).disabled).toBe(false);
        expect((chips[1].element as HTMLButtonElement).disabled).toBe(false);
    });

    it('add-module submits a blank host then emits changed', async () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: true,
        });
        const vm = wrapper.vm as unknown as {
            onAddModule: (m: { id: string }) => Promise<void>;
        };

        await vm.onAddModule({ id: 'investigation' });

        expect(api.submitModule).toHaveBeenCalledWith(
            'permit-1',
            undefined,
            'investigation',
            {},
        );
        expect(wrapper.emitted('changed')).toHaveLength(1);
    });

    it('confirming module removal deletes it and emits changed', async () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: true,
        });
        const vm = wrapper.vm as unknown as {
            moduleRemove: {
                open: (row: { tileid: string }) => void;
                confirm: () => Promise<void>;
                state: { visible: boolean };
            };
        };

        vm.moduleRemove.open({ tileid: 'm1' });
        await vm.moduleRemove.confirm();

        expect(api.removeModuleAndRequirements).toHaveBeenCalledWith(
            'permit-1',
            'm1',
        );
        expect(wrapper.emitted('changed')).toHaveLength(1);
    });

    it('adding a requirement calls the api and emits changed', async () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: true,
        });
        const vm = wrapper.vm as unknown as {
            onAddRequirement: (row: { tileid: string }) => Promise<void>;
        };
        await vm.onAddRequirement({ tileid: 'm1' });
        expect(api.addBlankRequirement).toHaveBeenCalledWith('permit-1', 'm1');
        expect(wrapper.emitted('changed')).toHaveLength(1);
    });

    it('confirming requirement removal calls the api and emits changed', async () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: true,
        });
        const vm = wrapper.vm as unknown as {
            reqRemove: {
                open: (payload: unknown) => void;
                confirm: () => Promise<void>;
            };
        };
        vm.reqRemove.open({
            row: { tileid: 'm1' },
            requirement: { resourceId: 'r-9' },
        });
        await vm.reqRemove.confirm();
        expect(api.removeRequirement).toHaveBeenCalledWith(
            'permit-1',
            'm1',
            'r-9',
        );
        expect(wrapper.emitted('changed')).toHaveLength(1);
    });

    it('toggling module completion sends the flipped flag and emits changed', async () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: true,
        });
        const vm = wrapper.vm as unknown as {
            state: { rows: { tileid: string; isCompleted: boolean }[] };
            onToggleCompleted: (row: {
                tileid: string;
                isCompleted: boolean;
            }) => Promise<void>;
        };
        const row = vm.state.rows[0];
        expect(row.isCompleted).toBe(false);
        await vm.onToggleCompleted(row);

        expect(api.setModuleCompleted).toHaveBeenCalledWith(
            'permit-1',
            'm1',
            true,
        );
        expect(wrapper.emitted('changed')).toHaveLength(1);
    });

    it('toggling a requirement satisfies it and updates the row in place', async () => {
        const wrapper = mountModules({
            modules: [staffModule()],
            isStaff: true,
        });
        const vm = wrapper.vm as unknown as {
            onToggleRequirement: (r: {
                resourceId: string;
                satisfied: boolean | null;
            }) => Promise<void>;
        };
        const requirement = { resourceId: 'r-9', satisfied: false };
        await vm.onToggleRequirement(requirement);

        expect(api.setRequirementSatisfied).toHaveBeenCalledWith('r-9', true);
        // The row flips locally so the status icon updates without a reload.
        expect(requirement.satisfied).toBe(true);
    });

    it('persisting order renumbers rows and patches every tile', async () => {
        const wrapper = mountModules({
            modules: [
                moduleTile({
                    tileid: 'a',
                    name: 'A',
                    moduleId: 'A-1',
                    order: 1,
                }),
                moduleTile({
                    tileid: 'b',
                    name: 'B',
                    moduleId: 'B-1',
                    order: 2,
                }),
            ],
            isStaff: true,
        });
        const vm = wrapper.vm as unknown as {
            state: { rows: { tileid: string; order: number }[] };
            persistOrder: () => Promise<void>;
        };
        // Simulate a completed drag: B now sits before A.
        vm.state.rows = [vm.state.rows[1], vm.state.rows[0]];
        await vm.persistOrder();

        expect(api.patchModuleOrder).toHaveBeenCalledWith(
            'permit-1',
            'admin-1',
            [
                { tileid: 'b', order: 1, name: 'B', moduleId: 'B-1' },
                { tileid: 'a', order: 2, name: 'A', moduleId: 'A-1' },
            ],
        );
    });
});
