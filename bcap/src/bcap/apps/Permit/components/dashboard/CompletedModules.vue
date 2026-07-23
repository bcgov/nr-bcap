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
    setModuleCompleted,
    setRequirementSatisfied,
} from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { useConfirmAction } from '@/bcap/apps/Permit/composables/useConfirmAction.ts';
import { useDragReorder } from '@/bcap/apps/Permit/composables/useDragReorder.ts';
import ReviewSummary, {
    type ReviewField,
} from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import type {
    ProcessRequirement,
    PermitProcessModuleTile,
} from '@/bcap/types.ts';
import QuestionDialog from '@/bcap/apps/Permit/components/dashboard/QuestionDialogExternal.vue';
import type { AppThread } from '@/bcap/types.ts';

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

const {
    modules,
    permitId,
    adminTileId,
    isStaff,
    addableModules,
    applicationId,
    threads,
    summaryFields,
} = defineProps<{
    modules: PermitProcessModuleTile[];
    permitId: string;
    adminTileId: string;
    isStaff?: boolean;
    addableModules?: AddableModule[];
    applicationId?: string;
    threads?: AppThread[];
    summaryFields?: ReviewField[];
}>();

const emit = defineEmits<{
    // A module was added or removed; the parent should reload the modules.
    (event: 'changed'): void;
    // Messaging events to bubble up to the parent
    (event: 'message-sent'): void;
    (event: 'thread-resolved', threadId: string): void;
}>();

interface RequirementItem {
    name: string;
    resourceId: string;
    type: string;
    ministryAssignee: string;
    satisfied: boolean | null;
    internal: boolean | null;
    href: string;
}

interface ModuleRow {
    tileid: string;
    name: string;
    moduleId: string;
    moduleResourceId: string; // NEW: Holds the UUID of the module for the API
    completedDate: string;
    isCompleted: boolean;
    order: number;
    requirements: RequirementItem[];
}

// Status glyphs, defined once so the legend, module pills, and requirement rows
// stay in sync. The app loads only Font Awesome solid, so every class is solid.
const STATUS_ICON = {
    future: 'fa-solid fa-circle-notch',
    inProgress: 'fa-solid fa-clock',
    complete: 'fa-solid fa-check',
    unknown: 'fa-solid fa-circle-notch',
} as const;

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
    const nodeVal = tile.aliased_data?.module_id?.node_value;
    const moduleResourceId = Array.isArray(nodeVal)
        ? nodeVal[0]?.resourceId || ''
        : '';

    return {
        tileid: tile.tileid ?? '',
        name:
            tile.aliased_data?.module_name?.display_value || 'Untitled module',
        moduleId:
            tile.aliased_data?.module_id?.display_value ||
            (!Array.isArray(nodeVal) ? String(nodeVal || '') : '') ||
            '',
        moduleResourceId, // Now safely either a UUID or an empty string
        completedDate:
            tile.aliased_data?.module_completed_date?.display_value || '',
        isCompleted: Boolean(
            tile.aliased_data?.is_module_completed?.node_value,
        ),
        order,
        requirements: requirementItems(tile),
    };
};

const state = reactive({
    rows: [] as ModuleRow[],
    saving: false,
    loading: [] as string[],
});

const ui = reactive({
    openPanels: [] as string[],
    adding: null as string | null,
    addingRequirement: null as string | null,
    togglingModule: null as string | null,
    togglingRequirement: null as string | null,
});

