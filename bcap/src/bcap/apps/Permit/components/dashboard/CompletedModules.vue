<script setup lang="ts">
import { computed, reactive, watch } from 'vue';
import arches from 'arches';
import Accordion from 'primevue/accordion';
import AccordionPanel from 'primevue/accordionpanel';
import AccordionHeader from 'primevue/accordionheader';
import AccordionContent from 'primevue/accordioncontent';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import {
    patchModuleOrder,
    fetchRequirementDetails,
    removeModuleAndRequirements,
    submitModule,
    reorderModuleRequirements,
    addBlankRequirement,
    removeRequirement,
} from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { useConfirmAction } from '@/bcap/apps/Permit/composables/useConfirmAction.ts';
import { useDragReorder } from '@/bcap/apps/Permit/composables/useDragReorder.ts';
import type {
    ProcessRequirement,
    PermitProcessModuleTile,
} from '@/bcap/types.ts';

const QUICK_ADD_MODULE_TYPES = ['investigation', 'alteration', 'inspection'];

const requirementType = (requirement: ProcessRequirement): string =>
    requirement.aliased_data?.requirement_identification?.aliased_data
        ?.is_template_requirement?.aliased_data?.process_requirement_type
        ?.display_value || '';

const checklistHref = (id: string): string =>
    `${arches.urls.plugin('internal-permit-dashboard')}/checklist?id=${id}`;
const editChecklistHref = (id: string): string =>
    `${arches.urls.plugin('internal-permit-dashboard')}/EditChecklist?id=${id}`;

interface AddableModule {
    id: string;
    label: string;
}

const { modules, permitId, adminTileId, isStaff, addableModules } =
    defineProps<{
        modules: PermitProcessModuleTile[];
        permitId: string;
        adminTileId: string;
        // Staff view: enables reordering (and the add/remove controls).
        isStaff?: boolean;
        // Module types a staff member can add, each routing to its workflow.
        addableModules?: AddableModule[];
    }>();

const emit = defineEmits<{
    // A module was added or removed; the parent should reload the modules.
    (event: 'changed'): void;
}>();

interface RequirementItem {
    name: string;
    resourceId: string;
    type: string;
    // Ministry assignee from the module's requirement tile (may be empty).
    ministryAssignee: string;
    // null until its status has loaded from the requirement resource.
    satisfied: boolean | null;
    // Internal (staff-only) step; null until loaded.
    internal: boolean | null;
    href: string;
}

interface ModuleRow {
    tileid: string;
    name: string;
    moduleId: string;
    completedDate: string;
    order: number;
    requirements: RequirementItem[];
}

const isChecklist = (type: string): boolean =>
    type.toLowerCase().includes('checklist');

const hrefFor = (type: string, id: string): string => {
    if (!id) return '';
    return isChecklist(type) ? checklistHref(id) : `/bcap/resource/${id}`;
};

// resourceId -> type/satisfied/internal, so rows rebuilt after a reorder keep
// their type/link/status without a fetch-driven flash.
interface RequirementMeta {
    type: string;
    satisfied: boolean;
    internal: boolean;
}
const detailCache = new Map<string, RequirementMeta>();

const requirementSatisfied = (requirement: ProcessRequirement): boolean =>
    requirement.aliased_data?.sub_requirement_assessment_n1?.aliased_data
        ?.requirement_status?.node_value === true;

const requirementInternal = (requirement: ProcessRequirement): boolean =>
    requirement.aliased_data?.requirement_identification?.aliased_data
        ?.is_template_requirement?.aliased_data?.is_internal_requirement
        ?.node_value === true;

