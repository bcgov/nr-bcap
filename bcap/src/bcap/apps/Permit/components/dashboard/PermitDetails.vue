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
import {
    permitModules as permitModuleCatalogue,
    modulesForFilingType,
} from './permitModules.ts';
import QuestionDialog from './QuestionDialogExternal.vue';

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
    existingMessages: [] as Array<{
        author: string;
        text: string;
        date: string;
    }>,
    activeThreadId: null as string | null,
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

const headerMeta = computed(() =>
    [
        state.permitData.applicationNumber,
        state.permitData.submissionType,
        state.permitData.sector,
    ]
        .filter(Boolean)
        .join(' · '),
);

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

const loadInvestigations = async () => {
    const drafts = await fetchDrafts();
    state.investigationDrafts = drafts.filter(
        (d: InvestigationDraft) =>
            d.graph_slug === GraphSlug.Investigation &&
            !!d.parent_resource_id &&
            d.parent_resource_id === permitId.value,
    );
};

const loadMessages = async () => {
    if (!permitId.value) return;

    try {
        const { messages, threadId } = await getMessagesForPermit(
            permitId.value,
        );
        state.existingMessages = messages;
        state.activeThreadId = threadId;
    } catch (error) {
        console.error('Error loading messages:', error);
        state.existingMessages = [];
        state.activeThreadId = null;
    }
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
            <div class="permit-header w-full">
                <div class="permit-icon-area">
                    <i class="fa-solid fa-bolt permit-icon"></i>
                </div>

                <div class="permit-info">
                    <h2 class="project-name">
                        {{ state.permitData.projectName }}
                    </h2>
                    <p class="permit-meta">
                        {{ headerMeta }}
                        <span
                            v-if="!state.permitData.sector"
                            class="meta-unset"
                        >
                            · Sector not specified
                        </span>
                    </p>
                </div>

                <div class="submit-area">
                    <div
                        v-if="state.permitData.submittedDate"
                        class="submitted-text"
                    >
                        <i class="fa-regular fa-calendar-check"></i>
                        Submitted
                        <strong>{{ state.permitData.submittedDate }}</strong>
                    </div>
                    <button
                        v-else
                        class="print-btn"
                        @click="submitPermit"
                    >
                        Submit Permit
                    </button>

                    <QuestionDialog
                        :application-id="state.permitData.applicationNumber"
                        :permit-resource-id="permitId"
                        :existing-messages="state.existingMessages"
                        :thread-id="state.activeThreadId"
                        @message-sent="loadMessages"
                    />
                </div>
            </div>
        </template>

        <div class="module-layout">
            <div
                v-if="!isStaff"
                class="side-menu"
            >
                <button
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
                        <!-- Nothing done yet on a module that starts a new
                             workflow: the add affordance takes the same slot,
                             so one icon column runs down the menu. -->
                        <i
                            v-else-if="mod.id !== GraphSlug.PermitApplication"
                            class="fa-solid fa-plus menu-add"
                            title="Start this module"
                        ></i>
                    </div>
                </button>
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
                        </div>
                    </template>

                    <div
                        v-if="activeModule.id === GraphSlug.PermitApplication"
                        class="investigation-lists"
                    >
                        <section
                            v-if="
                                !isStaff && state.investigationDrafts.length > 0
                            "
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
                                            <i
                                                class="fa-regular fa-file-lines draft-icon"
                                            ></i>
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
                                        </span>
                                    </AccordionHeader>
                                    <AccordionContent>
                                        <div class="draft-actions">
                                            <router-link
                                                class="draft-resume"
                                                :to="{
                                                    name: routeNames.investigationModule,
                                                    query: {
                                                        draftId: draft.id,
                                                    },
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
                                                <i
                                                    class="fa-solid fa-trash"
                                                ></i>
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
                            :is-staff="isStaff"
                            :addable-modules="addableModules"
                            :summary-fields="basicInfoFields"
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

/* Header. PrimeVue wraps this in its own padded, bordered bar; that is stripped
   so the navy band runs the full width of the panel. */
.full-height :deep(.p-panel-header) {
    padding: 0;
    border: none;
    border-radius: 0;
    background: transparent;
}

.permit-header {
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
    display: flex;
    align-items: center;
    gap: 1.25rem;
    width: 100%;
    padding: 1.25rem 2rem;
    background: var(--bc-navy);
    border-bottom: 3px solid var(--bc-gold);
}

.permit-header .permit-icon-area {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-shrink: 0;
    width: 52px;
    height: 52px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.12);
}