const loadRequirementDetails = async (rows: ModuleRow[]) => {
    // Only fetch for rows with ids we haven't cached; the rest are already
    // hydrated, so they neither fetch nor show a loader.
    const rowsToLoad = rows.filter((row) =>
        row.requirements.some(
            (r) => r.resourceId && !detailCache.has(r.resourceId),
        ),
    );
    if (!rowsToLoad.length) return;
    const ids = [
        ...new Set(
            rowsToLoad
                .flatMap((row) => row.requirements)
                .map((requirement) => requirement.resourceId)
                .filter((id) => id && !detailCache.has(id)),
        ),
    ];
    const tileids = rowsToLoad.map((row) => row.tileid);
    state.loading.push(...tileids);
    try {
        const details = await fetchRequirementDetails(ids);
        for (const [id, detail] of Object.entries(details)) {
            detailCache.set(id, {
                type: requirementType(detail),
                satisfied: requirementSatisfied(detail),
                internal: requirementInternal(detail),
            });
        }
        for (const row of rowsToLoad) {
            for (const requirement of row.requirements) {
                const meta = detailCache.get(requirement.resourceId);
                if (meta === undefined) continue;
                requirement.type = meta.type;
                requirement.href = hrefFor(meta.type, requirement.resourceId);
                requirement.satisfied = meta.satisfied;
                requirement.internal = meta.internal;
            }
        }
    } finally {
        state.loading = state.loading.filter((id) => !tileids.includes(id));
    }
};

const isLoadingRequirements = (row: ModuleRow): boolean =>
    state.loading.includes(row.tileid);

// Fetch statuses only for the modules whose panels are open, so opening a permit
// doesn't chain a request for every module's requirements up front.
const loadOpenModules = (openIds: string[]) => {
    const openRows = state.rows.filter((row) => openIds.includes(row.tileid));
    if (openRows.length) loadRequirementDetails(openRows);
};

let seededDefaultOpen = false;
watch(
    () => modules,
    (tiles) => {
        state.rows = (tiles || [])
            .filter((tile) => tile.tileid && tile.aliased_data?.module_name)
            .map(toRow)
            .sort((a, b) => a.order - b.order);
        // On first load, open the top module by default; afterward the user's
        // open/closed choices stand for the life of the view.
        if (!seededDefaultOpen) {
            seededDefaultOpen = true;
            if (!ui.openPanels.length && state.rows.length) {
                ui.openPanels = [state.rows[0].tileid];
            }
        }
        loadOpenModules(ui.openPanels);
    },
    { immediate: true, deep: true },
);

const dnd = useDragReorder();
const persistReqOrder = (row: ModuleRow) =>
    reorderModuleRequirements(
        permitId,
        row.tileid,
        row.requirements.map((requirement) => requirement.resourceId),
    );

const onAddModule = async (mod: AddableModule) => {
    if (ui.adding) return;
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
        loadOpenModules(value);
    },
    { deep: true },
);

const hasModules = computed(() => state.rows.length > 0);

// All requirements are shown, internal ones included.
const visibleRequirements = (row: ModuleRow): RequirementItem[] =>
    row.requirements;

const moduleRemove = useConfirmAction<ModuleRow>(async (row) => {
    await removeModuleAndRequirements(permitId, row.tileid);
    emit('changed');
});

const onToggleCompleted = async (row: ModuleRow) => {
    if (ui.togglingModule) return;
    ui.togglingModule = row.tileid;
    try {
        await setModuleCompleted(permitId, row.tileid, !row.isCompleted);
        emit('changed');
    } catch (error) {
        console.error('Failed to change module completion:', error);
    } finally {
        ui.togglingModule = null;
    }
};

