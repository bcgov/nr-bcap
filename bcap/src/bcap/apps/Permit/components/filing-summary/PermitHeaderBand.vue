<script setup lang="ts">
import { computed } from 'vue';

export interface PermitHeader {
    projectName: string;
    applicationNumber: string;
    submissionType: string;
    sector: string;
    organization: string;
    submittedDate: string | null;
    // Index signature so the object is a valid router history state value.
    [key: string]: string | null;
}

const { header } = defineProps<{ header: PermitHeader }>();

const meta = computed(() =>
    [header.organization, header.submissionType, header.sector].filter(Boolean),
);
</script>

<template>
    <div class="permit-header w-full">
        <div class="permit-icon-area">
            <i class="fa-solid fa-bolt permit-icon"></i>
        </div>
        <div class="permit-info">
            <div class="permit-title-line">
                <h2 class="project-name">{{ header.projectName }}</h2>
                <span class="application-number">
                    {{ header.applicationNumber }}
                </span>
            </div>
            <p class="permit-meta">
                <span
                    v-for="part in meta"
                    :key="part"
                    class="meta-part"
                >
                    {{ part }}
                </span>
                <span
                    v-if="!header.sector"
                    class="meta-flag"
                >
                    Sector not specified
                </span>
            </p>
        </div>
        <div class="header-actions">
            <slot name="actions" />
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
    gap: 0.35rem;
    flex-grow: 1;
    min-width: 0;
}

.permit-title-line {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.75rem;
}

.project-name {
    margin: 0;
    font-size: 1.9rem;
    line-height: 1.2;
    font-weight: 700;
    color: #ffffff;
    word-break: break-word;
}

.application-number {
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: #b6c4d6;
}

.permit-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0;
    font-size: 1.15rem;
    color: #cbd5e1;
}

.meta-part + .meta-part::before {
    content: '·';
    padding-right: 0.5rem;
    color: #6f819b;
}

.meta-flag {
    padding: 0.05rem 0.7rem;
    border: 1px solid var(--bc-gold);
    border-radius: 999px;
    font-size: 1.15rem;
    color: var(--bc-gold);
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
    font-size: 1.15rem;
}
</style>
