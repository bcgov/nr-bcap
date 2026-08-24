<script setup lang="ts">
import { onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Accordion from 'primevue/accordion';
import AccordionPanel from 'primevue/accordionpanel';
import AccordionHeader from 'primevue/accordionheader';
import AccordionContent from 'primevue/accordioncontent';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import { graphForModule } from '@/bcap/apps/Permit/components/dashboard/permitModules.ts';
import { usePermitHeaderStore } from '@/bcap/stores/permitHeader.ts';
import { useDragReorder } from '@/bcap/apps/Permit/composables/useDragReorder.ts';
import { useModuleActions } from '@/bcap/apps/Permit/composables/useModuleActions.ts';
import ReviewSummary, {
    type ReviewField,
} from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import type { PermitApplicationProcessModuleTile } from '@/bcap/client/types.gen.ts';
import { useMessageStore } from '@/bcap/stores/message.ts';
import ModulePanelHeader from '@/bcap/apps/Permit/components/filing-summary/modules/ModulePanelHeader.vue';
import RequirementRow from '@/bcap/apps/Permit/components/filing-summary/modules/RequirementRow.vue';
import {
    STATUS_ICON,
    type ModuleRow,
    type RequirementItem,
} from '@/bcap/apps/Permit/components/filing-summary/modules/moduleRows.ts';

const props = defineProps<{
    modules: PermitApplicationProcessModuleTile[];
    permitId: string;
    adminTileId: string;
    isStaff?: boolean;
    applicationId?: string;
    summaryFields?: ReviewField[];
}>();

const emit = defineEmits<{
    // A module was added or removed; the parent should reload the modules.
    (event: 'changed'): void;
}>();

const router = useRouter();
const route = useRoute();

// The requirement a dashboard card drilled in on, if any.
const focusRequirementId = String(route?.query?.requirement ?? '');

const {
    state,
    ui,
    hasModules,
    isLoadingRequirements,
    onAddRequirement,
    onToggleCompleted,
    onToggleRequirement,
    onAssignRequirement,
    loadAssignees,
    moduleRemove,
    reqRemove,
    persistOrder,
    persistReqOrder,
} = useModuleActions({
    permitId: props.permitId,
    adminTileId: props.adminTileId,
    tiles: () => props.modules,
    onChanged: () => emit('changed'),
    focusRequirementId,
});

const dnd = useDragReorder();

const messageStore = useMessageStore();
const headerStore = usePermitHeaderStore();
onMounted(() => {
    messageStore.loadModuleUnread(props.permitId);
    if (props.isStaff) loadAssignees();
});

// Optional chaining: the component is mounted without a router in tests.
const staffQuery = computed(() => route?.query?.staff ?? '');

// The drilled-in row only exists once its panel is open and its requirements
// have hydrated. Post-flush so the row is in the DOM, and the watcher stops
// itself once it has scrolled.
const stopFocusScroll = watch(
    () => state.rows,
    () => {
        if (!focusRequirementId) return;
        const row = document.getElementById(`req-${focusRequirementId}`);
        if (!row) return;
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        stopFocusScroll();
    },
    { deep: true, flush: 'post' },
);

// The button only shows once requirements have loaded, so the host ids are
// already populated here.
const onViewSubmission = (
    row: ModuleRow,
    index: number,
    requirement: RequirementItem,
) => {
    let graph: string = GraphSlug.PermitApplication;
    let resourceId = requirement.hostResourceId || props.permitId;
    if (index !== 0) {
        const resolved = graphForModule(row.name);
        const host = requirement.hostResourceId || row.hostResourceId;
        if (!resolved || !host) return;
        graph = resolved;
        resourceId = host;
    }
    headerStore.setReview({
        graph,
        resourceId,
        permitId: props.permitId,
        title: row.name,
    });
    // Carry ?staff through so the review page's breadcrumb returns to the same
    // staff/external view of the permit.
    router.push({ name: routeNames.moduleReview, query: route?.query ?? {} });
};

// All requirements are shown, internal ones included.
const visibleRequirements = (row: ModuleRow): RequirementItem[] =>
    row.requirements;

const archesResourceId = (row: ModuleRow, index: number): string =>
    row.hostResourceId || (index === 0 ? props.permitId : '');
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
                    <ModulePanelHeader
                        :row="row"
                        :is-staff="isStaff"
                        :resource-id="archesResourceId(row, index)"
                        :toggling="ui.togglingModule"
                        @toggle="onToggleCompleted(row)"
                        @remove="moduleRemove.open(row)"
                        @dragstart="dnd.start('modules', index)"
                        @dragend="dnd.end"
                    />
                </AccordionHeader>
                <AccordionContent>
                    <!-- Mounted only while expanded: each requirement row opens
                         a messages dialog that fetches on mount. -->
                    <template v-if="ui.openPanels.includes(row.tileid)">
                        <!-- The Submission Resource (first) carries the Project
                         Summary above its requirements. -->
                        <div
                            v-if="index === 0"
                            class="module-summary"
                        >
                            <ReviewSummary :fields="summaryFields || []" />
                        </div>
                        <p
                            v-if="isLoadingRequirements(row)"
                            class="empty-note loading-note"
                        >
                            <i class="fa-solid fa-spinner fa-spin"></i>
                            Loading requirements&hellip;
                        </p>
                        <template v-else-if="visibleRequirements(row).length">
                            <div class="requirement-head">
                                <span class="head-task">Task</span>
                                <span
                                    class="req-right"
                                    :class="{ 'is-readonly': !isStaff }"
                                >
                                    <span>Assignee</span>
                                    <span class="head-action">Task action</span>
                                </span>
                            </div>
                            <ul class="requirement-list">
                                <li
                                    v-for="(
                                        requirement, reqIndex
                                    ) in visibleRequirements(row)"
                                    :id="`req-${requirement.resourceId}`"
                                    :key="
                                        requirement.resourceId ||
                                        requirement.name
                                    "
                                    class="requirement-item"
                                    :class="{
                                        'is-focused':
                                            requirement.resourceId ===
                                            focusRequirementId,
                                    }"
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
                                        @dragstart="
                                            dnd.start(row.tileid, reqIndex)
                                        "
                                        @dragend="dnd.end"
                                    >
                                        <i
                                            class="fa-solid fa-grip-vertical"
                                        ></i>
                                    </span>
                                    <RequirementRow
                                        :requirement="requirement"
                                        :module-id="row.moduleId"
                                        :permit-id="permitId"
                                        :is-staff="isStaff"
                                        :application-id="applicationId"
                                        :staff="staffQuery"
                                        :toggling="ui.togglingRequirement"
                                        :can-view-submission="
                                            !isLoadingRequirements(row)
                                        "
                                        :assignees="state.assignees"
                                        :position="reqIndex + 1"
                                        @toggle="
                                            onToggleRequirement(requirement)
                                        "
                                        @assign="
                                            (contributorId) =>
                                                onAssignRequirement(
                                                    row,
                                                    requirement,
                                                    contributorId,
                                                )
                                        "
                                        @remove="
                                            reqRemove.open({ row, requirement })
                                        "
                                        @view-submission="
                                            onViewSubmission(
                                                row,
                                                index,
                                                requirement,
                                            )
                                        "
                                    />
                                </li>
                            </ul>
                        </template>
                        <p
                            v-else
                            class="empty-note"
                        >
                            No process requirements on this module.
                        </p>

                        <div class="module-footer-actions">
                            <div
                                v-if="isStaff"
                                class="add-req-row"
                            >
                                <Button
                                    type="button"
                                    class="add-req-btn"
                                    :disabled="
                                        ui.addingRequirement === row.tileid
                                    "
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
                                </Button>
                            </div>
                        </div>
                    </template>
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
    --progress-gold: #e3a82b;
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

