<script setup lang="ts">
import { computed } from 'vue';
import DetailsSection from '@/bcap/components/DetailsSection/DetailsSection.vue';
import EmptyState from '@/bcap/components/EmptyState.vue';
import { getDisplayValue, isEmpty } from '@/bcap/util.ts';
import type { RepositorySchema } from '@/bcap/schema/RepositorySchema.ts';
import 'primeicons/primeicons.css';

const props = withDefaults(
    defineProps<{
        data: RepositorySchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: 'en',
    },
);

const repositoryData = computed(() => {
    return props.data?.aliased_data?.repository_identifier;
});

const contactData = computed(() => {
    return props.data?.aliased_data?.contact_information;
});

const hasBasicInfo = computed(() => {
    const data = repositoryData.value?.aliased_data;
    return (
        data &&
        (!isEmpty(data.repository_name) ||
            !isEmpty(data.repository_location_code))
    );
});

const hasContactInfo = computed(() => {
    const data = contactData.value?.aliased_data;
    return (
        data &&
        (!isEmpty(data.contact_person) ||
            !isEmpty(data.contact_email) ||
            !isEmpty(data.contact_phone))
    );
});

const hasNotes = computed(() => {
    return (
        props.data?.aliased_data?.repository_notes &&
        props.data.aliased_data.repository_notes.length > 0
    );
});
</script>

<template>
    <DetailsSection
        section-title="1. Repository Information"
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
                            v-if="
                                !isEmpty(
                                    repositoryData?.aliased_data
                                        ?.repository_name,
                                )
                            "
                        >
                            Repository Name
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    repositoryData?.aliased_data
                                        ?.repository_name,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    repositoryData?.aliased_data
                                        ?.repository_name,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    repositoryData?.aliased_data
                                        ?.repository_location_code,
                                )
                            "
                        >
                            Location Code
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    repositoryData?.aliased_data
                                        ?.repository_location_code,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    repositoryData?.aliased_data
                                        ?.repository_location_code,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No repository information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Contact Information"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasContactInfo }"
            >
                <template #sectionContent>
                    <dl v-if="hasContactInfo">
                        <dt
                            v-if="
                                !isEmpty(
                                    contactData?.aliased_data?.contact_person,
                                )
                            "
                        >
                            Contact Person
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    contactData?.aliased_data?.contact_person,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    contactData?.aliased_data?.contact_person,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    contactData?.aliased_data?.contact_email,
                                )
                            "
                        >
                            Email
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    contactData?.aliased_data?.contact_email,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    contactData?.aliased_data?.contact_email,
                                )
                            }}
                        </dd>

                        <dt
                            v-if="
                                !isEmpty(
                                    contactData?.aliased_data?.contact_phone,
                                )
                            "
                        >
                            Phone
                        </dt>
                        <dd
                            v-if="
                                !isEmpty(
                                    contactData?.aliased_data?.contact_phone,
                                )
                            "
                        >
                            {{
                                getDisplayValue(
                                    contactData?.aliased_data?.contact_phone,
                                )
                            }}
                        </dd>
                    </dl>
                    <EmptyState
                        v-else
                        message="No contact information available."
                    />
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="Notes"
                variant="subsection"
                :visible="true"
                :class="{ 'empty-section': !hasNotes }"
            >
                <template #sectionContent>
                    <div v-if="hasNotes">
                        <div
                            v-for="(note, index) in props.data?.aliased_data
                                ?.repository_notes"
                            :key="index"
                            class="note-item"
                        >
                            {{ note }}
                        </div>
                    </div>
                    <EmptyState
                        v-else
                        message="No notes available."
                    />
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>

<style scoped>
.note-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid #e9ecef;
}

.note-item:last-child {
    border-bottom: none;
}
</style>
