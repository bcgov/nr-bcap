<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';

// Sits under the header band, not inside it: the band is identity, this is
// navigation. The last crumb is the current page and is never a link.
export interface Crumb {
    label: string;
    to?: RouteLocationRaw;
}

defineProps<{ crumbs: Crumb[] }>();
</script>

<template>
    <nav
        class="crumbs"
        aria-label="Breadcrumb"
    >
        <template
            v-for="(crumb, index) in crumbs"
            :key="crumb.label"
        >
            <i
                v-if="index"
                class="fa-solid fa-chevron-right crumb-sep"
                aria-hidden="true"
            ></i>
            <RouterLink
                v-if="crumb.to && index < crumbs.length - 1"
                :to="crumb.to"
                class="crumb-link"
            >
                {{ crumb.label }}
            </RouterLink>
            <span
                v-else
                class="crumb-current"
                aria-current="page"
            >
                {{ crumb.label }}
            </span>
        </template>
    </nav>
</template>

<style scoped>
.crumbs {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    min-width: 0;
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
    font-size: 1.25rem;
    line-height: 1.4;
}
.crumb-link {
    color: var(--bc-link, #1a5a96);
    font-weight: 400;
    text-decoration: none;
    white-space: nowrap;
}
.crumb-link:hover {
    text-decoration: underline;
}
.crumb-sep {
    font-size: 0.85em;
    color: #9aa4b1;
}
/* The trailing crumb is the page title's echo, so it stays quiet and truncates
   rather than wrapping the row. */
.crumb-current {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #4b5563;
    font-weight: 600;
}
</style>
