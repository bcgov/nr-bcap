import type {
    AliasedNodeData,
    AliasedTileData,
} from '@/arches_component_lab/types.ts';

export interface IsTemplateRequirementTile extends AliasedTileData {
    aliased_data: {
        is_template_requirement?: AliasedNodeData;
        has_submission_requirement?: AliasedNodeData;
        default_target_processing_time?: AliasedNodeData;
    };
}

export interface RequirementIdentificationTile extends AliasedTileData {
    aliased_data: {
        requirement_name?: AliasedNodeData;
        is_template_requirement?: IsTemplateRequirementTile;
    };
}

export interface RequirementExecutionDurationTile extends AliasedTileData {
    aliased_data: {
        requirement_process_start_date: AliasedNodeData; // YYYY-MM-DD
        requirement_process_due_date: AliasedNodeData; // YYYY-MM-DD
        requirement_process_completion_date: AliasedNodeData; // YYYY-MM-DD
    };
}

export interface RequirementSubmissionTile extends AliasedTileData {
    aliased_data: {
        requirment_submission?: AliasedNodeData;
    };
}

export interface RequirementAssessmentTile extends AliasedTileData {
    aliased_data: {
        requirement_status: AliasedNodeData;
        assessment_notes: AliasedNodeData;
    };
}

export interface SubRequirementTile extends AliasedTileData {
    aliased_data: {
        // sub_requirement_reference?: AliasedNodeData;
        sub_requirement_description?: AliasedNodeData;
        sub_requirement_name?: AliasedNodeData;
        sub_requirement_assessment_notes: AliasedNodeData;
        sub_requirement_mandatory?: AliasedNodeData;
        sub_requirement_sort_order?: AliasedNodeData;
        sub_requirement_satisfied: AliasedNodeData;
    };
}

export interface PermitRequirementSchema extends AliasedTileData {
    aliased_data: {
        requirement_identification?: RequirementIdentificationTile;
        requirement_execution_duration: RequirementExecutionDurationTile;
        requirment_submission?: RequirementSubmissionTile;
        sub_requirement_assessment_n1?: RequirementAssessmentTile;
        sub_requirement?: SubRequirementTile[];
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