const requirementItems = (tile: PermitProcessModuleTile): RequirementItem[] =>
    (tile.aliased_data?.process_requirement || [])
        .map((child) => ({
            order:
                child.aliased_data?.process_requirement_order?.node_value ?? 0,
            name:
                child.aliased_data?.process_requirement?.display_value ||
                'Requirement',
            resourceId:
                child.aliased_data?.process_requirement?.node_value?.[0]
                    ?.resourceId || '',
            ministryAssignee:
                child.aliased_data?.ministry_assignee?.display_value || '',
        }))
        .sort((a, b) => a.order - b.order)
        .map(({ name, resourceId, ministryAssignee }) => {
            // Seed type/status from the cache so a rebuild (e.g. after reorder)
            // doesn't flash empty while the fetch re-runs.
            const meta = detailCache.get(resourceId);
            const type = meta?.type ?? '';
            return {
                name,
                resourceId,
                type,
                ministryAssignee,
                satisfied: meta?.satisfied ?? null,
                internal: meta?.internal ?? null,
                href: hrefFor(type, resourceId),
            };
        });

const toRow = (tile: PermitProcessModuleTile): ModuleRow => {
    const order = tile.aliased_data?.module_order?.node_value ?? 0;
    return {
        tileid: tile.tileid ?? '',
        name:
            tile.aliased_data?.module_name?.display_value || 'Untitled module',
        moduleId:
            tile.aliased_data?.module_id?.display_value ||
            tile.aliased_data?.module_id?.node_value ||
            '',
        completedDate:
            tile.aliased_data?.module_completed_date?.display_value || '',
        order,
        requirements: requirementItems(tile),
    };
};

const state = reactive({
    rows: [] as ModuleRow[],
    saving: false,
});

const loadRequirementDetails = async () => {
    // Only fetch ids we haven't cached; everything else is already on the rows.
    const ids = [
        ...new Set(
            state.rows
                .flatMap((row) => row.requirements)
                .map((requirement) => requirement.resourceId)
                .filter((id) => id && !detailCache.has(id)),
        ),
    ];
    if (!ids.length) return;
    const details = await fetchRequirementDetails(ids);
    for (const [id, detail] of Object.entries(details)) {
        detailCache.set(id, {
            type: requirementType(detail),
            satisfied: requirementSatisfied(detail),
            internal: requirementInternal(detail),
        });
    }
    for (const row of state.rows) {
        for (const requirement of row.requirements) {
            const meta = detailCache.get(requirement.resourceId);
            if (meta === undefined) continue;
            requirement.type = meta.type;
            requirement.href = hrefFor(meta.type, requirement.resourceId);
            requirement.satisfied = meta.satisfied;
            requirement.internal = meta.internal;
        }
    }
};

watch(
    () => modules,
    (tiles) => {
        state.rows = (tiles || [])
            .filter((tile) => tile.tileid && tile.aliased_data?.module_name)
            .map(toRow)
            .sort((a, b) => a.order - b.order);
        loadRequirementDetails();
    },
    { immediate: true, deep: true },
);

const openStorageKey = `submitted-modules-open:${permitId}`;
const readOpenPanels = (): string[] => {
    try {
        return JSON.parse(sessionStorage.getItem(openStorageKey) || '[]');
    } catch {
        return [];
    }
};
const ui = reactive({
    openPanels: readOpenPanels(),
    // The module type currently being added (quick-add bar).
    adding: null as string | null,
    // The module tile a requirement is currently being added to.
    addingRequirement: null as string | null,
});

const dnd = useDragReorder();
const persistReqOrder = (row: ModuleRow) =>
    reorderModuleRequirements(
        permitId,
        row.tileid,
        row.requirements.map((requirement) => requirement.resourceId),
    );

const canAdd = (id: string) => QUICK_ADD_MODULE_TYPES.includes(id);

const onAddModule = async (mod: AddableModule) => {
    if (!canAdd(mod.id) || ui.adding) return;
    ui.adding = mod.id;
    try {
        // Blank host: staff fill it in afterward via the module's edit links.
        await submitModule(permitId, undefined, mod.id as GraphSlug, {});
        emit('changed');
    } catch (error) {
        console.error('Failed to add module:', error);
    } finally {
        ui.adding = null;
    }
};
watch(
    () => ui.openPanels,
    (value) => {
        sessionStorage.setItem(openStorageKey, JSON.stringify(value));
    },
);

const hasModules = computed(() => state.rows.length > 0);