// Toggle a non-checklist requirement's satisfied status. Updates the row and
// the detail cache in place so the status icon flips without a full reload.
const onToggleRequirement = async (requirement: RequirementItem) => {
    if (ui.togglingRequirement) return;
    ui.togglingRequirement = requirement.resourceId;
    const next = !requirement.satisfied;
    try {
        await setRequirementSatisfied(requirement.resourceId, next);
        requirement.satisfied = next;
        const meta = detailCache.get(requirement.resourceId);
        if (meta) meta.satisfied = next;
    } catch (error) {
        console.error('Failed to change requirement status:', error);
    } finally {
        ui.togglingRequirement = null;
    }
};

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
            <h2 class="section-title">Submitted modules</h2>
            <span
                v-if="state.saving"
                class="saving-note"
            >
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                Saving order…
            </span>
            <span class="status-legend">
                <i :class="[STATUS_ICON.future, 'is-future']"></i>
                Future
                <i :class="[STATUS_ICON.inProgress, 'is-in-progress']"></i>
                In progress
                <i :class="[STATUS_ICON.complete, 'is-satisfied']"></i>
                Complete
            </span>
        </div>
        <div
            v-if="isStaff && addableModules && addableModules.length"
            class="add-module-bar"
        >
            <button
                v-for="mod in addableModules"
                :key="mod.id"
                type="button"
                class="add-module-chip"
                :disabled="ui.adding !== null"
                :title="`Add ${mod.label} module`"
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
                        <span class="module-title">
                            <span class="module-name">{{ row.name }}</span>
                            <span
                                v-if="row.moduleId"
                                class="module-id"
                            >
                                · {{ row.moduleId }}
                            </span>
                        </span>
                        <span
                            class="module-state-pill"
                            :class="
                                row.isCompleted
                                    ? 'state-complete'
                                    : 'state-progress'
                            "
                        >
                            <i
                                :class="
                                    row.isCompleted
                                        ? STATUS_ICON.complete
                                        : STATUS_ICON.inProgress
                                "
                            ></i>
                            {{ row.isCompleted ? 'Complete' : 'In progress' }}
                        </span>
                        <span class="module-trailing">
                            <span
                                v-if="row.completedDate"
                                class="module-date"
                            >
                                <i class="fa-regular fa-circle-check"></i>
                                Submitted {{ row.completedDate }}
                            </span>
                            <button
                                v-if="isStaff"
                                type="button"
                                class="module-toggle"
                                :class="{ 'is-satisfied': row.isCompleted }"
                                :disabled="ui.togglingModule === row.tileid"
                                :title="
                                    row.isCompleted
                                        ? 'Mark this module unsatisfied'
                                        : 'Mark this module satisfied'
                                "
                                @click.stop="onToggleCompleted(row)"
                            >
                                <i
                                    class="fa-solid"
                                    :class="
                                        ui.togglingModule === row.tileid
                                            ? 'fa-circle-notch fa-spin'
                                            : row.isCompleted
                                              ? 'fa-rotate-left'
                                              : 'fa-check'
                                    "
                                ></i>
                                {{
                                    row.isCompleted
                                        ? 'Mark unsatisfied'
                                        : 'Mark satisfied'
                                }}
                            </button>
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
                    </span>
                </AccordionHeader>
                <AccordionContent>
                    <!-- The Submission Resource (first) carries the Project
                         Summary above its requirements. -->
                    <div
                        v-if="index === 0"
                        class="module-summary"
                    >
                        <ReviewSummary :fields="summaryFields || []" />
                        <a
                            v-if="isStaff"
                            class="req-action req-action-edit submission-action"
                            :href="`/bcap/resource/${permitId}`"
                            target="_blank"
                            rel="noopener"
                        >
                            View submission in Arches
                        </a>
                    </div>
                    <p
                        v-if="isLoadingRequirements(row)"
                        class="empty-note loading-note"
                    >
                        <i class="fa-solid fa-spinner fa-spin"></i>
                        Loading requirements&hellip;
                    </p>
                    <ul
                        v-else-if="visibleRequirements(row).length"
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
                                        ? [
                                              STATUS_ICON.unknown,
                                              'status-unknown',
                                          ]
                                        : requirement.satisfied
                                          ? [STATUS_ICON.complete, 'status-ok']
                                          : [
                                                STATUS_ICON.inProgress,
                                                'status-in-progress',
                                            ]
                                "
                                :title="
                                    requirement.satisfied === null
                                        ? 'Status loading'
                                        : requirement.satisfied
                                          ? 'Satisfied'
                                          : 'In progress'
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
                                            title="Complete the checklist to satisfy this requirement"
                                        >
                                            <i
                                                class="fa-solid fa-magnifying-glass"
                                            ></i>
                                            Complete Checklist
                                        </a>
                                        <a
                                            class="req-action"
                                            :href="
                                                editChecklistHref(
                                                    requirement.resourceId,
                                                )
                                            "
                                            target="_blank"
                                            rel="noopener"
                                            title="Add, remove, or reorder subrequirements"
                                        >
                                            Edit Checklist (manager only)
                                        </a>
                                    </template>
                                    <button
                                        v-else
                                        type="button"
                                        class="req-action req-satisfy"
                                        :class="{
                                            'is-satisfied':
                                                requirement.satisfied,
                                        }"
                                        :disabled="
                                            ui.togglingRequirement ===
                                            requirement.resourceId
                                        "
                                        @click="
                                            onToggleRequirement(requirement)
                                        "
                                    >
                                        <i
                                            class="fa-solid"
                                            :class="
                                                ui.togglingRequirement ===
                                                requirement.resourceId
                                                    ? 'fa-circle-notch fa-spin'
                                                    : requirement.satisfied
                                                      ? 'fa-rotate-left'
                                                      : 'fa-check'
                                            "
                                        ></i>
                                        {{
                                            requirement.satisfied
                                                ? 'Mark unsatisfied'
                                                : 'Mark satisfied'
                                        }}
                                    </button>
                                    <a
                                        class="req-action"
                                        :href="`/bcap/resource/${requirement.resourceId}`"
                                        target="_blank"
                                        rel="noopener"
                                    >
                                        View Arches
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

                    <div class="module-footer-actions">
                        <QuestionDialog
                            v-if="applicationId && threads"
                            :application-id="applicationId"
                            :permit-resource-id="
                                row.moduleResourceId || permitId
                            "
                            :threads="threads"
                            :context="row.name"
                            @message-sent="$emit('message-sent')"
                            @thread-resolved="$emit('thread-resolved', $event)"
                        />

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
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
}

