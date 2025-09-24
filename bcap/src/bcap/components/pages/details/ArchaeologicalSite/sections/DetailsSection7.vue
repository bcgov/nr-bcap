<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import 'primeicons/primeicons.css';

const props = withDefaults(
    defineProps<{
        data: any;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: 'en',
    },
);

const hasRestrictedRemainsInfo = computed(() => {
    return props.data?.aliased_data?.restricted_ancestral_remains_remark
        ?.aliased_data;
});
</script>

<template>
    <DetailsSection
        section-title="7. Ancestral Remains"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Restricted Ancestral Remains Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasRestrictedRemainsInfo }"
            >
                <template #sectionContent>
                    <dl v-if="hasRestrictedRemainsInfo">
                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data
                                        .restricted_ancestral_remains_remark,
                                )
                            "
                        >
                            Restricted Ancestral Remains Remarks
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data
                                        .restricted_ancestral_remains_remark,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data
                                        .restricted_ancestral_remains_remark,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data.remains_remark_entry_date,
                                )
                            "
                        >
                            Entered On
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data.remains_remark_entry_date,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data.remains_remark_entry_date,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data.remains_remark_made_by,
                                )
                            "
                        >
                            Entered By
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data.remains_remark_made_by,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    props.data.aliased_data
                                        .restricted_ancestral_remains_remark
                                        .aliased_data.remains_remark_made_by,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No restricted ancestral remains information available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