// Applicants (non-staff) don't see internal-only requirements.
const visibleRequirements = (row: ModuleRow): RequirementItem[] =>
    isStaff
        ? row.requirements
        : row.requirements.filter(
              (requirement) => requirement.internal !== true,
          );

const moduleRemove = useConfirmAction<ModuleRow>(async (row) => {
    await removeModuleAndRequirements(permitId, row.tileid);
    emit('changed');
});

const onAddRequirement = async (row: ModuleRow) => {
    if (ui.addingRequirement) return;
    ui.addingRequirement = row.tileid;
    try {
        await addBlankRequirement(permitId, row.tileid);
        emit('changed');
    } catch (error) {
        console.error('Failed to add requirement:', error);
    } finally {
        ui.addingRequirement = null;
    }
};

const reqRemove = useConfirmAction<{
    row: ModuleRow;
    requirement: RequirementItem;
}>(async ({ row, requirement }) => {
    await removeRequirement(permitId, row.tileid, requirement.resourceId);
    emit('changed');
});

const persistOrder = async () => {
    // Renumber from the new positions, then persist every tile's module_order.
    const ordered = state.rows.map((row, position) => ({
        ...row,
        order: position + 1,
    }));
    state.rows = ordered;
    state.saving = true;
    try {
        await patchModuleOrder(
            permitId,
            adminTileId,
            ordered.map((row) => ({
                tileid: row.tileid,
                order: row.order,
                name: row.name,
                moduleId: row.moduleId,
            })),
        );
    } catch (error) {
        console.error('Failed to save module order:', error);
    } finally {
        state.saving = false;
    }
};
</script>

