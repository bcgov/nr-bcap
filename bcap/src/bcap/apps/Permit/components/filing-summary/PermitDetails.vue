<!-- Ideally we want to rename this to FilingSummary.vue --->
<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Panel from 'primevue/panel';
import ProgressSpinner from 'primevue/progressspinner';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import Accordion from 'primevue/accordion';
import AccordionPanel from 'primevue/accordionpanel';
import AccordionHeader from 'primevue/accordionheader';
import AccordionContent from 'primevue/accordioncontent';
import type { ReviewField } from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import CompletedModules from './CompletedModules.vue';
import PermitHeaderBand from './PermitHeaderBand.vue';
import { getBasicInfoFields } from '@/bcap/util.ts';
import type { PermitAliasedData } from '@/bcap/types.ts';
import {
    fetchPermitDetails,
    patchPermitSubmissionDate,
    fetchDrafts,
    deleteDraft,
} from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import type { InvestigationDraft } from '@/bcap/types.ts';
import {
    permitModules as permitModuleCatalogue,
    modulesForFilingType,
} from '../dashboard/permitModules.ts';
import QuestionDialog from '../common/QuestionDialogExternal.vue';
import { useMessageStore } from '@/bcap/stores/message.ts';

const messageStore = useMessageStore();

const route = useRoute();
const router = useRouter();
const permitId = computed(() => route.params.id as string);
// Staff view: enables the module reorder/add/remove controls. Set as ?staff on
// the URL when a staff member opens the permit.
// We will fix this when roles and permissions are done correctly.
const isStaff = computed(
    () => String(route.query.staff).toLowerCase() === 'true',
);

// A draft resumes into its own module's workflow, chosen by its graph slug.
const draftRouteName = (draft: InvestigationDraft): string =>
    permitModuleCatalogue.find((mod) => mod.id === draft.graph_slug)
        ?.routeName || routeNames.investigationModule;

const draftTitle = (draft: InvestigationDraft) => {
    const ident = draft.data?.investigation_identification?.aliased_data
        ?.investigation_identification as
        | { node_value?: { en?: { value?: string } }; en?: { value?: string } }
        | undefined;
    const name = ident?.node_value?.en?.value ?? ident?.en?.value;
    return name ? `Investigation - ${name}` : 'Untitled Investigation';
};

interface PermitHeaderData {
    projectName: string;
    applicationNumber: string;
    submissionType: string;
    sector: string;
    submittedDate: string | null;
}

interface ModuleResponse {
    status: 'completed' | 'review' | 'unstarted';
}

// Loaded permit view state, grouped so the async loaders update one object.
const state = reactive({
    isLoading: true,
    permitData: {
        projectName: 'Loading...',
        applicationNumber: '...',
        submissionType: '',
        sector: '...',
        submittedDate: null,
    } as PermitHeaderData,
    adminTileMeta: { tileid: '', nodegroup: '' },
    fetchedModuleData: {} as Record<string, ModuleResponse>,
    rawPermitData: null as PermitAliasedData | null,
    investigationDrafts: [] as InvestigationDraft[],
    // Completed/existing investigations have no endpoint yet; wired in later.
    completedInvestigations: [] as InvestigationDraft[],
});

const modulesAllowedForFilingType = computed(() =>
    modulesForFilingType(
        state.rawPermitData?.application_identification?.aliased_data
            ?.filing_type?.display_value ?? '',
    ),
);

const moduleFromQuery = route.query.module;
const activeModuleId = ref(
    typeof moduleFromQuery === 'string' &&
        modulesAllowedForFilingType.value.some((m) => m.id === moduleFromQuery)
        ? moduleFromQuery
        : modulesAllowedForFilingType.value[0].id,
);

watch(modulesAllowedForFilingType, (mods) => {
    if (mods.length && !mods.some((mod) => mod.id === activeModuleId.value)) {
        activeModuleId.value = mods[0].id;
    }
});

const activeModule = computed(() => {
    return modulesAllowedForFilingType.value.find(
        (m) => m.id === activeModuleId.value,
    );
});

const basicInfoFields = computed<ReviewField[]>(() => {
    return getBasicInfoFields(state.rawPermitData);
});

