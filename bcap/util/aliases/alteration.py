from bcap.util.bcap_aliases import AbstractAliases


class AlterationAliases(AbstractAliases):
    ADDITIONAL_COLLECTION_AND_SAMPLING_DETAILS = (
        "additional_collection_and_sampling_details"
    )
    ADDITIONAL_RECORDING_INFORMATION = "additional_recording_information"
    ADDITIONAL_REPOSITORY_AND_CURATION_COMMENTS = (
        "additional_repository_and_curation_comments"
    )
    AFFECTED_SITES = "affected_sites"
    ALTERATION_IDENTIFICATION = "alteration_identification"
    ALTERNATE_ANCESTRAL_REMAINS_APPROACH = "alternate_ancestral_remains_approach"
    ALTERNATE_CMT_APPROACH = "alternate_cmt_approach"
    ALTERNATE_EXCAVATION_APPROACH = "alternate_excavation_approach"
    ALTERNATE_HISTORICAL_SITES_APPROACH = "alternate_historical_sites_approach"
    ALTERNATE_ROCK_ART_RECORDING_APPROACH = "alternate_rock_art_recording_approach"
    ALTERNATE_SITE_FLAGGING_APPROACH = "alternate_site_flagging_approach"
    ALTERNATE_WET_SITES_APPROACH = "alternate_wet_sites_approach"
    ANCESTRAL_REMAINS_APPROACH_ADDITIONAL_COMMENTS = (
        "ancestral_remains_approach_additional_comments"
    )
    ANCESTRAL_REMAINS_APPROACH_COMPLIANT = "ancestral_remains_approach_compliant"
    ANCESTRAL_REMAINS_APPROACH_METHODS = "ancestral_remains_approach_methods"
    ARCH_BEARING_SEDIMENT = "arch_bearing_sediment"
    ARCH_POTENTIAL_APPROACH = "arch_potential_approach"
    ARCH_WORKPLANS_AND_SCHEDULE_A = "arch_workplans_and_schedule_a"
    ARE_ANCESTRAL_REMAINS_ANTICIPATED = "are_ancestral_remains_anticipated"
    ARE_CHANCE_FINDS_EXPECTED = "are_chance_finds_expected"
    ASSESSMENT_APPROACH = "assessment_approach"
    COLLECTION_APPROACH = "collection_approach"
    COLLECTION_APPROACH_ADDITIONAL_COMMENTS = "collection_approach_additional_comments"
    COLLECTION_APPROACH_DETAILS = "collection_approach_details"
    DATA_ANALYSIS_METHODS = "data_analysis_methods"
    DESTINATION_REPOSITORY = "destination_repository"
    DETAILS_OF_COLLECTED_MATERIALS = "details_of_collected_materials"
    DETAILS_OF_COLLECTED_SAMPLES = "details_of_collected_samples"
    FIELD_DIRECTORS = "field_directors"
    FIELD_TRANSPORT_AND_LAB_METHODS = "field_transport_and_lab_methods"
    HAS_ARCH_POTENTIAL = "has_arch_potential"
    HAS_CMT_SURVEY = "has_cmt_survey"
    HAS_HISTORICAL_SITES = "has_historical_sites"
    HAS_MACHINE_ASSISTED_INSPECTION = "has_machine_assisted_inspection"
    HAS_PRE_FIELD_RESEARCH = "has_pre_field_research"
    HAS_REPOSITORY_AGREEMENT = "has_repository_agreement"
    HAS_REPOSITORY_BEEN_CONTACTED = "has_repository_been_contacted"
    HAS_SITE_FLAGGING = "has_site_flagging"
    HAS_SUBSURFACE_TESTING = "has_subsurface_testing"
    HAS_SURVEY_COVERAGE = "has_survey_coverage"
    HAS_WET_SITES = "has_wet_sites"
    HAS_WINTER_ASSESSMENTS = "has_winter_assessments"
    HIP_OBJECTIVES = "hip_objectives"
    HIP_STUDY_DETAILS = "hip_study_details"
    IS_EXCAVATION_APPROACH_COMPLIANT = "is_excavation_approach_compliant"
    IS_HCA_COMPLIANT = "is_hca_compliant"
    IS_REPOSITORY_REQUIRED = "is_repository_required"
    IS_ROCK_ART_RECORDING_COMPLIANT = "is_rock_art_recording_compliant"
    MACHINE_ASSISTED_INSPECTION_APPROACH = "machine_assisted_inspection_approach"
    MACHINE_ASSISTED_INSPECTION_METHODS = "machine_assisted_inspection_methods"
    METHODS_ALIGNMENT = "methods_alignment"
    MITIGATION_MEASURES = "mitigation_measures"
    OTHER_FIELD_METHODS = "other_field_methods"
    OTHER_RECORDING_APPROACHES = "other_recording_approaches"
    OVERSEEING_ARCHAEOLOGIST = "overseeing_archaeologist"
    PERMIT_DELIVERABLES = "permit_deliverables"
    RELATED_ASSESSMENTS = "related_assessments"
    RELEVANT_ARCH_STUDIES = "relevant_arch_studies"
    SUBSURFACE_TESTING_APPROACH = "subsurface_testing_approach"
    SURVEY_COVERAGE_APPROACH = "survey_coverage_approach"
    WINTER_ASSESSMENT_METHODS = "winter_assessment_methods"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(AlterationAliases)


class AlterationGroupAliases(AbstractAliases):
    MATERIAL_COLLECTION = "material_collection"
    METHODOLOGY = "methodology"
    RECORDINGS = "recordings"
    SECTION_1_OVERVIEW = "section_1_overview"
    SECTION_2_PERSONNEL = "section_2_personnel"
    SECTION_6_ANCESTRAL_REMAINS = "section_6_ancestral_remains"
    SECTION_7_REPOSITORY_AND_CURATION = "section_7_repository_and_curation"

    @staticmethod
    def get_aliases():
        return AbstractAliases.get_dict(AlterationGroupAliases)
