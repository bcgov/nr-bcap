import { computed, reactive } from 'vue';
import { defineStore } from 'pinia';
import arches from 'arches';
import { apiFetchJson } from '@/bcap/api.ts';
import { zUserResponse } from '@/bcap/client/zod.gen.ts';
import type { UserResponse } from '@/bcap/client/types.gen.ts';

// The signed-in user. Ministry staff are superusers or members of Archaeology
// Branch; every other group authorizes a function rather than the staff view.
const ARCHAEOLOGY_BRANCH = 'Archaeology Branch';

export const useUserStore = defineStore('bcapUser', () => {
    const state = reactive({
        profile: null as UserResponse | null,
    });

    // Kept once loaded: the route guard asks on every navigation. Nothing is
    // assigned on a failure, so the next navigation retries.
    async function fetchUser(): Promise<UserResponse | null> {
        if (state.profile) return state.profile;
        const result = zUserResponse.safeParse(
            await apiFetchJson(arches.urls.api_user),
        );
        if (!result.success) {
            console.warn('UserResponse failed validation:', result.error);
            return null;
        }
        state.profile = result.data;
        return state.profile;
    }

    const isInternal = computed(
        () =>
            !!state.profile &&
            (state.profile.is_superuser ||
                ARCHAEOLOGY_BRANCH in state.profile.groups),
    );

    return { state, isInternal, fetchUser };
});
