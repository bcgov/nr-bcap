import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';

export interface ReportSubmissionTile extends AliasedTileData {
    aliased_data: {
        report_title?: AliasedNodeData;
        consultant_report_number?: AliasedNodeData;
        archaeological_consultant?: AliasedNodeData;
        archaological_company?: AliasedNodeData;
        report_file?: AliasedNodeData;
        report_recommendations?: AliasedNodeData;
    };
}

export interface SubmissionPhotographsTile extends AliasedTileData {
    aliased_data: {
        submission_photographs?: AliasedNodeData;
        photograph_view?: AliasedNodeData;
        photograph_date?: AliasedNodeData;
        photographer?: AliasedNodeData;
        photograph_description?: AliasedNodeData;
    };
}

export interface SubmissionAssessmentTile extends AliasedTileData {
    aliased_data: {
        arch_branch_internal_notes?: AliasedNodeData;
        arch_branch_determined_level_of_risk?: AliasedNodeData;
        arch_branch_response?: AliasedNodeData;
        arch_branch_approval_status?: AliasedNodeData; //boolean
        arch_branch_approval_date?: AliasedNodeData; //date
    };
}

export interface RequirementSubmissionProcessTile extends AliasedTileData {
    aliased_data: {
        submission_number?: AliasedNodeData;
        submission_type?: AliasedNodeData;
        report_submission?: ReportSubmissionTile;
        submission_photographs?: SubmissionPhotographsTile;
        submission_assessment?: SubmissionAssessmentTile;
    };
}

export interface RequirementSubmissionSchema extends AliasedTileData {
    aliased_data: {
        requirement_submission_process?: RequirementSubmissionProcessTile[];
    };
    graph_has_different_publication: boolean;
    name: string;
    descriptors: Record<
        string,
        { name: string; map_popup: string; description: string }
    >;
    legacyid: string;
    createdtime: string;
    graph: string;
    graph_publication: string;
    resource_instance_lifecycle_state: string;
    principaluser: string | null;
}
