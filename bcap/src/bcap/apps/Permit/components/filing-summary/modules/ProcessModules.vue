<script setup lang="ts">
import { onMounted, computed } from 'vue';
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
import type { PermitHeader } from '@/bcap/apps/Permit/components/filing-summary/PermitHeaderBand.vue';
import { setReviewNav } from '@/bcap/apps/Permit/reviewNav.ts';
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
    type AddableModule,
    type ModuleRow,
    type RequirementItem,
} from '@/bcap/apps/Permit/components/filing-summary/modules/moduleRows.ts';

const props = defineProps<{
    modules: PermitApplicationProcessModuleTile[];
    permitId: string;
    adminTileId: string;
    isStaff?: boolean;
    addableModules?: AddableModule[];
    applicationId?: string;
    summaryFields?: ReviewField[];
    permitHeader?: PermitHeader;
}>();

const emit = defineEmits<{
    // A module was added or removed; the parent should reload the modules.
    (event: 'changed'): void;
}>();

const {
    state,
    ui,
    hasModules,
    isLoadingRequirements,
    onAddModule,
    onAddRequirement,
    onToggleCompleted,
    onToggleRequirement,
    moduleRemove,
    reqRemove,
    persistOrder,
    persistReqOrder,
} = useModuleActions({
    permitId: props.permitId,
    adminTileId: props.adminTileId,
    tiles: () => props.modules,
    onChanged: () => emit('changed'),
});

const dnd = useDragReorder();

const messageStore = useMessageStore();
onMounted(() => messageStore.loadModuleUnread(props.permitId));

const router = useRouter();
const route = useRoute();

// Optional chaining: the component is mounted without a router in tests.
const staffQuery = computed(() => route?.query?.staff ?? '');

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
    setReviewNav({
        graph,
        resourceId,
        permitId: props.permitId,
        title: row.name,
        permitHeader: props.permitHeader,
    });
    // Carry ?staff through so the review page's breadcrumb returns to the same
    // staff/external view of the permit.
    router.push({ name: routeNames.moduleReview, query: route?.query ?? {} });
};

// All requirements are shown, internal ones included.
const visibleRequirements = (row: ModuleRow): RequirementItem[] =>
    row.requirements;
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
            <Button
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
            </Button>
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
                        :toggling="ui.togglingModule"
                        @toggle="onToggleCompleted(row)"
                        @remove="moduleRemove.open(row)"
                        @dragstart="dnd.start('modules', index)"
                        @dragend="dnd.end"
                    />
                </AccordionHeader>
                <AccordionContent>
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
                                @toggle="onToggleRequirement(requirement)"
                                @remove="reqRemove.open({ row, requirement })"
                                @view-submission="
                                    onViewSubmission(row, index, requirement)
                                "
                            />
                        </li>
                    </ul>
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
                            </Button>
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
    color: var(--progress-gold);
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
