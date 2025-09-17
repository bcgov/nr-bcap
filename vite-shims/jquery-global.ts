const g: any = typeof window !== "undefined" ? window : globalThis;
let jq: any = g.jQuery || g.$;
if (!jq) {
    await import("/@fs/web_root/bcap/node_modules/jquery/dist/jquery.js");
    jq = g.jQuery || g.$;
    if (!jq) throw new Error("[jquery-shim] Failed to initialize jQuery.");
}
g.$ = g.$ || jq;
g.jQuery = g.jQuery || jq;
export default jq;
export const jQuery = jq;
export const $ = jq;
