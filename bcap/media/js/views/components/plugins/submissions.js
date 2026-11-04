import registerVuePlugin from 'utils/register-vue-plugin';
import BCAPPermitApp from '@/bcap/apps/Permit/App.vue';
import { routes } from '@/bcap/apps/Permit/routes.ts';
import { BCGovPermitPreset } from '@/bcap/primevue-bcgov-preset.ts';
import defaultInitWorkflowTemplate from 'templates/views/components/plugins/submissions.htm';

registerVuePlugin('submissions', {
    component: BCAPPermitApp,
    routes,
    preset: BCGovPermitPreset,
    mountPoint: '#bcap-mounting-point',
    template: defaultInitWorkflowTemplate,
});
