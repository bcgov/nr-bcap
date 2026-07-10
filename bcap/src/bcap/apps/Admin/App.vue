<script setup lang="ts">
import { provide, ref } from 'vue';

import Toast from 'primevue/toast';

import {
    ENGLISH,
    USER_KEY,
    selectedLanguageKey,
    systemLanguageKey,
} from '@/bcgov_arches_common/constants.ts';

import type { Ref } from 'vue';
import type { Language, User } from '@/bcgov_arches_common/types.ts';

// Admin tools (e.g. Contributor invitations). Access is enforced server-side
// by the API (IsAdminUser); this shell just hosts the routed pages.
const user = ref<User | null>(null);
const setUser = (userToSet: User | null) => {
    user.value = userToSet;
};
provide(USER_KEY, { user, setUser });

const selectedLanguage: Ref<Language> = ref(ENGLISH);
provide(selectedLanguageKey, selectedLanguage);
provide(systemLanguageKey, ENGLISH);
</script>

<template>
    <main>
        <div class="bcgov-main-content">
            <RouterView />
        </div>
    </main>
    <Toast />
</template>

<style scoped>
main {
    font-family: sans-serif;
    min-height: 100vh;
    width: 100vw;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
}
.bcgov-main-content {
    flex: auto;
    background-color: #e9e9e9;
}
</style>