/* Text inherits BC Sans from the root; Font Awesome icons keep their own font
   (a universal override here would swap the icon font and break the glyphs). */
.submitted-modules :deep(.p-accordionheader),
.submitted-modules :deep(.p-accordioncontent-content) {
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
}

/* Pale blue header so each module reads as a distinct, airy BC Gov card. */
.submitted-modules :deep(.p-accordionheader) {
    background-color: #eef4fb;
    color: var(--bc-navy);
    padding: 1.9rem 1.5rem 1.9rem 2.5rem;
    /* Match the panel's corners so the open-state outline follows them. */
    border-radius: 10px 10px 0 0;
}

/* Name in navy, id muted grey, chevron navy, all against the pale blue bar. */
.submitted-modules :deep(.p-accordionheader) .module-name,
.submitted-modules :deep(.p-accordionheader-toggle-icon) {
    color: var(--bc-navy);
}
.submitted-modules :deep(.p-accordionheader) .module-id {
    color: var(--bc-muted);
    font-size: 1.3rem;
}
/* PrimeVue hard-codes 14px on the chevron svg, so override the attributes. */
.submitted-modules :deep(.p-accordionheader-toggle-icon) {
    width: 1.5rem;
    height: 1.5rem;
}
.submitted-modules :deep(.p-accordionheader) .drag-handle {
    color: rgba(0, 51, 102, 0.5);
}
.submitted-modules :deep(.p-accordionheader) .drag-handle:hover {
    color: var(--bc-navy);
    background-color: rgba(0, 51, 102, 0.1);
}

/* Darken on hover so the whole header reads as the click target. */
/* The open panel is ringed rather than tinted, so which one is selected is
   obvious without changing the header colour. */
.submitted-modules :deep(.p-accordionpanel-active .p-accordionheader) {
    outline: 2px solid var(--bc-link);
    outline-offset: -2px;
}

.submitted-modules :deep(.p-accordionheader:hover) {
    background-color: #e2ecf8;
}

/* Match the draft accordion's content inset so both lists align. The top inset
   matches the row gap so the first row isn't pinched against the gold rule. */
.submitted-modules :deep(.p-accordioncontent-content) {
    padding: 1.5rem 2rem 1.75rem;
}

.section-head {
    display: flex;
    align-items: center;
    gap: 1rem;
}

