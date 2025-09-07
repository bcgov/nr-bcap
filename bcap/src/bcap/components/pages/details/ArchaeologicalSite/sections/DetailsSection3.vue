<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";

import "primeicons/primeicons.css";
import type { SiteVisitSchema } from "@/bcap/schema/SiteVisitSchema.ts";
import SiteVisitDetailsSection3 from "@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection3.vue";

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema[] | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const currentData = computed<SiteVisitSchema[] | undefined>(
    (): SiteVisitSchema[] | undefined => {
        return props.data as SiteVisitSchema[] | undefined;
    },
);

const sectionTitle = function (siteVisit: SiteVisitSchema): string {
    return [
        siteVisit.aliased_data.site_visit_details.aliased_data
            .last_date_of_site_visit.display_value,
        siteVisit.aliased_data.site_visit_details.aliased_data.site_visit_type
            .display_value,
    ].join(" ");
};
</script>

<template>
    <DetailsSection
        section-title="3. Site Visits"
        :visible="true"
        :loading="props.loading"
    >
        <template #sectionContent>
            <SiteVisitDetailsSection3
                v-for="visit in currentData"
                :key="visit.resourceinstanceid"
                :data="visit"
                :visible="false"
                :section-title="sectionTitle(visit)"
                :language-code="languageCode"
            ></SiteVisitDetailsSection3>

            <div>
                {{ Object.keys(currentData?.[0]?.aliased_data ?? {}) }}
                <!--                <StandardDataTable-->
                <!--                    :table-data="currentData?.site_typology ?? []"-->
                <!--                    :column-definitions="typologyColumns"-->
                <!--                    title="Site Typology"-->
                <!--                    initial-sort-field="0"-->
                <!--                ></StandardDataTable>-->
            </div>
        </template>
    </DetailsSection>
</template>