.permit-header .permit-icon {
    font-size: 1.9rem;
    color: var(--bc-gold);
}

.permit-header .permit-info {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    flex-grow: 1;
    min-width: 0;
}

.permit-header .permit-info .project-name {
    margin: 0;
    font-size: 1.9rem;
    line-height: 1.2;
    font-weight: 700;
    color: #ffffff;
    word-break: break-word;
}

.permit-header .permit-info .permit-meta {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 400;
    color: #cbd5e1;
}

.permit-header .permit-info .meta-unset {
    color: #93a4bb;
    font-style: italic;
}

.submit-area {
    font-size: 1.15rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
}

/* An outlined pill reads on the navy; a filled one would fight the button. A
   fixed height on both keeps the pair level whatever padding each carries. */
.submitted-text,
.submit-area :deep(.trigger-btn) {
    height: 2.5rem;
}

.submitted-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0 1rem;
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 999px;
    line-height: 1.5;
    color: #ffffff;
}

.submitted-text strong {
    font-weight: 700;
}

/* The trigger is the only action on the band, so it inverts to a solid white
   button. PrimeVue ships its own font-size, hence the explicit inherit. */
.submit-area :deep(.trigger-btn) {
    font-size: inherit;
    background-color: #ffffff;
    border-color: #ffffff;
    color: var(--bc-navy);
    font-weight: 700;
}

.submit-area :deep(.trigger-btn:hover) {
    background-color: var(--bc-selected);
    border-color: var(--bc-selected);
}

/* Layout */
.module-layout {
    display: flex;
    gap: 3rem;
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
    width: 220px;
    flex-shrink: 0;
    gap: 2px;
    /* Drops the first item level with the panel heading beside it. */
    margin-top: 1.5rem;
}

.menu-item {
    background-color: #ffffff;
    color: #333333;
    border: none;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    text-align: left;
    font-size: 1.25rem;
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
    font-weight: 500;
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
    /* Long label/value rows strand on wide screens past about this width. */
    max-width: 1100px;
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
    font-size: 2.2rem;
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

/* On the navy band the same button inverts, matching the question trigger. */
.submit-area .print-btn {
    background-color: #ffffff;
    color: var(--bc-navy);
    font-weight: 700;
    font-size: inherit;
}

.submit-area .print-btn:hover {
    background-color: var(--bc-selected);
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
    font-size: 1.7rem;
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

.draft-panel {
    border: 1px solid #e5e7eb;
    border-radius: 4px;
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

/* Same navy header and gold rule as the submitted modules, so both lists read
   as one family. */
.draft-modules :deep(.p-accordionheader) {
    background-color: var(--bc-grey);
    color: #ffffff;
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
    padding: 1.35rem 1.5rem 1.35rem 2.5rem;
    border-radius: 4px 4px 0 0;
}

/* The gold rule marks which draft is expanded, matching the submitted list. */
.draft-modules :deep(.p-accordionpanel-active .p-accordionheader) {
    border-bottom: 3px solid var(--bc-gold);
}

.draft-modules :deep(.p-accordionheader) .draft-name,
.draft-modules :deep(.p-accordionheader) .draft-icon,
.draft-modules :deep(.p-accordionheader-toggle-icon) {
    color: #ffffff;
}

/* PrimeVue hard-codes 14px on the chevron svg, so override the attributes. */
.draft-modules :deep(.p-accordionheader-toggle-icon) {
    width: 1.5rem;
    height: 1.5rem;
}

/* The open panel is ringed rather than tinted, so which one is selected is
   obvious without changing the header colour. */
.draft-modules :deep(.p-accordionpanel-active .p-accordionheader) {
    outline: 2px solid var(--bc-link);
    outline-offset: -2px;
}

.draft-modules :deep(.p-accordionheader:hover) {
    background-color: #4a4a4a;
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

.draft-icon {
    margin-right: 0.35rem;
    font-size: 1.15rem;
    color: #64748b;
}

.draft-name {
    font-weight: 700;
    font-size: max(16px, 1.25rem);
    color: #111827;
}

.draft-meta {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 13px;
    color: #ffffff;
    white-space: nowrap;
    background: transparent;
    border: 1px solid #ffffff;
    padding: 0.4rem 1rem;
    border-radius: 999px;
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