/* Quiet key for the two header glyphs; sits opposite the section title. */
.status-legend {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0 0 1.4rem auto;
    font-size: 1.3rem;
    color: var(--bc-muted);
}

.status-legend .is-satisfied {
    color: #16a34a;
    margin-left: 0.75rem;
}

.status-legend .is-in-progress {
    color: #7c3aed;
    margin-left: 0.75rem;
}

.status-legend .is-future {
    color: #94a3b8;
}

.section-title {
    margin: 0 0 1.4rem;
    font-size: 1.3rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--bc-grey);
}

.saving-note {
    font-size: 0.95rem;
    color: #2563eb;
}

.add-module-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-bottom: 2.5rem;
}

/* Outlined by default, filled on hover. */
.add-module-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1.2rem;
    font-size: 14px;
    font-weight: 700;
    color: #3a3f4b;
    background: #ffffff;
    border: 1px solid #3a3f4b;
    border-radius: 4px;
    cursor: pointer;
    transition:
        background-color 0.15s ease,
        color 0.15s ease;
}

.add-module-chip:hover:not(:disabled) {
    background: #3a3f4b;
    color: #ffffff;
}

.add-module-chip:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.modules-accordion {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
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

/* Name and id share a baseline as one unit, so the id lines up with the name
   however their sizes differ. The block as a whole centers in the header row. */
.module-title {
    display: inline-flex;
    align-items: baseline;
    gap: 0.5rem;
}

.module-name {
    font-weight: 700;
    font-size: max(16px, 1.25rem);
    color: #111827;
}

.module-id {
    font-size: max(16px, 1.25rem);
    font-weight: 400;
    color: #111827;
}

/* The date pill and the staff actions sit together at the row's right end. */
.module-trailing {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
}

/* Tan for in progress, green for complete: the state reads at a glance from
   the right end of the bar. */
.module-state-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin-left: 0.75rem;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    white-space: nowrap;
}

.module-state-pill.state-progress {
    background-color: #ede9fe;
    color: #7c3aed;
}

.module-state-pill.state-complete {
    background-color: #cdeed6;
    color: #15803d;
}

.module-state-pill.state-future {
    background-color: #f1f5f9;
    color: #64748b;
}

/* Matches the draft accordion's "Last updated" pill. */
.module-date {
    font-size: 13px;
    color: var(--bc-navy);
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: transparent;
    border: 1px solid var(--bc-border);
    padding: 0.4rem 1rem;
    border-radius: 999px;
}

.module-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 1rem;
    border: 1px solid var(--bc-navy);
    border-radius: 4px;
    background: transparent;
    color: var(--bc-navy);
    font: inherit;
    font-size: 13px;
    font-weight: 700;
    white-space: nowrap;
    cursor: pointer;
}

.module-toggle:hover:not(:disabled) {
    background: rgba(0, 51, 102, 0.08);
}

/* Filled navy once satisfied, so the state reads off the button as well as
   the status icon. */
.module-toggle.is-satisfied {
    background: var(--bc-navy);
    border-color: var(--bc-navy);
    color: #ffffff;
}

.module-toggle.is-satisfied:hover:not(:disabled) {
    background: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
}

/* The glyph sits inside a filled circle: gold = in progress, green = complete. */
.module-status {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    font-size: 11px;
    color: #ffffff;
    margin-right: 0.35rem;
}

.module-status.is-satisfied {
    background-color: #16a34a;
}

.module-status.is-in-progress {
    background-color: #7c3aed;
}

.module-toggle:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.module-remove {
    background: none;
    border: none;
    /* Muted until hover, where it turns BC Gov red. */
    color: rgba(0, 51, 102, 0.5);
    cursor: pointer;
    font-size: 1rem;
    padding: 0.35rem;
    border-radius: 6px;
    transition: background-color 0.15s ease;
}

.module-remove:hover {
    color: #ffffff;
    background-color: rgba(200, 16, 46, 0.85);
}

.submission-action {
    display: inline-block;
    margin-top: 1rem;
}

