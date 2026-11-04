import registerVuePlugin from 'utils/register-vue-plugin';
import BCAPPermitApp from '@/bcap/apps/Permit/App.vue';
import { routes } from '@/bcap/apps/Permit/routes.ts';
import { BCGovPermitPreset } from '@/bcap/primevue-bcgov-preset.ts';
import internalDashboardTemplate from 'templates/views/components/plugins/internal-permit-dashboard.htm';

registerVuePlugin('internal-permit-dashboard', {
    component: BCAPPermitApp,
    routes,
    preset: BCGovPermitPreset,
    mountPoint: '#internal-dashboard-mounting-point',
    template: internalDashboardTemplate,
});
