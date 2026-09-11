<script setup lang="ts">
defineProps<{
    title: string;
    detail?: string;
}>();
</script>

<template>
    <div
        class="inline-error"
        role="alert"
    >
        <p class="inline-error-title">
            <i
                class="pi pi-times-circle inline-error-icon"
                aria-hidden="true"
            />
            {{ title }}
        </p>
        <p
            v-if="detail"
            class="inline-error-detail"
        >
            {{ detail }}
        </p>
    </div>
</template>

<style scoped>
.inline-error {
    padding: 1.25rem 1.5rem;
    background: #ffffff;
    color: var(--bc-text);
    border: 1px solid #e5e7eb;
    border-left: 4px solid #d8292f;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(16, 24, 40, 0.06);
}

/* The icon rides in the title's row, so it centres on the title whatever the
   icon font's metrics. */
.inline-error-title {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    line-height: 1.4;
}

.inline-error-icon {
    flex: none;
    color: #d8292f;
    font-size: 1.3rem;
    line-height: 1;
}

/* Indented to the title text (icon plus gap); the server sends one message
   per line. */
.inline-error-detail {
    margin: 0.35rem 0 0 1.9rem;
    font-size: 1.15rem;
    line-height: 1.5;
    white-space: pre-line;
}
</style>