/* The per-row hairlines already close off the summary, so no extra rule here. */
.module-summary {
    /* Matches the module menu items on the left. */
    font-size: 1.25rem;
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
}

/* The summary is plain data, so labels and values both read as text even when
   a value happens to be a link. */
.module-summary :deep(.div-grid-cols dt) {
    color: #111827;
}

.module-summary :deep(.div-grid-cols dd),
.module-summary :deep(.div-grid-cols dd a) {
    color: #333333;
}

/* Hairline between summary rows. The grid's column gap is dropped so each
   line runs unbroken across both columns. */
.module-summary :deep(.div-grid-cols) {
    gap: 0;
}

.module-summary :deep(.div-grid-cols dt),
.module-summary :deep(.div-grid-cols dd) {
    padding: 0.9rem 1rem 0.9rem 0;
    border-bottom: 1px solid #e5e7eb;
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
    gap: 0.75rem;
    padding: 0.9rem 0.5rem;
    border-bottom: 1px solid #e5e7eb;
    border-radius: 4px;
    transition: background-color 0.12s ease;
}

.requirement-item:hover {
    background-color: #f6f9fd;
}

.status-icon {
    font-size: 13px;
    flex-shrink: 0;
}

.status-ok {
    color: #16a34a;
}

/* Violet marks the row as in progress, matching the module status glyph. */
.status-in-progress {
    color: #7c3aed;
}

.status-unknown {
    color: #cbd5e1;
}

.requirement-name {
    color: #111827;
    font-weight: 500;
    font-size: 13px;
}

.req-right {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    white-space: nowrap;
}

/* Subtle bordered chip so the type reads as an intentional tag, not a stray
   label. Fixed width keeps the actions after it (View, trash) aligned. */
.req-type {
    display: inline-block;
    min-width: 8rem;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--bc-muted);
    border: 1px solid var(--bc-border);
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    white-space: nowrap;
}

.req-assignee {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 12px;
    color: #475569;
    white-space: nowrap;
}

.req-action {
    font-size: 13px;
    font-weight: 600;
    color: var(--bc-navy);
    text-decoration: none;
    padding: 0.25rem 0.65rem;
    border: 1px solid var(--bc-border);
    border-radius: 6px;
    background: #ffffff;
    transition:
        background-color 0.15s ease,
        border-color 0.15s ease;
}

.req-action:hover {
    background: var(--bc-panel);
    border-color: var(--bc-navy);
    text-decoration: none;
}

/* A button styled as a req-action; the icon needs the shared inline spacing. */
.req-satisfy {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    cursor: pointer;
    font-family: inherit;
}

/* Filled green once satisfied so the state reads off the button as well as the
   status icon, matching the module-level toggle. */
.req-satisfy.is-satisfied {
    background: #16a34a;
    border-color: #16a34a;
    color: #ffffff;
}

.req-satisfy.is-satisfied:hover {
    background: #15803d;
    border-color: #15803d;
}

.req-satisfy:disabled {
    opacity: 0.6;
    cursor: not-allowed;
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
    font-size: 13px;
    padding: 0.25rem 0.35rem;
    border-radius: 4px;
    transition: background-color 0.15s ease;
}

.req-remove:hover {
    background-color: #fde8ea;
}

.module-footer-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1rem;
}

.add-req-row {
    margin-top: 0;
}

/* Matches the add-module chips at the top of the panel. */
.add-req-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 14px;
    font-weight: 700;
    color: #3a3f4b;
    background: #ffffff;
    border: 1px solid #3a3f4b;
    border-radius: 4px;
    padding: 0.6rem 1.2rem;
    cursor: pointer;
    transition:
        background-color 0.15s ease,
        color 0.15s ease;
}

.add-req-btn:hover {
    background: #3a3f4b;
    color: #ffffff;
}

.empty-note {
    margin: 0.85rem 0 0;
    /* Matches the module menu items on the left. */
    font-size: 14px;
    color: #6b7280;
    font-style: italic;
}
</style>
