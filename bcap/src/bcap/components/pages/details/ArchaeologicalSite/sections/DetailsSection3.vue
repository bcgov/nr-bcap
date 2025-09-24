<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import 'primeicons/primeicons.css';
import type { SiteVisitSchema } from '@/bcap/schema/SiteVisitSchema.ts';
import SiteVisitDetailsSection3 from '@/bcap/components/pages/details/SiteVisit/sections/SiteVisitDetailsSection3.vue';

const props = withDefaults(
    defineProps<{
        data: SiteVisitSchema[] | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: 'en',
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
                            variant="subsection"
                            v-for="visit in currentData"
                            :key="visit.resourceinstanceid"
                            :data="visit"
                            :visible="false"
                            :section-title="sectionTitle(visit)"
                            :language-code="languageCode"
                        />
                    </div>
                    <EmptyState
                        v-else
                        message="No site visits available for this site."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
