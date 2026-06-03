import { defineConfig } from "@hey-api/openapi-ts";

// Generate Zod schemas (single source of truth) from the OpenAPI spec.
// Types are derived via z.infer, so no separate type plugin.
// output.header adds a regenerated guide for mapping a schema name to its route.
export default defineConfig({
    input: "schema.yml",
    output: {
        path: "bcap/src/bcap/client",
        header: ({ defaultValue }) => [
            ...defaultValue,
            "//",
            "// Generated from the OpenAPI spec in schema.yml.",
            "// Route-bound schemas are named z<Operation><Role> -- e.g. zApiDashboardRetrieveResponse:",
            "//   Role   = Response | Query | Body | Path",
            "//   Method = verb in <Operation>: Retrieve/List=GET, Create=POST,",
            "//            Update=PUT, PartialUpdate=PATCH, Destroy=DELETE",
            "// Look up <Operation> in schema.yml `paths` for the url.",
            "// Names without an Api* prefix (e.g. zDashboardCard) are shared, route-agnostic components.",
        ],
    },
    plugins: ["zod"],
});
