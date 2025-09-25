<script setup lang="ts">
interface Props {
    message?: string;
}

const props = withDefaults(defineProps<Props>(), {
    message: 'No data found',
});
</script>

<template>
    <div class="empty-section">
        <p>{{ props.message }}</p>
    </div>
</template>

<style scoped></style>