<template>
    <section
        v-if="hasModules"
        class="submitted-modules"
    >
        <div class="section-head">
            <h4 class="section-title">Submitted modules</h4>
            <span
                v-if="state.saving"
                class="saving-note"
            >
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                Saving order…
            </span>
        </div>
        <p
            v-if="isStaff"
            class="drag-hint"
        >
            Drag a module by its handle to reorder.
        </p>

        <div
            v-if="isStaff && addableModules && addableModules.length"
            class="add-module-bar"
        >
            <span class="add-module-label">Add module:</span>
            <button
                v-for="mod in addableModules"
                :key="mod.id"
                type="button"
                class="add-module-chip"
                :disabled="!canAdd(mod.id) || ui.adding !== null"
                :title="
                    canAdd(mod.id) ? `Add ${mod.label} module` : 'Coming soon'
                "
                @click="onAddModule(mod)"
            >
                <i
                    class="fa-solid"
                    :class="
                        ui.adding === mod.id
                            ? 'fa-circle-notch fa-spin'
                            : 'fa-plus'
                    "
                ></i>
                {{ mod.label }}
            </button>
        </div>

        <Accordion
            v-model:value="ui.openPanels"
            multiple
            class="modules-accordion"
        >
            <AccordionPanel
                v-for="(row, index) in state.rows"
                :key="row.tileid"
                :value="row.tileid"
                class="module-panel"
                :class="{
                    dragging: dnd.isDragging('modules', index),
                    'drag-over': dnd.isOver('modules', index),
                }"
                @dragover.prevent
                @dragenter.prevent="dnd.enter('modules', index)"
                @drop="dnd.drop('modules', index, state.rows, persistOrder)"
            >
                <AccordionHeader>
                    <span class="module-head">
                        <span
                            v-if="isStaff"
                            class="drag-handle"
                            title="Drag to reorder"
                            draggable="true"
                            @dragstart="dnd.start('modules', index)"
                            @dragend="dnd.end"
                            @click.stop
                        >
                            <i class="fa-solid fa-grip-vertical"></i>
                        </span>
                        <span class="module-name">{{ row.name }}</span>
                        <span
                            v-if="row.moduleId"
                            class="module-id"
                        >
                            - {{ row.moduleId }}
                        </span>
                        <span
                            v-if="row.completedDate"
                            class="module-date"
                        >
                            Submitted {{ row.completedDate }}
                        </span>
                        <button
                            v-if="isStaff"
                            type="button"
                            class="module-remove"
                            title="Remove module"
                            @click.stop="moduleRemove.open(row)"
                        >
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </span>
                </AccordionHeader>
                <AccordionContent>
                    <ul
                        v-if="visibleRequirements(row).length"
                        class="requirement-list"
                    >
                        <li
                            v-for="(
                                requirement, reqIndex
                            ) in visibleRequirements(row)"
                            :key="requirement.resourceId || requirement.name"
                            class="requirement-item"
                            @dragover.prevent
                            @drop="
                                dnd.drop(
                                    row.tileid,
                                    reqIndex,
                                    row.requirements,
                                    () => persistReqOrder(row),
                                )
                            "
                        >
                            <span
                                v-if="isStaff"
                                class="req-drag-handle"
                                title="Drag to reorder"
                                draggable="true"
                                @dragstart="dnd.start(row.tileid, reqIndex)"
                                @dragend="dnd.end"
                            >
                                <i class="fa-solid fa-grip-vertical"></i>
                            </span>
                            <i
                                class="status-icon"
                                :class="
                                    requirement.satisfied === null
                                        ? 'fa-regular fa-circle status-unknown'
                                        : requirement.satisfied
                                          ? 'fa-solid fa-circle-check status-ok'
                                          : 'fa-solid fa-circle-xmark status-no'
                                "
                                :title="
                                    requirement.satisfied === null
                                        ? 'Status loading'
                                        : requirement.satisfied
                                          ? 'Satisfied'
                                          : 'Not satisfied'
                                "
                            ></i>
                            <span class="requirement-name">
                                {{ requirement.name }}
                            </span>
                            <span class="req-right">
                                <span
                                    v-if="requirement.ministryAssignee"
                                    class="req-assignee"
                                    title="Ministry assignee"
                                >
                                    <i class="fa-regular fa-user"></i>
                                    {{ requirement.ministryAssignee }}
                                </span>
                                <span
                                    v-if="requirement.type"
                                    class="req-type"
                                >
                                    {{ requirement.type }}
                                </span>
                                <template
                                    v-if="isStaff && requirement.resourceId"
                                >
                                    <template
                                        v-if="isChecklist(requirement.type)"
                                    >
                                        <a
                                            class="req-action"
                                            :href="
                                                checklistHref(
                                                    requirement.resourceId,
                                                )
                                            "
                                            target="_blank"
                                            rel="noopener"
                                        >
                                            Fill out checklist
                                        </a>
                                        <a
                                            class="req-action req-action-edit"
                                            :href="
                                                editChecklistHref(
                                                    requirement.resourceId,
                                                )
                                            "
                                            target="_blank"
                                            rel="noopener"
                                        >
                                            Edit Checklist (add/remove/order
                                            subrequirements)
                                        </a>
                                    </template>
                                    <a
                                        class="req-action req-action-edit"
                                        :href="`/bcap/resource/${requirement.resourceId}`"
                                        target="_blank"
                                        rel="noopener"
                                    >
                                        View resource in Arches
                                    </a>
                                    <button
                                        type="button"
                                        class="req-remove"
                                        title="Remove requirement"
                                        @click="
                                            reqRemove.open({ row, requirement })
                                        "
                                    >
                                        <i class="fa-solid fa-trash"></i>
                                    </button>
                                </template>
                            </span>
                        </li>
                    </ul>
                    <p
                        v-else
                        class="empty-note"
                    >
                        No process requirements on this module.
                    </p>
                    <div
                        v-if="isStaff"
                        class="add-req-row"
                    >
                        <button
                            type="button"
                            class="add-req-btn"
                            :disabled="ui.addingRequirement === row.tileid"
                            @click="onAddRequirement(row)"
                        >
                            <i
                                class="fa-solid"
                                :class="
                                    ui.addingRequirement === row.tileid
                                        ? 'fa-circle-notch fa-spin'
                                        : 'fa-plus'
                                "
                            ></i>
                            Add Checklist
                        </button>
                    </div>
                </AccordionContent>
            </AccordionPanel>
        </Accordion>

        <Dialog
            v-model:visible="moduleRemove.state.visible"
            modal
            :closable="false"
            header="Remove module?"
            :style="{ width: '30rem' }"
        >
            <p>
                This removes
                <strong>
                    {{ moduleRemove.state.target?.name
                    }}{{
                        moduleRemove.state.target?.moduleId
                            ? ` - ${moduleRemove.state.target.moduleId}`
                            : ''
                    }}
                </strong>
                and its process requirements. This cannot be undone.
            </p>
            <template #footer>
                <Button
                    label="Cancel"
                    text
                    :disabled="moduleRemove.state.busy"
                    @click="moduleRemove.state.visible = false"
                />
                <Button
                    label="Remove"
                    severity="danger"
                    :loading="moduleRemove.state.busy"
                    @click="moduleRemove.confirm"
                />
            </template>
        </Dialog>

        <Dialog
            v-model:visible="reqRemove.state.visible"
            modal
            :closable="false"
            header="Remove requirement?"
            :style="{ width: '30rem' }"
        >
            <p>
                This removes
                <strong>{{ reqRemove.state.target?.requirement?.name }}</strong>
                from this module. This cannot be undone.
            </p>
            <template #footer>
                <Button
                    label="Cancel"
                    text
                    :disabled="reqRemove.state.busy"
                    @click="reqRemove.state.visible = false"
                />
                <Button
                    label="Remove"
                    severity="danger"
                    :loading="reqRemove.state.busy"
                    @click="reqRemove.confirm"
                />
            </template>
        </Dialog>
    </section>
