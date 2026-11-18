<script setup lang="ts">
import { Form } from '@primevue/forms';
import GenericWidget from '@/arches_vue_components/generics/GenericWidget/GenericWidget.vue';
import { EDIT } from '@/arches_vue_components/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import { useDraftStep } from '@/bcap/composables/useDraftStep.ts';
import type { HcaPermitApplicationResourceAliasedData } from '@/bcap/client/types.gen.ts';

const emit = defineEmits(['update:step-is-valid']);

const { draftData, isValid, updateValue } =
    useDraftStep<HcaPermitApplicationResourceAliasedData>(
        undefined,
        'application_contacts',
        emit,
    );

defineExpose({ isValid });
</script>

<template>
    <Form
        :validate-on-blur="true"
        :validate-on-value-update="true"
        :validate-on-mount="false"
    >
        <FieldSet legend="Archaeologist">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_contacts?.aliased_data?.archaeologist
                "
                graph-slug="hca_permit_application"
                node-alias="archaeologist"
                @update:aliased-node-data="
                    updateValue($event, 'archaeologist', 'application_contacts')
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_contacts?.aliased_data
                        ?.is_first_permit_applciation
                "
                graph-slug="hca_permit_application"
                node-alias="is_first_permit_applciation"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'is_first_permit_applciation',
                        'application_contacts',
                    )
                "
            />
        </FieldSet>

        <FieldSet legend="Proponent Contact">
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_contacts?.aliased_data?.proponent_name
                "
                graph-slug="hca_permit_application"
                node-alias="proponent_name"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'proponent_name',
                        'application_contacts',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_contacts?.aliased_data
                        ?.proponent_address
                "
                graph-slug="hca_permit_application"
                node-alias="proponent_address"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'proponent_address',
                        'application_contacts',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_contacts?.aliased_data
                        ?.proponent_company
                "
                graph-slug="hca_permit_application"
                node-alias="proponent_company"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'proponent_company',
                        'application_contacts',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_contacts?.aliased_data
                        ?.proponent_email
                "
                graph-slug="hca_permit_application"
                node-alias="proponent_email"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'proponent_email',
                        'application_contacts',
                    )
                "
            />
            <GenericWidget
                :mode="EDIT"
                :aliased-node-data="
                    draftData?.application_contacts?.aliased_data
                        ?.proponent_phone
                "
                graph-slug="hca_permit_application"
                node-alias="proponent_phone"
                @update:aliased-node-data="
                    updateValue(
                        $event,
                        'proponent_phone',
                        'application_contacts',
                    )
                "
            />
        </FieldSet>
    </Form>
</template>
