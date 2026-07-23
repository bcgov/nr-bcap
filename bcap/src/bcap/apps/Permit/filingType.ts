// The permit application's filing_type reference labels, as seeded from
// pkg/reference_data/skos/filing_type.xml. Values must match the list item
// labels exactly -- they arrive on the resource as display_value.
export enum FilingType {
    PermitApplicationStandard = 'Permit Application - Standard',
    PermitApplicationEmergency = 'Permit Application - Emergency',
    PermitApplicationMultiProject = 'Permit Application - Multi Project',
    ZoneAddition = 'Zone Addition',
    SiteVisit = 'Site Visit',
    DocumentSubmission = 'Document Submission',
    InformationRequest = 'Information Request',
}