</template>

<style scoped>
.submitted-modules {
    margin-top: 2.5rem;
    font-size: 1.05rem;
    line-height: 1.5;
    font-family: 'BC Sans', 'Noto Sans', Verdana, Arial, sans-serif;
}

/* Text inherits BC Sans from the root; Font Awesome icons keep their own font
   (a universal override here would swap the icon font and break the glyphs). */
.submitted-modules :deep(.p-accordionheader),
.submitted-modules :deep(.p-accordioncontent-content) {
    font-family: 'BC Sans', 'Noto Sans', Verdana, Arial, sans-serif;
}

/* Tint the header blue so the panel doesn't read as an all-white block. */
.submitted-modules :deep(.p-accordionheader) {
    background-color: var(--bc-selected);
    border-bottom: 1px solid var(--bc-border);
}

/* Match the draft accordion's content inset so both lists align. */
.submitted-modules :deep(.p-accordioncontent-content) {
    padding: 0.75rem 1rem;
}

.section-head {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.section-title {
    margin: 0;
    font-size: 1.35rem;
    font-weight: 700;
    color: #003366;
    letter-spacing: 0.01em;
}

.saving-note {
    font-size: 0.95rem;
    color: #2563eb;
}

.drag-hint {
    margin: 0.35rem 0 1rem;
    font-size: 0.95rem;
    color: #6b7280;
}

.add-module-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-bottom: 1rem;
}

.add-module-label {
    font-weight: 600;
    color: var(--bc-navy);
}

.add-module-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.85rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--bc-navy);
    background: var(--bc-selected);
    border: 1px solid var(--bc-border);
    border-radius: 999px;
    cursor: pointer;
    transition:
        background-color 0.15s ease,
        border-color 0.15s ease;
}

.add-module-chip:hover:not(:disabled) {
    background: #dbe6f5;
    border-color: var(--bc-navy);
}

.add-module-chip:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.modules-accordion {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    /* Space from the heading; holds on the non-staff view where the drag hint
       above is absent. */
    margin-top: 1rem;
}

.module-panel {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #ffffff;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    overflow: hidden;
    transition:
        box-shadow 0.15s ease,
        border-color 0.15s ease,
        transform 0.15s ease,
        opacity 0.15s ease;
}

.module-panel:hover {
    box-shadow: 0 4px 12px rgba(16, 24, 40, 0.08);
    border-color: #cbd5e1;
}