/* White while collapsed; the pale blue band means "expanded". Grey here muddies
   against the page, so the card is lifted with a hairline instead of a fill. */
.submitted-modules :deep(.p-accordionheader) {
    background-color: #fff;
    border: 1px solid #e6eaef;
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
    background-color: #eef4fb;
}

.submitted-modules :deep(.p-accordionheader:hover) {
    background-color: #f4f8fd;
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
    color: var(--progress-gold);
    margin-left: 0.75rem;
}

.status-legend .is-future {
    color: #94a3b8;
}

.section-title {
    margin: 0 0 1.4rem;
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--bc-navy);
}

.module-count {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1.4rem;
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--bc-navy);
}

.saving-note {
    font-size: 0.95rem;
    color: #2563eb;
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

/* The per-row hairlines already close off the summary, so no extra rule here. */
.module-summary {
    /* Matches the module menu items on the left. */
    font-size: 1.25rem;
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid #e5e7eb;
}

/* The column strip's own edge separates it, so the summary's rule would double up. */
.module-summary:has(+ .requirement-head) {
    border-bottom: 0;
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

/* Column labels over the rows. Uses the same trailing grid as a requirement row
   (RequirementRow reads these vars), so the labels sit over their columns. */
/* Bleeds through the content padding so the strip meets the panel edges; when a
   module leads with its summary the head keeps the gap above it. */
.requirement-head {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    /* Overshoots the inset; the panel clips it, so no sliver at the edges. */
    margin-inline: -3rem;
    padding: 0.6rem 3rem;
    border-bottom: 1px solid #e5e7eb;
    background: #f8fafc;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94a3b8;
}

/* Where nothing precedes it, close the content's top inset too so the strip
   butts against the module header. */
.requirement-head:first-child {
    margin-top: -1.5rem;
}

.head-task {
    flex: 1;
    min-width: 0;
}

/* Lines up with the kebab column the rows leave room for. */
.head-action {
    padding-right: 3.5rem;
}

.requirement-head .req-right {
    margin-left: auto;
    display: grid;
    align-items: center;
    gap: 0.75rem;
    white-space: nowrap;
    grid-template-columns: minmax(0, 16rem) minmax(0, 46rem);
}

.requirement-head .req-right.is-readonly {
    grid-template-columns: minmax(0, 16rem) minmax(0, 30rem);
}

.requirement-head .head-action {
    justify-self: end;
}

.requirement-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    /* No gap: the rows are full-bleed bands, so their border is the divider. */
    gap: 0;
}

/* Every row bleeds through the content inset, so hover and the focused band are
   the same width; the extra 0.5rem of padding keeps the columns where they were. */
.requirement-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-inline: -3rem;
    padding: 0.9rem 3.5rem;
    border-bottom: 1px solid #e5e7eb;
    transition: background-color 0.12s ease;
}

