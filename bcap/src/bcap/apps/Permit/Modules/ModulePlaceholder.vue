<script setup lang="ts">
import Panel from 'primevue/panel';

// A wired-but-empty module: the route exists so the card can open it, the form
// itself is still to come.
defineProps<{ title: string }>();
</script>

<template>
    <Panel class="full-height">
        <h1>{{ title }}</h1>
        <p>This form is coming soon.</p>
    </Panel>
</template>

<style scoped>
h1 {
    margin-bottom: 1rem;
}
</style>
