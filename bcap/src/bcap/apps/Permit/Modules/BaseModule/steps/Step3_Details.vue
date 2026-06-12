<script setup lang="ts">
import { inject, type Ref } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type {
    AliasedNodeData,
    CardXNodeXWidgetData,
} from '@/arches_component_lab/types.ts';
import { updateDraftValue } from '@/bcap/util.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

const draftId = inject<Ref<string | null>>('draftId');
const draftData = inject<Ref<ArchesDraftData>>('draftData');
const graphSlug = 'permit_application';

const isValid = () => {
    return true;
};

const updateValue = (
    newValue: AliasedNodeData,
    attribute_name: string,
    node_group_alias: string | string[],
) => {
    updateDraftValue(
        draftData?.value,
        draftId?.value,
        graphSlug,
        newValue,
        attribute_name,
        node_group_alias,
    );
};

const mapOverrides = {
    widget: {
        widgetid: '',
        component:
            'bcgov_arches_common/widgets/MapDropZoneWidget/MapDropZoneWidget.vue',
    },
} satisfies Partial<CardXNodeXWidgetData>;

defineExpose({ isValid });
</script>

<template>
    <FieldSet legend="">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.archaeological_assessment_plan?.aliased_data
                    ?.section_1_overview?.aliased_data?.assessment_approach
            "
            graph-slug="permit_application"
            node-alias="assessment_approach"
            @update:value="
                updateValue($event, 'assessment_approach', [
                    'archaeological_assessment_plan',
                    'section_1_overview',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.first_nation_consultation?.aliased_data
                    ?.fn_file_numbers
            "
            graph-slug="permit_application"
            node-alias="fn_file_numbers"
            @update:value="
                updateValue(
                    $event,
                    'fn_file_numbers',
                    'first_nation_consultation',
                )
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data?.project_boundary
            "
            :card-x-node-x-widget-data-overrides="mapOverrides"
            graph-slug="permit_application"
            node-alias="project_boundary"
            @update:value="
                updateValue($event, 'project_boundary', 'proposed_project')
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data
                    ?.development_project_details?.aliased_data
                    ?.industrial_sector
            "
            graph-slug="permit_application"
            node-alias="industrial_sector"
            @update:value="
                updateValue($event, 'industrial_sector', [
                    'proposed_project',
                    'development_project_details',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.proposed_project?.aliased_data
                    ?.development_project_details?.aliased_data
                    ?.alteration_details
            "
            graph-slug="permit_application"
            node-alias="alteration_details"
            @update:value="
                updateValue($event, 'alteration_details', [
                    'proposed_project',
                    'development_project_details',
                ])
            "
        />
    </FieldSet>
    <br />
</template>

<style></style>
