<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import type { LegislativeAct } from '@/bcap/client/types.gen.ts';
import type { AliasedNodeData } from '@/arches_vue_components/types.ts';
import 'primeicons/primeicons.css';

const props = withDefaults(
    defineProps<{
        data: LegislativeAct | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: 'en',
    },
);

// The generated LegislativeAct type does not include the legislative_act tile
// (act_name, act_type, etc.). currentData is cast for backwards-compatibility
// with the template; all has* computed will evaluate to false.
const currentData = computed<
    { aliased_data?: Record<string, AliasedNodeData | undefined> } | undefined
>(() => {
    return undefined;
});

const hasBasicInfo = computed(() => {
    const data = currentData.value?.aliased_data;
    return (
        data &&
        (!isEmpty(data.act_name) ||
            !isEmpty(data.act_type) ||
            !isEmpty(data.jurisdiction) ||
            !isEmpty(data.act_citation) ||
            !isEmpty(data.responsible_ministry) ||
            !isEmpty(data.act_status))
    );
});

const hasDates = computed(() => {
    const data = currentData.value?.aliased_data;
    return (
        data && (!isEmpty(data.enactment_date) || !isEmpty(data.repeal_date))
    );
});

const hasDescription = computed(() => {
    const data = currentData.value?.aliased_data;
    return data && !isEmpty(data.act_description);
});
</script>

<template>
    <DetailsSection
        section-title="1. Legislative Act Information"
        :loading="props.loading"
        :visible="true"
    >
        <template #sectionContent>
            <DetailsSection
                section-title="Basic Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasBasicInfo }"
            >
                <template #sectionContent>
                    <dl v-if="hasBasicInfo">
                        <dt
                            v-if="!isEmpty(currentData?.aliased_data?.act_name)"
                        >
                            Act Name
                        </dt>
                        <dd
                            v-if="!isEmpty(currentData?.aliased_data?.act_name)"
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.act_name,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="!isEmpty(currentData?.aliased_data?.act_type)"
                        >
                            Act Type
                        </dt>
                        <dd
                            v-if="!isEmpty(currentData?.aliased_data?.act_type)"
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.act_type,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.jurisdiction,
                                )
                            "
                        >
                            Jurisdiction
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.jurisdiction,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.jurisdiction,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.act_citation,
                                )
                            "
                        >
                            Citation
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.act_citation,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.act_citation,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data
                                        ?.responsible_ministry,
                                )
                            "
                        >
                            Responsible Ministry
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data
                                        ?.responsible_ministry,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data
                                        ?.responsible_ministry,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(currentData?.aliased_data?.act_status)
                            "
                        >
                            Status
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(currentData?.aliased_data?.act_status)
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.act_status,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No legislative act information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Dates"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDates }"
            >
                <template #sectionContent>
                    <dl v-if="hasDates">
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.enactment_date,
                                )
                            "
                        >
                            Enactment Date
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.enactment_date,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.enactment_date,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(currentData?.aliased_data?.repeal_date)
                            "
                        >
                            Repeal Date
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(currentData?.aliased_data?.repeal_date)
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.repeal_date,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No date information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Description"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasDescription }"
            >
                <template #sectionContent>
                    <dl v-if="hasDescription">
                        <dt
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.act_description,
                                )
                            "
                        >
                            Description
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    currentData?.aliased_data?.act_description,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    currentData?.aliased_data?.act_description,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No description available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
