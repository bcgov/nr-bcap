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
import ReviewSummary, {
    type ReviewField,
} from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';
import CompletedModules from '@/bcap/apps/Permit/components/dashboard/CompletedModules.vue';
import { getBasicInfoFields } from '@/bcap/util.ts';
import type { PermitAliasedData } from '@/bcap/types.ts';
import {
    fetchPermitDetails,
    patchPermitSubmissionDate,
    fetchDrafts,
    deleteDraft,
    getMessagesForPermit,
} from '@/bcap/apps/Permit/api.ts';
import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import type { InvestigationDraft } from '@/bcap/types.ts';
import QuestionDialog from './QuestionDialogExternal.vue';

export interface AppMessage {
    author: string;
    text: string;
    date?: string;
}

export interface AppThread {
    id: string;
    topic: string;
    messages: AppMessage[];
    hasUnread: boolean;
    isResolved?: boolean;
}

const route = useRoute();
const router = useRouter();
const permitId = computed(() => route.params.id as string);
// Staff view: enables the module reorder/add/remove controls. Set as ?staff on
// the URL when a staff member opens the permit.
// We will fix this when roles and permissions are done correctly.
const isStaff = computed(
    () => String(route.query.staff).toLowerCase() === 'true',
);

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
        sector: '...',
        submittedDate: null,
    } as PermitHeaderData,
    adminTileMeta: { tileid: '', nodegroup: '' },
    fetchedModuleData: {} as Record<string, ModuleResponse>,
    rawPermitData: null as PermitAliasedData | null,
    investigationDrafts: [] as InvestigationDraft[],
    // Completed/existing investigations have no endpoint yet; wired in later.
    completedInvestigations: [] as InvestigationDraft[],
    threads: [] as AppThread[],
});

const permitModules = ref([
    {
        id: 'basic-info',
        menuLabel: 'Project Summary',
        title: 'Project Summary',
        description:
            'General information regarding the permit application and overall project scope.',
        listItems: ['Project Details', 'Applicant Information'],
        routeName: 'baseModule',
        disabled: false,
    },
    // To the top temporarily
    {
        id: 'investigation',
        menuLabel: 'Investigation',
        title: 'Investigation module',
        description:
            'Details regarding the planned archaeological investigation, survey areas, and expected methodology.',
        listItems: [
            'Scope of investigation (para)',
            'First Nations file number (if known)',
            'Ancestral remains anticipated (boolean)',
        ],
        routeName: 'investigationModule',
        disabled: false,
    },
    {
        id: 'inspection',
        menuLabel: 'Inspection',
        title: 'Inspection module',
        description:
            'Information regarding site inspections and monitoring requirements.',
        listItems: [
            'Development description (description of work contained in inspection module - multiple paragraphs)',
            'Assessment approach (multiple para)',
            'First Nations file number (if known)',
        ],
        routeName: 'inspectionModule',
        disabled: true,
    },
    {
        id: 'alteration',
        menuLabel: 'Alteration',
        title: 'Alteration module',
        description:
            'The alteration module is designed for any projects that include site alterations; disturbing or modifying an archaeological site for development or post-depositional alterations.',
        listItems: [
            'Field Directors (list of Contributors)',
            'Archaeologist to oversee (boolean)',
            'Oversight approach (multiple para)',
            'Is this a research permit (boolean)',
        ],
        routeName: 'alterationsModule',
        disabled: true,
    },
    {
        id: 'site-visit',
        menuLabel: 'Site Visit',
        title: 'Site Visit module',
        description:
            'Records of site visits conducted under the permit, including observations and follow-up actions.',
        listItems: [],
        // No route yet -- coming soon.
        routeName: '',
        disabled: true,
    },
]);

const moduleFromQuery = route.query.module;
const activeModuleId = ref(
    typeof moduleFromQuery === 'string' &&
        permitModules.value.some((m) => m.id === moduleFromQuery)
        ? moduleFromQuery
        : permitModules.value[0].id,
);

