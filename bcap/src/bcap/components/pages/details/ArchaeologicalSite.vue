<script setup lang="ts">
import { computed, ref } from "vue";


type LangCode = string;
interface Descriptor {
  name: string;
  // add more fields if needed
}

type ResourceDescriptors = Record<LangCode, Descriptor>;

const formattedNow = computed(() => {
  // undefined => use browser's locale (e.g., "en-CA", "fr-FR", etc.)
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(now.value);
});

const props = withDefaults(defineProps<{
    data: unknown,
    resourceDescriptors: ResourceDescriptors,
    languageCode?: string
}>(), {
    resourceDescriptors: () => ({en: {name: "Undefined"}}),
    languageCode: "en"
});

const now = ref(new Date());

</script>

<template>
    <div class="container">
        <div class="report-toolbar-preview ep-form-toolbar">
        <h4 class="report-toolbar-title"><span class="bc-report-title">Hi42! Archaeological Site</span> -
            <span class="bc-report-title">{{ props?.resourceDescriptors?.[props.languageCode]?.name }}</span></h4>
        <!-- Tools -->
        <div class="ep-form-toolbar-tools mar-no flex">
            <p class="report-print-date">
                <span data-bind="text: reportDate">{{ formattedNow }}</span>
            </p>
        </div>
    </div>
        <div style="background-color: lightblue">{{ props.data }}</div>
        <div style="background-color: lightgreen">{{ props.resourceDescriptors }}</div>
    </div>
</template>

<style scoped>

</style>