.module-panel.dragging {
    opacity: 0.95;
    transform: scale(1.02);
    box-shadow: 0 16px 32px rgba(16, 24, 40, 0.24);
    border-color: #93c5fd;
}

.module-panel.drag-over {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
    transform: translateY(2px);
}

.module-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding-right: 0.75rem;
}

.drag-handle {
    cursor: grab;
    color: #b0b7c3;
    padding: 0.25rem;
    border-radius: 6px;
    transition:
        color 0.15s ease,
        background-color 0.15s ease;
}

.drag-handle:hover {
    color: #475569;
    background-color: #f1f5f9;
}

.drag-handle:active {
    cursor: grabbing;
}

.module-name {
    font-weight: 600;
    font-size: 1.2rem;
    color: #111827;
}

.module-id {
    font-size: 1.2rem;
    font-weight: 600;
    color: #111827;
}

.module-date {
    margin-left: auto;
    font-size: 0.9rem;
    color: #475569;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background-color: #f1f5f9;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
}

/* When the date is absent this stays right-aligned via its own auto margin. */
.module-remove {
    margin-left: 0.5rem;
    background: none;
    border: none;
    color: #c8102e;
    cursor: pointer;
    font-size: 1rem;
    padding: 0.35rem;
    border-radius: 6px;
    transition: background-color 0.15s ease;
}

.module-remove:first-child {
    margin-left: auto;
}

.module-remove:hover {
    background-color: #fde8ea;
}

.requirement-list {
    list-style: none;
    margin: 0;
    padding: 0.25rem 0 0;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
}

.requirement-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 0.25rem;
    border-bottom: 1px solid #f1f5f9;
}

.requirement-item:last-child {
    border-bottom: none;
}

.status-icon {
    font-size: 1rem;
    flex-shrink: 0;
}

.status-ok {
    color: #16a34a;
}

.status-no {
    color: #dc2626;
}

.status-unknown {
    color: #cbd5e1;
}

.requirement-name {
    color: #111827;
    font-weight: 500;
    font-size: 1.1rem;
}

.req-right {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    white-space: nowrap;
}

.req-type {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #475569;
    background-color: #f1f5f9;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    white-space: nowrap;
}

.req-assignee {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: #475569;
    white-space: nowrap;
}

.req-action {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--bc-navy);
    text-decoration: none;
    padding: 0.25rem 0.65rem;
    border: 1px solid var(--bc-border);
    border-radius: 6px;
    background: var(--bc-selected);
    transition:
        background-color 0.15s ease,
        border-color 0.15s ease;
}

.req-action:hover {
    background: #dbe6f5;
    border-color: var(--bc-navy);
    text-decoration: none;
}

.req-action-edit {
    background: #ffffff;
}

.req-drag-handle {
    cursor: grab;
    color: #cbd5e1;
    padding: 0.15rem 0.25rem;
    border-radius: 4px;
    flex-shrink: 0;
    transition:
        color 0.15s ease,
        background-color 0.15s ease;
}

.req-drag-handle:hover {
    color: #64748b;
    background-color: #f1f5f9;
}

.req-drag-handle:active {
    cursor: grabbing;
}

.req-remove {
    background: none;
    border: none;
    color: #c8102e;
    cursor: pointer;
    font-size: 0.85rem;
    padding: 0.25rem 0.35rem;
    border-radius: 4px;
    transition: background-color 0.15s ease;
}

.req-remove:hover {
    background-color: #fde8ea;
}

.add-req-row {
    margin-top: 0.75rem;
}

.add-req-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--bc-navy);
    background: var(--bc-selected);
    border: 1px solid var(--bc-border);
    border-radius: 999px;
    padding: 0.4rem 0.85rem;
    cursor: pointer;
    transition:
        background-color 0.15s ease,
        border-color 0.15s ease;
}

.add-req-btn:hover {
    background: #dbe6f5;
    border-color: var(--bc-navy);
}

.empty-note {
    margin: 0;
    color: #6b7280;
    font-style: italic;
}
</style>
