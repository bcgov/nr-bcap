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
            "//",
            "// Field suffixes mirror the spec's `required` + `nullable`:",
            "//   .nullable()  value may be null, but the field is still present",
            "//   .optional()  field may be absent (undefined), but never null",
            "//   .nullish()   both: null OR absent  (nullable + not required)",
            "//",
            "// zFoo vs zFooWritable: a component reused as BOTH a response and a",
            "// request body splits in two when it has readOnly fields.",
            "//   zFoo          response shape -- every field, incl. readOnly ones",
            "//   zFooWritable  request-body shape -- readOnly fields dropped",
            "//                 (e.g. display_value, details, name, descriptors)",
            "// Parse responses with zFoo; build request bodies with zFooWritable.",
        ],
    },
    plugins: ["zod"],
});
