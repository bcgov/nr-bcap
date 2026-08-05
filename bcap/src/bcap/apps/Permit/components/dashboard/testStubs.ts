import { defineComponent } from 'vue';

// Stand-in for ProjectCard so the props a dashboard computes are inspectable.
// Declares the union of what both dashboards pass; a dashboard that omits some
// simply leaves them at their defaults.
export const ProjectCardStub = defineComponent({
    name: 'ProjectCard',
    props: {
        bodyTitle: { type: String, default: '' },
        bodySubtitle1: { type: String, default: '' },
        bodySubtitle2: { type: String, default: '' },
        capLabel: { type: String, default: '' },
        capDate: { type: String, default: '' },
        capPriority: { type: Boolean, default: false },
        body1: { type: String, default: '' },
        body2: { type: String, default: '' },
        body3: { type: String, default: '' },
        footerName: { type: String, default: '' },
        footerDate: { type: String, default: '' },
        unreadMessages: { type: Number, default: 0 },
        route: { type: Object, default: () => ({}) },
    },
    template: '<div class="project-card-stub">{{ bodyTitle }}</div>',
});