// The permit's process_module tiles; CompletedModules filters these to the ones
// with a submission date and renders them as a drag-reorderable accordion.
const processModules = computed(
    () =>
        state.rawPermitData?.application_admin?.aliased_data?.process_module ??
        [],
);

const getModuleStatus = (moduleId: string) => {
    return state.fetchedModuleData[moduleId]?.status || 'unstarted';
};

const loadPermitDetails = async () => {
    try {
        const aliased = await fetchPermitDetails(permitId.value);
        if (!aliased) return;

        state.rawPermitData = aliased;

        const appIdent = aliased.application_identification?.aliased_data;
        const propProj = aliased.proposed_project?.aliased_data;
        const devDetails = propProj?.development_project_details?.aliased_data;
        const appAdmin = aliased.application_admin;

        state.adminTileMeta = {
            tileid: appAdmin?.tileid || '',
            nodegroup: appAdmin?.nodegroup || '',
        };

        state.permitData = {
            projectName:
                appIdent?.project_name?.display_value || 'Unnamed Project',
            applicationNumber:
                appIdent?.application_id?.display_value || 'Pending',
            submissionType: appIdent?.filing_type?.display_value || '',
            // Left empty when unset so the header can mute it rather than
            // stating a sector that was never given.
            sector: devDetails?.industrial_sector?.display_value || '',
            submittedDate:
                appAdmin?.aliased_data?.application_submission_date
                    ?.display_value || null,
        };

        state.fetchedModuleData = {
            [GraphSlug.PermitApplication]: {
                status: appIdent?.project_name?.display_value
                    ? 'completed'
                    : 'unstarted',
            },
            // TODO fix in a bit
            inspection: {
                status: 'unstarted',
            },
            // TODO fix in a bit
            investigation: {
                status: 'unstarted',
            },
            // TODO fix in a bit
            alteration: {
                status: 'unstarted',
            },
        };
    } catch (error) {
        console.error('Failed to load permit details:', error);
        state.permitData.projectName = 'Failed to load project data';
    } finally {
        state.isLoading = false;
    }
};

const startNewModule = () => {
    if (activeModule.value?.disabled) return;
    if (activeModule.value && activeModule.value.routeName) {
        router.push({
            name: activeModule.value.routeName,
            query: { permitId: permitId.value },
        });
    }
};

// The module types a staff member can add from the submitted-modules panel,
// each routing to that module's existing workflow (Project Summary excluded).
const addableModules = computed(() =>
    permitModuleCatalogue
        .filter((mod) => mod.id !== GraphSlug.PermitApplication)
        .map((mod) => ({
            id: mod.id,
            label: mod.menuLabel,
        })),
);

const submitPermit = async () => {
    try {
        const backendDate = new Date().toISOString();
        const uiDate = new Date().toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
        });

        const adminPayload: {
            tileid?: string;
            aliased_data: { application_submission_date: string };
        } = {
            aliased_data: {
                application_submission_date: backendDate,
            },
        };

        if (state.adminTileMeta.tileid) {
            adminPayload.tileid = state.adminTileMeta.tileid;
        }

        await patchPermitSubmissionDate(permitId.value, adminPayload);

        state.permitData.submittedDate = uiDate;
        await loadPermitDetails();
    } catch (error) {
        console.error('Error submitting permit:', error);
        alert(
            'Failed to submit permit. Check the console for the Django error.',
        );
    }
};

const deleteState = reactive<{
    visible: boolean;
    busy: boolean;
    draft: InvestigationDraft | null;
}>({ visible: false, busy: false, draft: null });

const confirmDelete = (draft: InvestigationDraft) => {
    deleteState.draft = draft;
    deleteState.visible = true;
};

const performDelete = async () => {
    const draft = deleteState.draft;
    if (!draft) return;
    deleteState.busy = true;
    try {
        await deleteDraft(GraphSlug.Investigation, draft.id);
        deleteState.visible = false;
        await loadInvestigations();
    } catch (error) {
        console.error('Failed to delete draft:', error);
    } finally {
        deleteState.busy = false;
    }
};

