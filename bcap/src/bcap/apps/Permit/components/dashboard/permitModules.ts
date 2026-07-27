import { GraphSlug } from '@/bcap/apps/Permit/graphSlug.ts';
import { FilingType } from '@/bcap/apps/Permit/filingType.ts';

export interface PermitModule {
    id: string;
    menuLabel: string;
    title: string;
    description: string;
    listItems: string[];
    routeName: string;
    disabled: boolean;
}

const PERMIT_APPLICATION_MODULES: string[] = [
    GraphSlug.PermitApplication,
    GraphSlug.NoticeOfProjectIntent,
    GraphSlug.Investigation,
    GraphSlug.Inspection,
    GraphSlug.Alteration,
];

const MODULES_BY_FILING_TYPE: Record<FilingType, string[]> = {
    [FilingType.PermitApplicationStandard]: PERMIT_APPLICATION_MODULES,
    [FilingType.PermitApplicationEmergency]: PERMIT_APPLICATION_MODULES,
    [FilingType.PermitApplicationMultiProject]: PERMIT_APPLICATION_MODULES,
    [FilingType.ZoneAddition]: PERMIT_APPLICATION_MODULES,
    [FilingType.SiteVisit]: [GraphSlug.SiteVisit],
    [FilingType.DocumentSubmission]: [GraphSlug.DocumentSubmission],
    [FilingType.InformationRequest]: [GraphSlug.InformationRequest],
};

export const graphForModule = (name: string): string | undefined =>
    permitModules.find(
        (mod) =>
            mod.id !== GraphSlug.PermitApplication &&
            name.toLowerCase().includes(mod.menuLabel.toLowerCase()),
    )?.id;

export const modulesForFilingType = (filingType: string): PermitModule[] => {
    const ids =
        MODULES_BY_FILING_TYPE[filingType as FilingType] ??
        PERMIT_APPLICATION_MODULES;
    return permitModules.filter(
        (mod) => mod.id === GraphSlug.PermitApplication || ids.includes(mod.id),
    );
};

export const permitModules: PermitModule[] = [
    {
        id: GraphSlug.PermitApplication,
        menuLabel: 'Filing Summary',
        title: 'Filing Summary',
        description:
            'General information regarding the permit application and overall project scope.',
        listItems: ['Project Details', 'Applicant Information'],
        routeName: 'baseModule',
        disabled: false,
    },
    {
        id: GraphSlug.NoticeOfProjectIntent,
        menuLabel: 'Notice of Project Intent',
        title: 'Notice of Project Intent module',
        description:
            'Notice submitted to signal the intent to carry out a project under the permit.',
        listItems: [],
        // No route yet -- coming soon.
        routeName: '',
        disabled: true,
    },
    {
        id: GraphSlug.Investigation,
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
        id: GraphSlug.Inspection,
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
        id: GraphSlug.Alteration,
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
        id: GraphSlug.SiteVisit,
        menuLabel: 'Site Visit',
        title: 'Site Visit module',
        description:
            'Records of site visits conducted under the permit, including observations and follow-up actions.',
        listItems: [],
        // No route yet -- coming soon.
        routeName: '',
        disabled: true,
    },
    {
        id: GraphSlug.DocumentSubmission,
        menuLabel: 'Document Submission',
        title: 'Document Submission module',
        description: 'Supporting documents submitted against the permit.',
        listItems: [],
        // No route yet -- coming soon.
        routeName: '',
        disabled: true,
    },
    {
        id: GraphSlug.InformationRequest,
        menuLabel: 'Information Request',
        title: 'Information Request module',
        description:
            'A request for further information, tracking the response sent back.',
        listItems: [],
        // No route yet -- coming soon.
        routeName: '',
        disabled: true,
    },
];
