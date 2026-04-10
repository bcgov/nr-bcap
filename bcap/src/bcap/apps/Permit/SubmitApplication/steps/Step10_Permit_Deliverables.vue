<script setup lang="ts">
import FieldSet from 'primevue/fieldset';
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <FieldSet>
        <h3>Permit Deliverables</h3>
        <br />
        <ul class="bullet-list ml-4">
            <li>
                Permit deliverables are expected to comply with Branch
                standards, including Archaeological Impact Assessment
                Guidelines, the Interim Reporting Policy, and
            </li>
            <li>Site Form, Mapping, and Spatial Requirements.</li>
            <li>Permit deliverables submitted to the Branch include:</li>
        </ul>
        <br />
        <ol>
            <li>
                Site records (sent to
                <a
                    class="emailLink"
                    href="mailto:archsiteform@gov.bc.ca"
                >
                    archsiteform@gov.bc.ca
                </a>
                ) a. Artifact Catalogues, Faunal Analysis Reports, & Dating Lab
                Reports may be submitted at a later date, but no later than the
                deliverables due date noted in the permit unless otherwise
                approved by the Branch. PDF of Final Report uploaded via the
                Branch’s permit application system, Archaeology Permit Tracking
                System (APTS) Hardcopies of reports will be submitted to the
                Branch on request. When applicable, interims, specialized
                analyses (e.g., radiocarbon dating), and Notice of Intent
                (“NoI”) summaries (as defined in the Multi-Assessment Permit
                Policy) will be appended to reports
            </li>
            <li>
                Spatial files for study areas, Subsurface Test Areas (“STAs”),
                and Areas of Potential (“AOPs”) (sent to
                <a
                    class="emailLink"
                    href="mailto:archpermitspatial@gov.bc.ca"
                >
                    archpermitspatial@gov.bc.ca
                </a>
                )
            </li>
            <li>
                Confirmation of acceptance from the repository uploaded via the
                Branch’s permit application system.
            </li>
            <li>Grant of license.</li>
            <li>
                The permit holder will provide First Nations with reports. Other
                data (e.g., spatial files; site forms; photographs) will be
                provided upon request.
                <ul class="bullet-list ml-4">
                    <li>
                        The permit report and site form(s) will identify the
                        repository.
                    </li>
                    <li>
                        Site information described in reports must precisely
                        match provincial site records (e.g., boundaries,
                        recovered materials).
                    </li>
                </ul>
            </li>
            <li>
                a. b. 24 S. 12.2 Heritage Inspection Permit – Terms and
                Conditions Last Updated: April 11, 2025
                <ul class="bullet-list ml-4">
                    <li>
                        When there is a discrepancy between the site record
                        following fieldwork and what is available via Remote
                        Access to Archaeological Data (“RAAD”) the approach to
                        resolve the discrepancy will be confirmed by the Branch.
                    </li>
                    <li>
                        Photographs of diagnostic artifacts, formed tools, and
                        rock art must be included in the site record.
                    </li>
                    <li>
                        With large sample sizes, a permit report may include
                        only a selection of photographs.
                    </li>
                    <li>
                        The site record and report may be redacted prior to
                        distribution via the RAAD and the Provincial
                        Archaeologica
                    </li>
                </ul>
            </li>
        </ol>
    </FieldSet>
    <br />
</template>

<style>
li {
    color: unset;
    font-size: unset;
}

.bullet-list {
    list-style-type: disc;
    padding-left: 1.5rem;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}

.bullet-list-nested {
    list-style-type: circle;
    padding-left: 2rem;
    margin-top: 0.25rem;
}

.emailLink {
    color: #0000ee;
    text-decoration: underline;
}
</style>
