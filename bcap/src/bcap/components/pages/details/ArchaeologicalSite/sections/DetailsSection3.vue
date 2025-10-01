<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import type { EditLogData } from '@/bcgov_arches_common/types.ts';
import 'primeicons/primeicons.css';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import SiteVisitDetailsSection3 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection3.vue';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema[] | undefined;
        loading?: boolean;
        languageCode?: string;
        forceCollapsed?: boolean;
        editLogData?: EditLogData;
    }>(),
    {
        languageCode: 'en',
        loading: false,
        forceCollapsed: undefined,
        editLogData: () => ({}),
    },
);

const currentData = computed<SiteVisitSchema[] | undefined>(
    (): SiteVisitSchema[] | undefined => {
        return props.data as SiteVisitSchema[] | undefined;
    },
);

const sectionTitle = function (siteVisit: SiteVisitSchema): string {
    return siteVisit.descriptors.en.name;
};

const hasSiteVisits = computed(() => {
    return currentData.value && currentData.value.length > 0;
});
</script>

<template>
    <DetailsSection
        section-title="3. Site Visits"
        :visible="true"
        :loading="props.loading"
        :force-collapsed="props.forceCollapsed"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Site Visit Records"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasSiteVisits }"
            >
                <template #sectionContent>
                    <div v-if="hasSiteVisits">
                        <SiteVisitDetailsSection3
                            v-for="visit in currentData"
                            :key="visit.resourceinstanceid"
                            variant="subsection"
                            :data="visit"
                            :visible="false"
                            :section-title="sectionTitle(visit)"
                            :language-code="languageCode"
                            :edit-log-data="editLogData"
                        />
                    </div>
                    <EmptyState
                        v-else
                        message="No site visit(s) available for this site."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
