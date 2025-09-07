<script setup lang="ts">
import { computed, ref } from "vue";
import FieldSet from "primevue/fieldset";
import ProgressSpinner from "primevue/progressspinner";
const props = defineProps<{
    sectionTitle: string;
    visible?: boolean;
    loading?: boolean;
}>();
const sectionVisible = ref(props.visible ?? true);
const isLoading = computed(() => props.loading ?? false);
</script>

<template>
    <FieldSet
        :collapsed="!sectionVisible"
        :legend="props.sectionTitle"
        :toggleable="true"
    >
        <ProgressSpinner
            v-if="isLoading"
            :style="{ width: '2rem', height: '2rem' }"
        />
        <slot
            v-else
            name="sectionContent"
        ></slot>
    </FieldSet>
</template>

<style>
legend.p-fieldset-legend {
    width: unset;
    margin-bottom: 0;
    font-size: 1.75rem;
}
</style>
