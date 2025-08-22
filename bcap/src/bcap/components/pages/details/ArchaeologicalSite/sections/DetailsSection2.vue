<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import type {
    AliasedNodeData,
    AliasedTileData,
} from "@/arches_component_lab/types.ts";
// main.js or in your component's script setup
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import "primeicons/primeicons.css";
import type { IdentificationAndRegistrationTile } from "@/bcap/schema/ArchaeologySiteSchema.ts";

const props = withDefaults(
    defineProps<{
        data: IdentificationAndRegistrationTile | undefined;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<IdentificationAndRegistrationTile | undefined>(
    (): AliasedTileData | undefined => {
        return props.data?.aliased_data as
            | IdentificationAndRegistrationTile
            | undefined;
    },
);

const id_fields = [
    "borden_number",
    "registration_date",
    "registration_status",
    "parcel_owner_type",
    "site_creation_date",
    "register_type",
    "parent_site",
    "site_alert",
    "authority",
    "site_names",
] as const;

type IdFieldKey = (typeof id_fields)[number];

// Turn "borden_number" -> "Borden Number"
const labelize = (key: string) =>
    key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
</script>

<template>
    <DetailsSection
        section-title="2. ID & Registration"
        :visible="true"
    >
        <template #sectionContent>
            <div>
                <dl>
                    <template
                        v-for="field in id_fields"
                        :key="field"
                    >
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.[
                                        field as IdFieldKey
                                    ] as AliasedNodeData,
                                )
                            "
                        >
                            {{ labelize(field) }}
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.[
                                        field as IdFieldKey
                                    ] as AliasedNodeData,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.[
                                        field as IdFieldKey
                                    ] as AliasedNodeData,
                                )
                            }}
                        </dd>
                    </template>
                </dl>
                <dl v-if="(currentData?.site_decision?.length ?? 0) > 0">
                    <dt>Decision History</dt>
                    <dd>
                        <DataTable
                            :value="currentData?.site_decision"
                            data-key="tileid"
                            responsive-layout="scroll"
                            sort-field="aliased_data.decision_date.display_value"
                            :sort-order="-1"
                        >
                            <Column
                                header="Decision Date"
                                field="aliased_data.decision_date.display_value"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getDisplayValue(
                                            slotProps.data.aliased_data
                                                ?.decision_date,
                                        )
                                    }}
                                </template>
                            </Column>

                            <Column
                                header="Decision Maker"
                                field="aliased_data.decision_made_by.display_value"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getDisplayValue(
                                            slotProps.data.aliased_data
                                                ?.decision_made_by,
                                        )
                                    }}
                                </template>
                            </Column>

                            <Column
                                header="Decision"
                                field="aliased_data.site_decision.display_value"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getDisplayValue(
                                            slotProps.data.aliased_data
                                                ?.site_decision,
                                        )
                                    }}
                                </template>
                            </Column>

                            <Column
                                header="Criteria"
                                field="aliased_data.decision_criteria.display_value"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getDisplayValue(
                                            slotProps.data.aliased_data
                                                ?.decision_criteria,
                                        )
                                    }}
                                </template>
                            </Column>

                            <Column
                                header="Description"
                                field="aliased_data.decision_description.display_value"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getDisplayValue(
                                            slotProps.data.aliased_data
                                                ?.decision_description,
                                        )
                                    }}
                                </template>
                            </Column>

                            <Column
                                header="Recommended On"
                                field="aliased_data.recommendation_date.display_value"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getDisplayValue(
                                            slotProps.data.aliased_data
                                                ?.recommendation_date,
                                        )
                                    }}
                                </template>
                            </Column>

                            <Column
                                header="Recommended By"
                                field="aliased_data.recommended_by.display_value"
                                sortable
                            >
                                <template #body="slotProps">
                                    {{
                                        getDisplayValue(
                                            slotProps.data.aliased_data
                                                ?.recommended_by,
                                        )
                                    }}
                                </template>
                            </Column>
                        </DataTable>
                    </dd>
                </dl>
            </div>
        </template>
    </DetailsSection>
</template>

<style>
dl {
    display: flex;
    flex-direction: column;
    padding-bottom: 1rem;
}
dt {
    min-width: 20rem;
}
</style>
<style scoped></style>