const activeModule = computed(() => {
    return permitModules.value.find((m) => m.id === activeModuleId.value);
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

// helper functions
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
            sector:
                devDetails?.industrial_sector?.display_value ||
                'Unknown Sector',
            submittedDate:
                appAdmin?.aliased_data?.application_submission_date
                    ?.display_value || null,
        };

        state.fetchedModuleData = {
            'basic-info': {
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
    permitModules.value
        .filter((mod) => mod.id !== 'basic-info')
        .map((mod) => ({
            id: mod.id,
            label: mod.menuLabel,
            routeName: mod.routeName,
            disabled: mod.disabled || !mod.routeName,
        })),
);

const printModule = () => {
    window.print();
};

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

const loadInvestigations = async () => {
    const drafts = await fetchDrafts();
    state.investigationDrafts = drafts.filter(
        (d: InvestigationDraft) =>
            d.graph_slug === GraphSlug.Investigation &&
            !!d.data?.parent_resource_id &&
            d.data.parent_resource_id === permitId.value,
    );
};

const loadMessages = async () => {
    if (!permitId.value) return;

    try {
        const { threads } = await getMessagesForPermit(permitId.value);
        state.threads = threads || [];

        console.log(
            'THREADS SENT TO DIALOG:',
            JSON.parse(JSON.stringify(state.threads)),
        );
    } catch (error) {
        console.error('Error loading threads:', error);
        state.threads = [];
    }
};

const handleThreadResolved = async (threadId: string) => {
    console.log(`Thread ${threadId} marked as resolved.`);
    // TODO: Add your API call here to update the thread status to resolved.
    await loadMessages();
};

onMounted(() => {
    loadPermitDetails();
    loadInvestigations();
    loadMessages();
});

watch(permitId, () => {
    state.isLoading = true;
    loadPermitDetails();
    loadInvestigations();
    loadMessages();
});

watch(activeModuleId, (id) => {
    if (id === 'basic-info') {
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
            <div class="permit-header w-full">
                <div class="permit-icon-area">
                    <i class="fa-solid fa-bolt permit-icon"></i>
                </div>

                <div class="permit-info">
                    <h2 class="project-name">
                        {{ state.permitData.projectName }}
                    </h2>
                    <p class="application-number">
                        {{ state.permitData.applicationNumber }}
                    </p>
                    <p class="sector">{{ state.permitData.sector }}</p>
                </div>

                <div class="submit-area">
                    <QuestionDialog
                        :application-id="state.permitData.applicationNumber"
                        :permit-resource-id="permitId"
                        :threads="state.threads"
                        context="Permit Application"
                        @message-sent="loadMessages"
                        @thread-resolved="handleThreadResolved"
                    />

                    <div
                        v-if="state.permitData.submittedDate"
                        class="submitted-text"
                    >
                        <strong>Submitted:</strong>
                        {{ state.permitData.submittedDate }}
                    </div>
                    <button
                        v-else
                        class="print-btn"
                        style="margin-left: 1.5rem"
                        @click="submitPermit"
                    >
                        Submit Permit
                    </button>
                </div>
            </div>
        </template>

        <div class="module-layout">
            <div
                v-if="!isStaff"
                class="side-menu"
            >
                <button
                    v-for="mod in permitModules"
                    :key="mod.id"
                    class="menu-item"
                    :class="{ active: activeModuleId === mod.id }"
                    @click="activeModuleId = mod.id"
                >
                    <span class="menu-label">{{ mod.menuLabel }}</span>

                    <div class="status-icon-wrapper">
                        <i
                            v-if="getModuleStatus(mod.id) === 'completed'"
                            class="fa-solid fa-circle-check icon-completed"
                        ></i>
                        <div
                            v-else-if="getModuleStatus(mod.id) === 'review'"
                            class="icon-review-wrapper"
                        >
                            <i
                                class="fa-solid fa-magnifying-glass icon-review"
                            ></i>
                        </div>
                    </div>
                </button>
            </div>

            <div
                v-if="activeModule"
                class="content-area"
                :class="{
                    'white-card': ['completed', 'review'].includes(
                        getModuleStatus(activeModule.id),
                    ),
                }"
            >
                <h3 class="content-title">{{ activeModule.title }}</h3>

                <template
                    v-if="
                        ['completed', 'review'].includes(
                            getModuleStatus(activeModule.id),
                        )
                    "
                >
                    <ReviewSummary
                        v-if="activeModule.id === 'basic-info'"
                        :fields="basicInfoFields"
                    />

                    <div
                        v-else
                        class="mb-4 text-gray-600 italic"
                    >
                        Summary view for {{ activeModule.menuLabel }} is under
                        construction.
                    </div>

                    <button
                        class="print-btn mt-4"
                        @click="printModule"
                    >
                        Print
                    </button>
                </template>

                <template v-else>
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
                        v-if="activeModule.id !== 'basic-info'"
                        class="action-container"
                    >
                        <button
                            class="add-module-btn"
                            :disabled="activeModule.disabled"
                            @click="startNewModule"
                        >
                            <i class="fa-solid fa-plus"></i>
                            {{
                                activeModule.disabled
                                    ? 'Coming soon'
                                    : `Add ${activeModule.menuLabel} module`
                            }}
                        </button>
                        <QuestionDialog
                            :application-id="state.permitData.applicationNumber"
                            :permit-resource-id="permitId"
                            :threads="state.threads"
                            :context="activeModule.menuLabel"
                            @message-sent="loadMessages"
                            @thread-resolved="handleThreadResolved"
                        />
                    </div>
                </template>

                <div
                    v-if="activeModule.id === 'basic-info'"
                    class="investigation-lists"
                >
                    <section
                        v-if="!isStaff && state.investigationDrafts.length > 0"
                        class="draft-modules"
                    >
                        <h4 class="list-heading">Draft modules</h4>
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
                                        <i
                                            class="fa-regular fa-file-lines draft-icon"
                                        ></i>
                                        <span class="draft-name">
                                            {{ draftTitle(draft) }}
                                        </span>
                                        <span class="draft-meta">
                                            Last updated
                                            {{
                                                new Date(
                                                    draft.updated ||
                                                        draft.created,
                                                ).toLocaleDateString()
                                            }}
                                        </span>
                                    </span>
                                </AccordionHeader>
                                <AccordionContent>
                                    <div class="draft-actions">
                                        <router-link
                                            class="draft-resume"
                                            :to="{
                                                name: routeNames.investigationModule,
                                                query: { draftId: draft.id },
                                            }"
                                        >
                                            <i class="fa-solid fa-pen"></i>
                                            Resume draft
                                        </router-link>
                                        <button
                                            type="button"
                                            class="draft-delete"
                                            @click="confirmDelete(draft)"
                                        >
                                            <i class="fa-solid fa-trash"></i>
                                            Remove
                                        </button>
                                    </div>
                                </AccordionContent>
                            </AccordionPanel>
                        </Accordion>
                    </section>

                    <CompletedModules
                        :modules="processModules"
                        :permit-id="permitId"
                        :admin-tile-id="state.adminTileMeta.tileid"
                        :submission-date="state.permitData.submittedDate"
                        :is-staff="isStaff"
                        :addable-modules="addableModules"
                        @changed="loadPermitDetails"
                    />
                </div>
            </div>
        </div>
    </Panel>

    <Dialog
        v-model:visible="deleteState.visible"
        modal
        :closable="false"
        header="Remove draft?"
        :style="{ width: '28rem' }"
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

/* Header */
.permit-header {
    font-family: 'BC Sans', 'Noto Sans', Verdana, Arial, sans-serif;
    display: flex;
    gap: 1rem;
    padding: 0.5rem;
    width: 100%;
}

.permit-header .permit-icon-area {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    flex-shrink: 0;
    width: 65px;
}

.permit-header .permit-icon {
    font-size: 3rem;
    color: #003366;
}

.permit-header .permit-info {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    flex-grow: 1;
}

.permit-header .permit-info .project-name {
    margin: 0 0 0.1rem 0;
    font-size: 1.6rem;
    line-height: 1.1;
    font-weight: 600;
    color: #2e51dd;
    word-break: break-word;
}

.permit-header .permit-info .application-number {
    margin: 0;
    font-size: 1.2rem;
    color: #333333;
    font-weight: 500;
}

.permit-header .permit-info .sector {
    margin: 0;
    font-size: 1.1rem;
    color: #777777;
}

/* New Submit Area Styles */
.submit-area {
    display: flex;
    align-items: flex-end;
    justify-content: flex-end;
    flex-shrink: 0;
    margin-right: 1.5rem;
}

.submitted-text {
    font-size: 1rem;
    color: #1f2937;
    background-color: #f3f4f6;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    border: 1px solid #d1d5db;
    margin-left: 1.5rem;
}

/* Layout */
.module-layout {
    display: flex;
    gap: 3rem;
    padding: 2rem 1.5rem;
    min-height: 500px;
}

/* Side Menu */
.side-menu {
    display: flex;
    flex-direction: column;
    width: 220px;
    flex-shrink: 0;
    gap: 2px;
}

.menu-item {
    background-color: #ffffff;
    color: #333333;
    border: none;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    text-align: left;
    font-size: 1rem;
    font-weight: 400;
    cursor: pointer;
    transition:
        background-color 0.2s,
        color 0.2s;
    font-family: inherit;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.menu-item:hover {
    background-color: #e5e7eb;
}

.menu-item.active {
    background-color: #003366;
    color: #ffffff;
    font-weight: 500;
}

/* Status Icons */
.status-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
}

.icon-completed {
    color: #22c55e;
    font-size: 1.2rem;
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
    margin: 0 0 2rem 0;
    font-size: 1.5rem;
    font-weight: 700;
    color: #000000;
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
    font-size: 1.1rem;
    line-height: 1.6;
    color: #333333;
}

.content-list {
    margin: 0;
    padding-left: 1.5rem;
    color: #333333;
    font-size: 1.1rem;
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
    font-size: 1.1rem;
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

.investigation-lists .list-heading {
    margin: 1.5rem 0 0.5rem;
    font-size: 1.35rem;
    font-weight: 700;
    color: #003366;
}

/* Draft modules accordion */
.draft-modules {
    font-family: 'BC Sans', 'Noto Sans', Verdana, Arial, sans-serif;
}

.draft-accordion {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.draft-panel {
    border: 1px solid #e5e7eb;
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
    border-color: #cbd5e1;
}

/* Tint the header blue so it reads as one family with the submitted modules. */
.draft-modules :deep(.p-accordionheader) {
    background-color: var(--bc-selected);
    border-bottom: 1px solid var(--bc-border);
    font-family: 'BC Sans', 'Noto Sans', Verdana, Arial, sans-serif;
}

/* Match the submitted-modules content inset so both lists align. */
.draft-modules :deep(.p-accordioncontent-content) {
    padding: 0.75rem 1rem;
}

.draft-head {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding-right: 0.75rem;
}

.draft-icon {
    color: #64748b;
}

.draft-name {
    font-weight: 600;
    font-size: 1.2rem;
    color: #111827;
}

.draft-meta {
    margin-left: auto;
    font-size: 0.9rem;
    color: #475569;
    white-space: nowrap;
    background-color: #f1f5f9;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
}

.draft-actions {
    display: flex;
    gap: 1.5rem;
    align-items: center;
    padding: 0.6rem 0.25rem 0.4rem;
    font-size: 1.2rem;
}

.draft-resume {
    color: var(--bc-navy);
    font-weight: 600;
    font-size: 1.2rem;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
}

.draft-resume:hover {
    text-decoration: underline;
}

.draft-delete {
    background: none;
    border: none;
    color: #c8102e;
    cursor: pointer;
    font: inherit;
    font-weight: 600;
    font-size: 1.2rem;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0;
}

.draft-delete:hover {
    text-decoration: underline;
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
