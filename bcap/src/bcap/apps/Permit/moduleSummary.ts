import DOMPurify from 'dompurify';
import type { ModuleProgress } from '@/bcap/types.ts';

// Builds the module-progress HTML shown on a dashboard card (rendered via
// v-html in ProjectCard). The summary arrives on the card, so this is a pure
// formatter -- no fetch. Empty string when the permit has no modules.
export const buildModuleSummary = (progress?: ModuleProgress): string => {
    const total = progress?.total ?? 0;
    if (total === 0) return '';
    const done = `<strong>${progress?.completed ?? 0}/${total} modules complete</strong>`;
    const current = progress?.current_module;
    const html = current ? `${done}<br>Current Module: ${current}` : done;
    // Rendered with v-html and the module name is user-entered, so the result
    // is sanitized rather than trusted.
    return DOMPurify.sanitize(html);
};
