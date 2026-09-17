"""Graph ids, for the places that cannot resolve a slug.

Turning a slug into an id costs a query, and the permission defaults are read
at import, before any database is reachable. Kept beside the slugs rather than
in them so the two stay one-to-one.
"""


class GraphIds:
    ALTERATION = "b2901f47-bdfc-47bb-b212-3132b96efb0a"
    ARCHAEOLOGICAL_SITE = "cef9c510-e3e6-4057-ac08-89ad926180b4"
    BCAP_MESSAGE = "fef4e675-e4c8-4bea-9e8a-cb30c3978bef"
    CONTRIBUTOR = "605b0bbc-8661-4cf2-b340-df743a8c5f89"
    DOCUMENT_SUBMISSION = "010b893e-c9d2-4dfe-b5d1-837c49c2bb9a"
    HCA_PERMIT = "f4b391f1-79d1-4886-ab2d-d72a197a9f21"
    HRIA_DISCONTINUED_DATA = "19806d98-8200-45b4-9f5d-9f07d9a9aaa1"
    INFORMATION_REQUEST = "d4f514eb-bdc6-4f68-9c27-92883e1d4e7d"
    INSPECTION = "87968032-6faa-481b-a47c-30f9747acd52"
    INVESTIGATION = "febca6ba-2a51-494f-9809-c54e2dd42fc3"
    LEGISLATIVE_ACT = "52dd40f2-1dee-45d2-b72c-234c8cbb5418"
    LG_PERSON = "412444dd-b13f-4289-9f04-5c7f1878ad4e"
    LOCAL_GOVERNMENT = "aacf8bb6-3f6e-46d9-a551-b0749d7efffc"
    NOTICE_OF_PROJECT_INTENT = "6ca13de7-f5b3-4e38-a947-64eaf2a04b65"
    PERMIT_APPLICATION = "5c900e2b-257c-4af3-b67f-b5caf3850f71"
    PROCESS_REQUIREMENT = "0e74b1fa-1da4-4f17-9e65-dd79fbc96313"
    PROJECT_SANDBOX = "c3923080-d21e-42d7-b8f1-637b9d0ab63c"
    PUBLICATION = "3caf329f-b8f7-11e6-84a5-026d961c88e6"
    REPOSITORY = "3e6a2880-14d4-11ec-9df0-5254008afee6"
    SITE_SUBMISSION = "4e69d0a9-7af2-473f-929f-71d462ea32d1"
    SITE_VISIT = "2da1c15f-1ab6-4122-9dbc-d10da693ac79"
    WORKFLOW_DRAFTS = "fb6a3fbf-070d-43ae-b52c-0d1bfb78f206"
