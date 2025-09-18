<script setup lang="ts">
import { computed } from "vue";
import DetailsSection from "@/bcap/components/DetailsSection/DetailsSection.vue";
import { getDisplayValue, isEmpty } from "@/bcap/util.ts";
import type { RepositorySchema } from "@/bcap/schema/RepositorySchema.ts";
import "primeicons/primeicons.css";

const props = withDefaults(
    defineProps<{
        data: RepositorySchema | undefined;
        loading?: boolean;
        languageCode?: string;
    }>(),
    {
        languageCode: "en",
    },
);

const repositoryData = computed(() => {
    return props.data?.aliased_data?.repository_identifier;
});

const contactData = computed(() => {
    return props.data?.aliased_data?.contact_information;
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
                section-title="1.1 Basic Information"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="repositoryData?.aliased_data">
                        <dt v-if="repositoryData.aliased_data.repository_name && !isEmpty(repositoryData.aliased_data.repository_name)">Repository Name</dt>
                        <dd v-if="repositoryData.aliased_data.repository_name && !isEmpty(repositoryData.aliased_data.repository_name)">
                            {{ getDisplayValue(repositoryData.aliased_data.repository_name) }}
                        </dd>

                        <dt v-if="repositoryData.aliased_data.repository_location_code && !isEmpty(repositoryData.aliased_data.repository_location_code)">Location Code</dt>
                        <dd v-if="repositoryData.aliased_data.repository_location_code && !isEmpty(repositoryData.aliased_data.repository_location_code)">
                            {{ getDisplayValue(repositoryData.aliased_data.repository_location_code) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No repository information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.2 Contact Information"
                :visible="true"
            >
                <template #sectionContent>
                    <dl v-if="contactData?.aliased_data">
                        <dt v-if="contactData.aliased_data.contact_person && !isEmpty(contactData.aliased_data.contact_person)">Contact Person</dt>
                        <dd v-if="contactData.aliased_data.contact_person && !isEmpty(contactData.aliased_data.contact_person)">
                            {{ getDisplayValue(contactData.aliased_data.contact_person) }}
                        </dd>

                        <dt v-if="contactData.aliased_data.contact_email && !isEmpty(contactData.aliased_data.contact_email)">Email</dt>
                        <dd v-if="contactData.aliased_data.contact_email && !isEmpty(contactData.aliased_data.contact_email)">
                            {{ getDisplayValue(contactData.aliased_data.contact_email) }}
                        </dd>

                        <dt v-if="contactData.aliased_data.contact_phone && !isEmpty(contactData.aliased_data.contact_phone)">Phone</dt>
                        <dd v-if="contactData.aliased_data.contact_phone && !isEmpty(contactData.aliased_data.contact_phone)">
                            {{ getDisplayValue(contactData.aliased_data.contact_phone) }}
                        </dd>
                    </dl>
                    <div v-else>
                        <p>No contact information available.</p>
                    </div>
                </template>
            </DetailsSection>

            <DetailsSection
                section-title="1.3 Notes"
                :visible="true"
            >
                <template #sectionContent>
                    <div v-if="props.data?.aliased_data?.repository_notes?.length">
                        <div v-for="(note, index) in props.data.aliased_data.repository_notes" :key="index">
                            {{ note }}
                        </div>
                    </div>
                    <div v-else>
                        <p>No notes available.</p>
                    </div>
                </template>
            </DetailsSection>
        </template>
    </DetailsSection>
</template>
