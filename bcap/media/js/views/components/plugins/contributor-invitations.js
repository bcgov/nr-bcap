import registerVuePlugin from 'utils/register-vue-plugin';
import BCAPAdminApp from '@/bcap/apps/Admin/App.vue';
import { routes } from '@/bcap/apps/Admin/routes.ts';
import { BCGovPreset } from '@/bcap/primevue-bcgov-preset.ts';
import contributorInvitationsTemplate from 'templates/views/components/plugins/contributor-invitations.htm';

registerVuePlugin('contributor-invitations', {
    component: BCAPAdminApp,
    routes,
    preset: BCGovPreset,
    mountPoint: '#contributor-invitations-mounting-point',
    template: contributorInvitationsTemplate,
});
