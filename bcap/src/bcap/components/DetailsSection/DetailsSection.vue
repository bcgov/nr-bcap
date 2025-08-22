<script setup lang="ts">
import { ref } from "vue";
import FieldSet from "primevue/fieldset";
const props = defineProps<{ sectionTitle: string; visible: boolean }>();
const sectionVisible = ref(props.visible || true);
</script>

<template>
    <FieldSet
        :collapsed="!sectionVisible"
        :legend="props.sectionTitle"
        :toggleable="true"
    >
        <slot name="sectionContent"></slot>
    </FieldSet>
</template>
