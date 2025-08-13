import { createApp } from 'vue';
import ArchaeologicalSite from '@/bcap/components/pages/details/ArchaeologicalSite.vue';

// Guard against double-inclusion
if ((window as any).__BCAP_VITE_ENTRY_INSTALLED__) {
  console.warn('[BCAP] duplicate Vite entry ignored');
} else {
  (window as any).__BCAP_VITE_ENTRY_INSTALLED__ = true;

  function realMount(
    ko: any, el: HTMLElement, valueAccessor: any, allBindings: any, vm: any, ctx: any, origInit?: Function
  ) {
    const params = typeof valueAccessor === 'function' ? valueAccessor() : (valueAccessor || {});
    const props  = ko?.toJS?.(params.props || {}) ?? (params.props || {});

    const mount = document.createElement('div');
    mount.dataset.vite = 'ArchaeologicalSite';
    el.appendChild(mount);

    const app = createApp(ArchaeologicalSite, props);
    app.mount(mount);

    try { ko?.utils?.domNodeDisposal?.addDisposeCallback?.(el, () => { app.unmount(); }); } catch {}

    return { controlsDescendantBindings: true };
  }

  // install real mount + flush any queued calls
  (window as any).__bcapMountVueComponent = realMount;
  const q = (window as any).__bcap_vue_queue__ || [];
  if (q.length) {
    for (const args of q) {
      try { realMount.apply(null, args); } catch (e) { console.warn('[BCAP] queued mount failed', e); }
    }
    (window as any).__bcap_vue_queue__ = [];
  }

  // let any listeners know we’re ready (harmless if nothing listens)
  try { document.dispatchEvent(new Event('__BCAP_VITE_READY__')); } catch {}

  console.log('[BCAP] Vite entry loaded');

  if (import.meta.hot) import.meta.hot.accept();
}