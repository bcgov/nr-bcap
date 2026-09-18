<script setup lang="ts">
import { provide, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useGettext } from 'vue3-gettext';

import Toast from 'primevue/toast';

import {
    ENGLISH,
    selectedLanguageKey,
    systemLanguageKey,
} from '@/bcgov_arches_common/constants.ts';
import { useUserStore } from '@/bcap/stores/user.ts';

import type { Ref } from 'vue';
import type { RouteLocationNormalized } from 'vue-router';
import type { Language } from '@/bcgov_arches_common/types.ts';

const selectedLanguage: Ref<Language> = ref(ENGLISH);
provide(selectedLanguageKey, selectedLanguage);
const systemLanguage = ENGLISH; // TODO: get from settings
provide(systemLanguageKey, systemLanguage);

const router = useRouter();
const { $gettext } = useGettext();
const userStore = useUserStore();

// Shown in place of the router view. A refusal is not redirected anywhere: the
// staff pages are their own arches plugin, so sending the router elsewhere would
// leave the wrong page rendered inside their shell under a url that disagrees.
const accessError = ref('');

const authorize = async (to: RouteLocationNormalized) => {
    // The profile endpoint returns 403 for anonymous users. Change this if anonymous access is wanted.
    const profile = await userStore.load().catch(() => null);
    if (!profile) {
        // TODO: send to routeNames.login once that route is configured.
        accessError.value = $gettext(
            'You need to be signed in to use this page.',
        );
        return false;
    }
    const staffOnly = to.matched.some((record) => record.meta.requiresInternal);
    if (staffOnly && !profile.is_internal) {
        accessError.value = $gettext(
            'This page is for Archaeology Branch staff.',
        );
        return false;
    }
    accessError.value = '';
    return true;
};

router.beforeEach(authorize);

// Installing the router starts its first navigation, and that happens before
// this component's setup runs, so the guard above never sees the landing route.
router.isReady().then(() => authorize(router.currentRoute.value));
</script>

<template>
    <main>
        <div style="display: flex; flex: auto; flex-direction: row">
            <div
                class="bcgov-main-content bc-form"
                style="flex: auto; background-color: #e9e9e9"
            >
                <div
                    v-if="accessError"
                    class="access-error"
                >
                    {{ accessError }}
                </div>
                <RouterView v-else />
            </div>
        </div>
    </main>
    <Toast />
</template>

<style scoped>
main {
    font-family: sans-serif;
    min-height: 100%;
    width: 100%;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    /* Breathing room under the last row when scrolled to the bottom. */
    padding-bottom: 30px;
}

.full-height {
    height: 100%;
}

.access-error {
    margin: 1.5rem;
}
</style>

<style>
@import url('@/bcap/styles/bc-theme.css');

/* The arches plugin panel is a fixed calc(100vh - 50px) box, so a permit page
   taller than the viewport is cut off. Let it scroll. */
.content-panel {
    overflow-y: auto;
}

/* bc-theme forces BCSans on .bc-form *, and only restores the FA4/5 class names
   (.fa/.fas/.far). This app uses Font Awesome 6 style classes, so restore those
   too or the glyphs blank out to boxes. */
.bc-form .fa-solid,
.bc-form .fa-regular,
.bc-form .fa-light,
.bc-form .fa-thin {
    font-family: 'Font Awesome 6 Free';
}
.bc-form .fa-brands,
.bc-form .fab {
    font-family: 'Font Awesome 6 Brands';
}

/* The base theme sizes plain Select/MultiSelect labels but not tree-backed
   select labels or the string-widget inputs, so those render off-size. Bring
   them to the same bcgov form size as the rest of the fields. */
.bc-form input,
.bc-form textarea,
.bc-form .p-treeselect-label {
    font-size: 1.15rem;
}

/* Select/TreeSelect/MultiSelect panels teleport to <body>, outside the .bc-form
   wrapper, so the bcgov option theming can't reach them through that class.
   Apply it to the overlay panels directly. */
.p-select-overlay,
.p-treeselect-overlay,
.p-multiselect-overlay {
    font-family: 'BCSans', 'Noto Sans', Verdana, Arial, sans-serif;
    border: 1px solid #d1d5db;
}
.p-select-overlay *,
.p-treeselect-overlay *,
.p-multiselect-overlay * {
    font-size: 1.15rem;
}
.p-select-option.p-focus,
.p-treeselect-overlay .p-tree-node-content:hover,
.p-multiselect-option.p-focus {
    background: var(--bc-panel);
}
.p-select-option.p-select-option-selected,
.p-treeselect-overlay .p-tree-node-content.p-tree-node-selected,
.p-multiselect-option.p-multiselect-option-selected {
    background: var(--bc-selected);
    color: var(--bc-navy);
}

/* TreeSelect options render as tree nodes, whose panel class differs from the
   plain Select overlay. PrimeVue's runtime styles win on load order, so force
   the size to match the other dropdowns. */
.p-tree-node-label {
    font-size: 1.15rem !important;
}

/* PrimeVue draws a blue focus/selected indicator on the active tree option that
   shows as two bars across the row. Neutralize it wherever it lives: the node,
   its row, the selected/selectable states, and their pseudo-elements. */
.p-tree-node,
.p-tree-node:focus,
.p-tree-node:focus-visible,
.p-tree-node-content,
.p-tree-node-content.p-focus,
.p-tree-node-content.p-tree-node-selectable,
.p-tree-node-content.p-tree-node-selected,
.p-tree-node-content:focus,
.p-tree-node-content:focus-visible,
.p-tree-node-content::before,
.p-tree-node-content::after {
    box-shadow: none !important;
    outline: none !important;
    border: none !important;
    background-image: none !important;
    --p-focus-ring-width: 0 !important;
    --p-focus-ring-shadow: none !important;
}

/* The base theme mutes placeholder text for plain selects and inputs but not
   the tree-backed select, so its placeholder reads darker. Match it. */
.bc-form .p-treeselect-label.p-placeholder {
    color: var(--bc-muted);
}

/* The base theme borders plain Select/MultiSelect but not the tree-backed
   select, so it loses the form's default border. Bring it over. */
.bc-form .p-treeselect {
    width: 100%;
    border: 1px solid var(--bc-border);
    border-radius: 6px;
    background: #ffffff;
}

.bcgov-vertical-steps > .p-steplist {
    flex-direction: column;
    align-items: flex-start;
}

.bcgov-vertical-step-panels {
    height: 100%;
    width: 100%;
}

.bcgov-main-content .p-panel {
    background-color: var(--p-panel-background) !important;
}

.bcgov-stepper {
    display: flex;
    flex-direction: row;
}

.widget-label {
    margin-top: 1rem;
}
.pi.pi-asterisk {
    color: red;
    padding-left: 0.25rem;
}
</style>