// This needs to be more generic in the future
const loadInvestigations = async () => {
    const drafts = await fetchDrafts();
    state.investigationDrafts = drafts.filter(
        (d: InvestigationDraft) =>
            d.graph_slug === GraphSlug.Investigation &&
            !!d.parent_resource_id &&
            d.parent_resource_id === permitId.value,
    );
    // Load each draft's threads up front so its header can badge unread without
    // the dialog being opened. Drafts are few, so a fetch each is fine.
    for (const draft of state.investigationDrafts) {
        if (draft.id) messageStore.load(draft.id);
    }
};

onMounted(() => {
    loadPermitDetails();
    loadInvestigations();
});

watch(permitId, () => {
    state.isLoading = true;
    loadPermitDetails();
    loadInvestigations();
});

watch(activeModuleId, (id) => {
    if (id === GraphSlug.PermitApplication) {
        loadInvestigations();
    }
});
</script>

<template>
    <div
        v-if="state.isLoading"
        class="permit-loading"
    >
        <ProgressSpinner />
    </div>
    <Panel
        v-else
        class="full-height"
    >
        <template #header>
            <PermitHeaderBand :header="state.permitData">
                <template #actions>
                    <Button
                        class="header-submit-btn"
                        label="Submit Permit"
                        @click="submitPermit"
                    />
                </template>
            </PermitHeaderBand>
        </template>

        <div class="module-layout">
            <div
                v-if="!isStaff"
                class="side-menu"
            >
                <Button
                    v-for="mod in modulesAllowedForFilingType"
                    :key="mod.id"
                    class="menu-item"
                    :class="{ active: activeModuleId === mod.id }"
                    @click="activeModuleId = mod.id"
                >
                    <span class="menu-label">
                        {{ mod.menuLabel }}
                    </span>

                    <div class="status-icon-wrapper">
                        <i
                            v-if="getModuleStatus(mod.id) === 'completed'"
                            class="fa-solid fa-check icon-completed"
                        ></i>
                        <div
                            v-else-if="getModuleStatus(mod.id) === 'review'"
                            class="icon-review-wrapper"
                        >
                            <i
                                class="fa-solid fa-magnifying-glass icon-review"
                            ></i>
                        </div>
                        <!-- Nothing done yet on a module that starts a new
                             workflow: the add affordance takes the same slot,
                             so one icon column runs down the menu. -->
                        <i
                            v-else-if="mod.id !== GraphSlug.PermitApplication"
                            class="fa-solid fa-plus menu-add"
                            title="Start this module"
                        ></i>
                    </div>
                </Button>
            </div>

            <Transition
                name="module-swap"
                mode="out-in"
            >
                <div
                    v-if="activeModule"
                    :key="activeModule.id"
                    class="content-area"
                    :class="{
                        'white-card': ['review'].includes(
                            getModuleStatus(activeModule.id),
                        ),
                    }"
                >
                    <h1 class="content-title">{{ activeModule.title }}</h1>

                    <template
                        v-if="
                            !['completed', 'review'].includes(
                                getModuleStatus(activeModule.id),
                            )
                        "
                    >
                        <p class="content-description">
                            {{ activeModule.description }}
                        </p>

                        <ul class="content-list">
                            <li
                                v-for="(item, index) in activeModule.listItems"
                                :key="index"
                            >
                                {{ item }}
                            </li>
                        </ul>

                        <div
                            v-if="
                                activeModule.id !== GraphSlug.PermitApplication
                            "
                            class="action-container"
                        >
                            <Button
                                class="add-module-btn"
                                icon="fa-solid fa-plus"
                                :disabled="activeModule.disabled"
                                :label="
                                    activeModule.disabled
                                        ? 'Coming soon'
                                        : `Add ${activeModule.menuLabel} module`
                                "
                                @click="startNewModule"
                            />
                        </div>
                    </template>

                    <div
                        v-if="activeModule.id === GraphSlug.PermitApplication"
                        class="investigation-lists"
                    >
                        <section
                            v-if="state.investigationDrafts.length > 0"
                            class="draft-modules"
                        >
                            <h2 class="list-heading">Draft modules</h2>
                            <Accordion
                                multiple
                                class="draft-accordion"
                            >
                                <AccordionPanel
                                    v-for="draft in state.investigationDrafts"
                                    :key="draft.id"
                                    :value="draft.id"
                                    class="draft-panel"
                                >
                                    <AccordionHeader>
                                        <span class="draft-head">
                                            <span class="draft-name">
                                                {{ draftTitle(draft) }}
                                            </span>
                                            <span class="draft-meta">
                                                <i
                                                    class="fa-regular fa-clock"
                                                ></i>
                                                Last updated
                                                {{
                                                    new Date(
                                                        draft.updated ||
                                                            draft.created ||
                                                            '',
                                                    ).toLocaleDateString()
                                                }}
                                            </span>
                                            <span
                                                v-if="
                                                    messageStore.unreadCount(
                                                        draft.id,
                                                    )
                                                "
                                                class="draft-unread-badge"
                                                :title="`${messageStore.unreadCount(
                                                    draft.id,
                                                )} unread message(s)`"
                                            >
                                                <i
                                                    class="fa-solid fa-comment-dots"
                                                ></i>
                                                {{
                                                    messageStore.unreadCount(
                                                        draft.id,
                                                    )
                                                }}
                                            </span>
                                        </span>
                                    </AccordionHeader>
                                    <AccordionContent>
                                        <div class="draft-actions">
                                            <router-link
                                                class="draft-resume"
                                                :to="{
                                                    name: draftRouteName(draft),
                                                    query: {
                                                        draftId: draft.id,
                                                    },
                                                }"
                                            >
                                                <i
                                                    class="fa-solid"
                                                    :class="
                                                        isStaff
                                                            ? 'fa-eye'
                                                            : 'fa-pen'
                                                    "
                                                ></i>
                                                {{
                                                    isStaff
                                                        ? 'View draft'
                                                        : 'Resume draft'
                                                }}
                                            </router-link>
                                            <Button
                                                v-if="!isStaff"
                                                class="draft-delete"
                                                icon="fa-solid fa-trash"
                                                label="Remove"
                                                @click="confirmDelete(draft)"
                                            />
                                            <QuestionDialog
                                                :application-id="
                                                    state.permitData
                                                        .applicationNumber
                                                "
                                                :resource-id="draft.id"
                                                :context="draftTitle(draft)"
                                            />
                                        </div>
                                    </AccordionContent>
                                </AccordionPanel>
                            </Accordion>
                        </section>

                        <CompletedModules
                            :modules="processModules"
                            :permit-id="permitId"
                            :admin-tile-id="state.adminTileMeta.tileid"
                            :is-staff="isStaff"
                            :addable-modules="addableModules"
                            :summary-fields="basicInfoFields"
                            :application-id="state.permitData.applicationNumber"
                            :permit-header="state.permitData"
                            @changed="loadPermitDetails"
                        />
                    </div>
                </div>
            </Transition>
        </div>
    </Panel>

    <Dialog
        v-model:visible="deleteState.visible"
        modal
        :closable="false"
        header="Remove draft?"
        :style="{ width: '30rem' }"
    >
        <p>This permanently removes the draft. This action cannot be undone.</p>
        <template #footer>
            <Button
                label="Cancel"
                text
                :disabled="deleteState.busy"
                @click="deleteState.visible = false"
            />
            <Button
                label="Remove"
                severity="danger"
                :loading="deleteState.busy"
                @click="performDelete"
            />
        </template>
    </Dialog>
</template>

<style scoped lang="css">
.permit-loading {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60vh;
}

/* Header. PrimeVue wraps this in its own padded, bordered bar; that is stripped
   so the navy band runs the full width of the panel. */
.full-height :deep(.p-panel-header) {
    padding: 0;
    border: none;
    border-radius: 0;
    background: transparent;
}

/* The header band lives in PermitHeaderBand; only its slotted Submit button is
   styled here. */
.header-submit-btn {
    height: 3.1rem;
    padding: 0 1.5rem;
    font-size: 1.15rem;
    font-weight: 700;
    border-radius: 4px;
    background-color: #ffffff;
    border-color: #ffffff;
    color: var(--bc-navy);
    cursor: pointer;
}

.header-submit-btn:hover {
    background-color: var(--bc-selected);
    border-color: var(--bc-selected);
}

/* Layout */
.module-layout {
    display: flex;
    gap: 1.25rem;
    padding: 2rem 1.5rem;
    min-height: 500px;
}

/* Cross-fade the panel when a different module is picked. Opacity only: the
   panels differ in height, so moving them as well reads as a jump. */
.module-swap-enter-active {
    transition: opacity 0.22s ease-out;
}
.module-swap-leave-active {
    transition: opacity 0.1s ease-in;
}
.module-swap-enter-from,
.module-swap-leave-to {
    opacity: 0;
}

/* Side Menu */
.side-menu {
    display: flex;
    flex-direction: column;
    width: 260px;
    flex-shrink: 0;
    gap: 0.85rem;
    /* Drops the first item level with the panel heading beside it. */
    margin-top: 1.5rem;
}

.menu-item {
    background-color: #ffffff;
    color: #333333;
    border: none;
    border-radius: 6px;
    padding: 1.3rem 1.5rem;
    text-align: left;
    font-size: 1.45rem;
    font-weight: 400;
    cursor: pointer;
    transition:
        background-color 0.2s,
        color 0.2s;
    font-family: inherit;
    display: flex;
    gap: 0.6rem;
    align-items: center;
}

.menu-item:hover:not(.active) {
    background-color: var(--bc-selected);
    color: var(--bc-navy);
}

.menu-item.active {
    background-color: #003366;
    color: #ffffff;
    font-weight: 700;
}

/* A bare plus, lighter than the circled status glyphs it shares the column
   with, so it reads as an affordance rather than a state. */
.menu-add {
    font-size: 0.95rem;
    color: var(--bc-muted);
}

/* Grey disappears into the navy row. */
.menu-item.active .menu-add {
    color: #ffffff;
}

.menu-label {
    flex: 1;
}

/* Status Icons */
.status-icon-wrapper {
    flex: 0 0 22px;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Grey on the inactive (white) row; white on the navy active row. */
.icon-completed {
    color: var(--bc-grey);
    font-size: 1.2rem;
}

.menu-item.active .icon-completed {
    color: #ffffff;
}

.icon-review-wrapper {
    background-color: #fde047;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.icon-review {
    color: #000000;
    font-size: 0.75rem;
}

/* Content Area */
.content-area {
    flex-grow: 1;
    width: 100%;
    /* Cap only on very wide screens so long rows don't stretch edge to edge. */
    max-width: 1500px;
    padding: 1rem 2rem;
}

/* "paper" for finished modules */
.content-area.white-card {
    background-color: #ffffff;
    padding: 3rem;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.content-title {
    /* Top margin lines the heading up with the first side-menu button label.
       The heading's larger line box means its top sits above equal-offset text,
       so the offset is tuned by eye rather than summed from the paddings. */
    margin: 1.1rem 0 2rem 0;
    font-size: 2.8rem;
    font-weight: 700;
    color: #26292e;
}

/* Buttons */
.print-btn {
    background-color: #007bff;
    color: #ffffff;
    border: none;
    padding: 0.6rem 1.5rem;
    font-size: 1rem;
    font-weight: 500;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.print-btn:hover {
    background-color: #0056b3;
}

/* The in-content Print button sits directly under the review fields; give it
   room so it isn't crowding the last row. */
.content-area .print-btn {
    margin-top: 1.5rem;
}

.content-description {
    margin: 0 0 1.5rem 0;
    /* px, not rem: the root is 62%, so rem values land on fractional pixels
       and the glyphs rasterize badly. */
    font-size: 14px;
    line-height: 1.6;
    color: #333333;
}

.content-list {
    margin: 0;
    padding-left: 1.5rem;
    color: #333333;
    font-size: 14px;
    line-height: 1.6;
}

.content-list li {
    margin-bottom: 0.5rem;
}

.action-container {
    margin-top: 2.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid #d1d5db;
    display: flex;
    gap: 1rem;
}

.add-module-btn {
    background-color: #003366;
    color: #ffffff;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1.2rem;
    font-weight: 600;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.add-module-btn:hover {
    background-color: #002244;
}

.add-module-btn:disabled {
    background-color: var(--bc-muted, #6b7280);
    opacity: 0.6;
    cursor: not-allowed;
}

.investigation-lists {
    margin-top: 2.5rem;
}

/* Same group label as the submitted-modules section title. */
.investigation-lists .list-heading {
    margin: 0 0 1.4rem;
    font-size: 1.3rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--bc-grey);
}

/* Draft modules accordion */
.draft-modules {
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
}

.draft-accordion {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

/* Drafts carry the least weight on the page, so they're light white cards with
   a dashed muted border to signal "unfinished", not a solid brand-coloured bar. */
.draft-panel {
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    background: #ffffff;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    overflow: hidden;
    transition:
        box-shadow 0.15s ease,
        border-color 0.15s ease;
}

.draft-panel:hover {
    box-shadow: 0 4px 12px rgba(16, 24, 40, 0.08);
    border-color: #94a3b8;
}

.draft-modules :deep(.p-accordionheader) {
    background-color: #ffffff;
    color: #6b7280;
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
    padding: 1.9rem 1.5rem 1.9rem 2rem;
    border-radius: 10px 10px 0 0;
}

.draft-modules :deep(.p-accordionheader) .draft-name,
.draft-modules :deep(.p-accordionheader-toggle-icon) {
    color: #6b7280;
}

/* PrimeVue hard-codes 14px on the chevron svg, so override the attributes. */
.draft-modules :deep(.p-accordionheader-toggle-icon) {
    width: 1.5rem;
    height: 1.5rem;
}

.draft-modules :deep(.p-accordionpanel-active .p-accordionheader) {
    background-color: #f8fafc;
}

.draft-modules :deep(.p-accordionheader:hover) {
    background-color: #f8fafc;
}

/* Match the submitted-modules content inset so both lists align. */
.draft-modules :deep(.p-accordioncontent-content) {
    padding: 1.5rem 2rem;
}

.draft-head {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding-right: 0.75rem;
}

.draft-name {
    font-weight: 700;
    font-size: max(16px, 1.25rem);
    color: #6b7280;
}

.draft-meta {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 13px;
    color: #6b7280;
    white-space: nowrap;
}

/* Red unread pill at the far right of the draft header, by the chevron. */
.draft-unread-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.6rem;
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    background-color: #d32f2f;
    border-radius: 999px;
    white-space: nowrap;
}

.draft-actions {
    display: flex;
    gap: 1rem;
    align-items: center;
}

/* BC Gov buttons: solid navy for the primary action, outlined red to remove. */
.draft-resume,
.draft-delete {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.7rem 1.6rem;
    border-radius: 4px;
    font: inherit;
    font-size: 1.4rem;
    font-weight: 700;
    text-decoration: none;
    cursor: pointer;
}

.draft-resume {
    background: var(--bc-navy);
    border: 2px solid var(--bc-navy);
    color: #ffffff;
}

.draft-resume:hover {
    background: var(--bc-navy-dark);
    border-color: var(--bc-navy-dark);
    color: #ffffff;
    text-decoration: none;
}

.draft-delete {
    background: #ffffff;
    border: 2px solid #c8102e;
    color: #c8102e;
}

.draft-delete:hover {
    background: #fdeaed;
}

.resource-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.resource-list li {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #e5e7eb;
}

.resource-list a {
    color: #2e51dd;
    font-weight: 500;
    text-decoration: none;
}

.resource-list a:hover {
    text-decoration: underline;
}

.list-meta {
    color: #6c757d;
    font-size: 0.9rem;
    white-space: nowrap;
    margin-left: auto;
}

.remove-draft-btn {
    background: none;
    border: none;
    color: #9ca3af;
    cursor: pointer;
    padding: 0.25rem;
    font-size: 0.9rem;
    line-height: 1;
}

.remove-draft-btn:hover {
    color: #c8102e;
}

.text-muted {
    color: #6c757d;
    font-style: italic;
    padding: 0.5rem 0;
}

/* Print styling */
@media print {
    .side-menu,
    .print-btn,
    .permit-header {
        display: none !important;
    }
    .module-layout {
        padding: 0 !important;
    }
    .content-area.white-card {
        box-shadow: none !important;
        padding: 0 !important;
    }
}
</style>
