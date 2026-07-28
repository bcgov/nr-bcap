<script setup lang="ts">
import { computed } from 'vue';

export interface PermitHeader {
    projectName: string;
    applicationNumber: string;
    submissionType: string;
    sector: string;
    submittedDate: string | null;
    // Index signature so the object is a valid router history state value.
    [key: string]: string | null;
}

const { header } = defineProps<{ header: PermitHeader }>();

const meta = computed(() =>
    [header.applicationNumber, header.submissionType, header.sector]
        .filter(Boolean)
        .join(' · '),
);
</script>

<template>
    <div class="permit-header w-full">
        <div class="permit-icon-area">
            <i class="fa-solid fa-bolt permit-icon"></i>
        </div>
        <div class="permit-info">
            <h2 class="project-name">{{ header.projectName }}</h2>
            <p class="permit-meta">
                {{ meta }}
                <span
                    v-if="!header.sector"
                    class="meta-unset"
                >
                    · Sector not specified
                </span>
            </p>
        </div>
        <div class="header-actions">
            <div
                v-if="header.submittedDate"
                class="submitted-text"
            >
                <i class="fa-regular fa-calendar-check"></i>
                Submitted
                <strong>{{ header.submittedDate }}</strong>
            </div>
            <slot
                v-else
                name="actions"
            />
        </div>
    </div>
</template>

<style scoped>
.permit-header {
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
    display: flex;
    align-items: center;
    gap: 1.25rem;
    width: 100%;
    padding: 1.25rem 2rem;
    background: var(--bc-navy);
    border-bottom: 3px solid var(--bc-gold);
}

.permit-icon-area {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-shrink: 0;
    width: 52px;
    height: 52px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.12);
}

.permit-icon {
    font-size: 1.9rem;
    color: var(--bc-gold);
}

.permit-info {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    flex-grow: 1;
    min-width: 0;
}

.project-name {
    margin: 0;
    font-size: 1.9rem;
    line-height: 1.2;
    font-weight: 700;
    color: #ffffff;
    word-break: break-word;
}

.permit-meta {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 400;
    color: #cbd5e1;
}

.meta-unset {
    color: #93a4bb;
    font-style: italic;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
    font-size: 1.15rem;
}

.submitted-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    height: 3.1rem;
    padding: 0 1.1rem;
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 6px;
    color: #ffffff;
}

.submitted-text strong {
    font-weight: 700;
}
</style>
