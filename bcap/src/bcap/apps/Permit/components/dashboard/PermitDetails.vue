<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Panel from 'primevue/panel';
import { z } from 'zod';
import ReviewSummary, {
    type ReviewField,
} from '@/bcap/apps/Permit/Modules/ReviewSummary.vue';

const route = useRoute();
const router = useRouter();
const permitId = ref(route.params.id);

//  Token helper
const getCookie = (name: string) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + '=') {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1),
                );
                break;
            }
        }
    }
    return cookieValue;
};

// Zod Schemas for API Validation
const ArchesNode = z
    .object({
        display_value: z.string().nullish(),
    })
    .passthrough();

const PermitPayloadSchema = z
    .object({
        aliased_data: z
            .object({
                application_identification: z
                    .object({
                        aliased_data: z
                            .object({
                                project_name: ArchesNode.nullish(),
                                application_id: ArchesNode.nullish(),
                                is_replacement: ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),

                // NEW: Added application_contacts
                application_contacts: z
                    .object({
                        aliased_data: z
                            .object({
                                application_proponent: ArchesNode.nullish(),
                                has_retained_archaeologist:
                                    ArchesNode.nullish(),
                                rationale_for_no_archaeologist:
                                    ArchesNode.nullish(),
                                application_archaeologist: ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),

                proposed_project: z
                    .object({
                        aliased_data: z
                            .object({
                                scope_of_work: ArchesNode.nullish(),
                                project_type: ArchesNode.nullish(),
                                project_description: ArchesNode.nullish(), // NEW
                                project_boundary: z.unknown().nullish(), // NEW: For the map widget
                                development_project_details: z
                                    .object({
                                        aliased_data: z
                                            .object({
                                                industrial_sector:
                                                    ArchesNode.nullish(),
                                                alteration_details:
                                                    ArchesNode.nullish(),
                                            })
                                            .passthrough()
                                            .nullish(),
                                    })
                                    .passthrough()
                                    .nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),

                archaeological_assessment_plan: z
                    .object({
                        aliased_data: z
                            .object({
                                section_1_overview: z
                                    .object({
                                        aliased_data: z
                                            .object({
                                                assessment_approach:
                                                    ArchesNode.nullish(),
                                            })
                                            .passthrough()
                                            .nullish(),
                                    })
                                    .passthrough()
                                    .nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),

                first_nation_consultation: z
                    .object({
                        aliased_data: z
                            .object({
                                fn_file_numbers: ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),

                application_admin: z
                    .object({
                        tileid: z.string().nullish(),
                        nodegroup: z.string().nullish(),
                        aliased_data: z
                            .object({
                                application_submission_date:
                                    ArchesNode.nullish(),
                            })
                            .passthrough()
                            .nullish(),
                    })
                    .passthrough()
                    .nullish(),

                inspection: z.array(z.unknown()).nullish(),
                investigation: z.array(z.unknown()).nullish(),
            })
            .passthrough()
            .nullish(),
    })
    .passthrough();

// TypeScript Interfaces for UI State
interface PermitHeaderData {
    projectName: string;
    applicationNumber: string;
    sector: string;
    submittedDate: string | null;
}

interface ModuleResponse {
    status: 'completed' | 'review' | 'unstarted';
}

// State Variables
const permitData = ref<PermitHeaderData>({
    projectName: 'Loading...',
    applicationNumber: '...',
    sector: '...',
    submittedDate: null,
});

// Holds the raw tile UUID so we can target it in the PATCH
const adminTileMeta = ref({
    tileid: '',
    nodegroup: '',
});

const fetchedModuleData = ref<Record<string, ModuleResponse>>({});

type PermitAliasedData = z.infer<typeof PermitPayloadSchema>['aliased_data'];
const rawPermitData = ref<PermitAliasedData | null>(null);

const permitModules = ref([
    {
        id: 'basic-info',
        menuLabel: 'basic info',
        title: 'Basic information',
        description:
            'General information regarding the permit application and overall project scope.',
        listItems: ['Project Details', 'Applicant Information'],
        routeName: 'baseModule',
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
    },
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
    },
]);

const activeModuleId = ref(permitModules.value[0].id);

const activeModule = computed(() => {
    return permitModules.value.find((m) => m.id === activeModuleId.value);
});

const basicInfoFields = computed<ReviewField[]>(() => {
    const aliased = rawPermitData.value;
    if (!aliased) return [];

    // Look how clean this is now! No more "as Record<string, any>"
    const ident = aliased.application_identification?.aliased_data;
    const contacts = aliased.application_contacts?.aliased_data;
    const project = aliased.proposed_project?.aliased_data;
    const devDetails = project?.development_project_details?.aliased_data;
    const archPlan =
        aliased.archaeological_assessment_plan?.aliased_data?.section_1_overview
            ?.aliased_data;
    const fnConsult = aliased.first_nation_consultation?.aliased_data;

    return [
        {
            label: 'Replacement Application',
            value: ident?.is_replacement?.display_value,
        },
        { label: 'Project Name', value: ident?.project_name?.display_value },
        {
            label: 'Application ID',
            value: ident?.application_id?.display_value,
        },
        {
            label: 'Application Proponent',
            value: contacts?.application_proponent?.display_value,
        },
        {
            label: 'Has Retained Archaeologist',
            value: contacts?.has_retained_archaeologist?.display_value,
        },
        {
            label: 'Rationale For No Archaeologist',
            value: contacts?.rationale_for_no_archaeologist?.display_value,
        },
        {
            label: 'Application Archaeologist',
            value: contacts?.application_archaeologist?.display_value,
        },
        { label: 'Project Type', value: project?.project_type?.display_value },
        {
            label: 'Project Description',
            value: project?.project_description?.display_value,
            type: 'html',
        },
        {
            label: 'Scope of Work',
            value: project?.scope_of_work?.display_value,
            type: 'html',
        },
        {
            label: 'Assessment Approach',
            value: archPlan?.assessment_approach?.display_value,
        },
        {
            label: 'First Nations File Numbers',
            value: fnConsult?.fn_file_numbers?.display_value,
        },
        {
            label: 'Industrial Sector',
            value: devDetails?.industrial_sector?.display_value,
        },
        {
            label: 'Alteration Details',
            value: devDetails?.alteration_details?.display_value,
            type: 'html',
        },
        {
            label: 'Project Boundary',
            value: project?.project_boundary,
            type: 'map',
            nodeAlias: 'project_boundary',
        },
    ];
});

// helper functions
const getModuleStatus = (moduleId: string) => {
    return fetchedModuleData.value[moduleId]?.status || 'unstarted';
};

// API fetch
const loadPermitDetails = async () => {
    try {
        const response = await fetch(
            `/bcap/api/resource/permit_application/${permitId.value}`,
            {
                method: 'GET',
                headers: { accept: 'application/json' },
            },
        );

        if (!response.ok) throw new Error('Network response was not ok');

        const rawJson = await response.json();
        const parsedData = PermitPayloadSchema.safeParse(rawJson);

        if (!parsedData.success) {
            console.error('Zod Validation Failed:', parsedData.error.format());
            throw new Error('API payload did not match expected structure');
        }

        const rawData = parsedData.data;
        const aliased = rawData.aliased_data;
        rawPermitData.value = aliased;
        const appIdent = aliased?.application_identification?.aliased_data;
        const propProj = aliased?.proposed_project?.aliased_data;
        const devDetails = propProj?.development_project_details?.aliased_data;
        const appAdmin = aliased?.application_admin;

        adminTileMeta.value = {
            tileid: appAdmin?.tileid || '',
            nodegroup: appAdmin?.nodegroup || '',
        };

        permitData.value = {
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

        fetchedModuleData.value = {
            'basic-info': {
                status: appIdent?.project_name?.display_value
                    ? 'completed'
                    : 'unstarted',
            },
            inspection: {
                status:
                    (aliased?.inspection?.length ?? 0) > 0
                        ? 'completed'
                        : 'unstarted',
            },
            investigation: {
                status:
                    (aliased?.investigation?.length ?? 0) > 0
                        ? 'completed'
                        : 'unstarted',
            },
            alteration: {
                status: 'unstarted',
            },
        };
    } catch (error) {
        console.error('Failed to load permit details:', error);
        permitData.value.projectName = 'Failed to load project data';
    }
};

const startNewModule = () => {
    if (activeModule.value && activeModule.value.routeName) {
        router.push({
            name: activeModule.value.routeName,
            query: { permitId: permitId.value },
        });
    }
};

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

        if (adminTileMeta.value.tileid) {
            adminPayload.tileid = adminTileMeta.value.tileid;
        }

        const response = await fetch(
            `/bcap/api/resource/permit_application/${permitId.value}`,
            {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    accept: 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') || '',
                },
                body: JSON.stringify({
                    aliased_data: {
                        application_admin: adminPayload,
                    },
                }),
            },
        );

        if (!response.ok) {
            const errorBody = await response.text();
            console.error('🚨 DJANGO ERROR:', errorBody);
            throw new Error(`Failed to submit permit: ${response.statusText}`);
        }

        permitData.value.submittedDate = uiDate;
        await loadPermitDetails();
    } catch (error) {
        console.error('Error submitting permit:', error);
        alert(
            'Failed to submit permit. Check the console for the Django error.',
        );
    }
};

onMounted(() => {
    loadPermitDetails();
});
</script>

<template>
    <Panel class="full-height">
        <template #header>
            <div class="permit-header w-full">
                <div class="permit-icon-area">
                    <i class="fa-solid fa-bolt permit-icon"></i>
                </div>

                <div class="permit-info">
                    <h2 class="project-name">{{ permitData.projectName }}</h2>
                    <p class="application-number">
                        {{ permitData.applicationNumber }}
                    </p>
                    <p class="sector">{{ permitData.sector }}</p>
                </div>

                <div class="submit-area">
                    <div
                        v-if="permitData.submittedDate"
                        class="submitted-text"
                    >
                        <strong>Submitted:</strong>
                        {{ permitData.submittedDate }}
                    </div>
                    <button
                        v-else
                        class="print-btn"
                        @click="submitPermit"
                    >
                        Submit Permit
                    </button>
                </div>
            </div>
        </template>

        <div class="module-layout">
            <div class="side-menu">
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
                class="content-area"
                :class="{
                    'white-card': ['completed', 'review'].includes(
                        getModuleStatus(activeModule.id),
                    ),
                }"
                v-if="activeModule"
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
                        class="action-container"
                        v-if="activeModule.id !== 'basic-info'"
                    >
                        <button
                            class="add-module-btn"
                            @click="startNewModule"
                        >
                            <i class="fa-solid fa-plus"></i>
                            Add {{ activeModule.menuLabel }} module
                        </button>
                    </div>
                </template>
            </div>
        </div>
    </Panel>
</template>

<style scoped lang="css">
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
}

.submitted-text {
    font-size: 1rem;
    color: #1f2937;
    background-color: #f3f4f6;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    border: 1px solid #d1d5db;
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
    max-width: 800px;
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
