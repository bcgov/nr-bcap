<script setup lang="ts">
import { provide, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useGettext } from 'vue3-gettext';

import Toast from 'primevue/toast';
import { useToast } from 'primevue/usetoast';

import {
    ANONYMOUS,
    DEFAULT_ERROR_TOAST_LIFE,
    ENGLISH,
    ERROR,
    USER_KEY,
    selectedLanguageKey,
    systemLanguageKey,
} from '@/bcgov_arches_common/constants.ts';

import { routeNames } from '@/bcap/apps/Permit/routes.ts';
import { fetchUser } from '@/bcgov_arches_common/api.ts';

import type { Ref } from 'vue';
import type { Language, User } from '@/bcgov_arches_common/types.ts';

const user = ref<User | null>(null);
const setUser = (userToSet: User | null) => {
    user.value = userToSet;
};
provide(USER_KEY, { user, setUser });

const selectedLanguage: Ref<Language> = ref(ENGLISH);
provide(selectedLanguageKey, selectedLanguage);
const systemLanguage = ENGLISH; // TODO: get from settings
provide(systemLanguageKey, systemLanguage);

const router = useRouter();
const toast = useToast();
const { $gettext } = useGettext();

router.beforeEach(async (to, _from, next) => {
    try {
        let userData = await fetchUser();
        // if (
        //     to.meta.requiresAuthentication &&
        //     !(
        //         'Local Government' in userData.groups ||
        //         'Heritage Branch' in userData.groups
        //     )
        // ) {
        //     window.location.replace(window.location.origin + '/bcap');
        // }

        // setUser(userData);

        const requiresAuthentication = to.matched.some(
            (record) => record.meta.requiresAuthentication,
        );
        if (requiresAuthentication && userData.username === ANONYMOUS) {
            throw new Error();
        } else {
            next();
        }
    } catch (error) {
        if (to.name !== routeNames.home) {
            toast.add({
                severity: ERROR,
                life: DEFAULT_ERROR_TOAST_LIFE,
                summary: $gettext('Login required.'),
                detail: error instanceof Error ? error.message : undefined,
            });
        }
        // next({ name: routeNames.login });
        // This should be the above but it's not configured yet
        next({ name: routeNames.home });
    }
});
</script>

<template>
    <main>
        <div style="display: flex; flex: auto; flex-direction: row">
            <div
                class="bcgov-main-content bc-form"
                style="flex: auto; background-color: #e9e9e9"
            >
                <RouterView />
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