.requirement-item:hover {
    background-color: #f6f9fd;
}

/* The drilled-in row reads as a flat band, marked by the navy edge rather than
   elevation. */
/* Gold, not blue: blue already means "selected" on the panels and the option
   lists, so the current row would read as one of those. Muted off --bc-gold so
   it marks the row without alarming. */
.requirement-item.is-focused {
    background-color: #fffbf0;
    border-left: 6px solid #d99e0b;
    padding-left: calc(3.5rem - 6px);
}

.requirement-item.is-focused:hover {
    background-color: #fef6e4;
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

.module-footer-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1rem;
}

.add-req-row {
    margin-top: 0;
}

/* Dashed outline so adding reads as an empty slot, not another row action. */
.add-req-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: var(--bc-navy);
    background: transparent;
    border: 1px dashed #b6c2d1;
    border-radius: 4px;
    padding: 0.7rem 1.4rem;
    cursor: pointer;
    transition:
        background-color 0.15s ease,
        border-color 0.15s ease;
}

.add-req-btn:hover {
    background: var(--bc-panel);
    border-color: var(--bc-navy);
    color: var(--bc-navy);
}

.empty-note {
    margin: 0.85rem 0 0;
    /* Matches the module menu items on the left. */
    font-size: 14px;
    color: #6b7280;
    font-style: italic;
}
</style>
