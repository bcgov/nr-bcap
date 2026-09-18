import { computed, reactive } from 'vue';
import { defineStore } from 'pinia';
import arches from 'arches';
import { apiFetchJson } from '@/bcap/api.ts';
import { zUserProfileResponse } from '@/bcap/client/zod.gen.ts';

export type UserProfile = ReturnType<typeof zUserProfileResponse.parse>;

// The signed-in user. is_internal is the server's answer on whether to show the
// staff view, so the group that marks staff is never named here.
export const useUserStore = defineStore('bcapUser', () => {
    const state = reactive({
        profile: null as UserProfile | null,
    });

    // Kept once loaded: the route guard asks on every navigation. Nothing is
    // assigned on a failure, so the next navigation retries.
    async function load(): Promise<UserProfile | null> {
        if (state.profile) return state.profile;
        const result = zUserProfileResponse.safeParse(
            await apiFetchJson(arches.urls.api_user_profile),
        );
        if (!result.success) {
            console.warn(
                'UserProfileResponse failed validation:',
                result.error,
            );
            return null;
        }
        state.profile = result.data;
        return state.profile;
    }

    const isInternal = computed(() => state.profile?.is_internal ?? false);

    return { state, isInternal, load };
});
