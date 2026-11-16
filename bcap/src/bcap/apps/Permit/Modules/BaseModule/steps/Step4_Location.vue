<script setup lang="ts">
import { computed } from 'vue';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { BcapServiceRequestResourceAliasedData } from '@/bcap/client/types.gen.ts';

const { draftData, typedDraftData, isValid, updateValue } =
    useDraftStep<BcapServiceRequestResourceAliasedData>();

const hasCrownLandTenure = computed(() => {
    const tenure =
        typedDraftData?.value?.service_request_location?.aliased_data
            ?.crown_land_tenure_type?.aliased_data?.crown_land_tenure_type;
    return !!tenure?.node_value;
});

defineExpose({ isValid });
</script>

<template>
    <FieldSet legend="BC Property Address">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_location?.aliased_data
                    ?.bc_property_address?.[0]?.aliased_data?.street_number
            "
            graph-slug="bcap_service_request"
            node-alias="street_number"
            @update:aliased-node-data="
                updateValue($event, 'street_number', [
                    'service_request_location',
                    'bc_property_address[0]',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_location?.aliased_data
                    ?.bc_property_address?.[0]?.aliased_data?.street_name
            "
            graph-slug="bcap_service_request"
            node-alias="street_name"
            @update:aliased-node-data="
                updateValue($event, 'street_name', [
                    'service_request_location',
                    'bc_property_address[0]',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_location?.aliased_data
                    ?.bc_property_address?.[0]?.aliased_data?.city
            "
            graph-slug="bcap_service_request"
            node-alias="city"
            @update:aliased-node-data="
                updateValue($event, 'city', [
                    'service_request_location',
                    'bc_property_address[0]',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_location?.aliased_data
                    ?.bc_property_address?.[0]?.aliased_data?.postal_code
            "
            graph-slug="bcap_service_request"
            node-alias="postal_code"
            @update:aliased-node-data="
                updateValue($event, 'postal_code', [
                    'service_request_location',
                    'bc_property_address[0]',
                ])
            "
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_location?.aliased_data
                    ?.bc_property_address?.[0]?.aliased_data?.address_remarks
            "
            graph-slug="bcap_service_request"
            node-alias="address_remarks"
            @update:aliased-node-data="
                updateValue($event, 'address_remarks', [
                    'service_request_location',
                    'bc_property_address[0]',
                ])
            "
        />
    </FieldSet>

    <FieldSet legend="Crown Land Tenure">
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_location?.aliased_data
                    ?.crown_land_tenure_type?.aliased_data
                    ?.crown_land_tenure_type
            "
            graph-slug="bcap_service_request"
            node-alias="crown_land_tenure_type"
            @update:aliased-node-data="
                updateValue($event, 'crown_land_tenure_type', [
                    'service_request_location',
                    'crown_land_tenure_type',
                ])
            "
        />
        <GenericWidget
            v-if="hasCrownLandTenure"
            :mode="EDIT"
            :aliased-node-data="
                draftData?.service_request_location?.aliased_data
                    ?.crown_land_tenure_type?.aliased_data?.tenure_description
            "
            graph-slug="bcap_service_request"
            node-alias="tenure_description"
            @update:aliased-node-data="
                updateValue($event, 'tenure_description', [
                    'service_request_location',
                    'crown_land_tenure_type',
                ])
            "
        />
        <template v-if="hasCrownLandTenure">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.service_request_location?.aliased_data
                        ?.crown_land_tenure_type?.aliased_data
                        ?.crown_land_survey_information?.aliased_data?.districts
                "
                graph-slug="bcap_service_request"
                node-alias="districts"
                @update:aliased-node-data="
                    updateValue($event, 'districts', [
                        'service_request_location',
                        'crown_land_tenure_type',
                        'crown_land_survey_information',
                    ])
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.service_request_location?.aliased_data
                        ?.crown_land_tenure_type?.aliased_data
                        ?.crown_land_survey_information?.aliased_data
                        ?.land_title
                "
                graph-slug="bcap_service_request"
                node-alias="land_title"
                @update:aliased-node-data="
                    updateValue($event, 'land_title', [
                        'service_request_location',
                        'crown_land_tenure_type',
                        'crown_land_survey_information',
                    ])
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.service_request_location?.aliased_data
                        ?.crown_land_tenure_type?.aliased_data
                        ?.crown_land_survey_information?.aliased_data?.pin_n1
                "
                graph-slug="bcap_service_request"
                node-alias="pin_n1"
                @update:aliased-node-data="
                    updateValue($event, 'pin_n1', [
                        'service_request_location',
                        'crown_land_tenure_type',
                        'crown_land_survey_information',
                    ])
                "
            />
        </template>
    </FieldSet>
    <br />
</template>
