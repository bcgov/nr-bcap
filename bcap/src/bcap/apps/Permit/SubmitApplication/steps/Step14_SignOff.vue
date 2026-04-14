<script setup lang="ts">
import { ref } from 'vue';
import GenericWidget from '@/arches_component_lab/generics/GenericWidget/GenericWidget.vue';
import { EDIT, VIEW } from '@/arches_component_lab/widgets/constants.ts';
import FieldSet from 'primevue/fieldset';
import type { AliasedNodeData } from '@/arches_component_lab/types.ts';
import { currentDateValue } from '@/bcap/util.ts';

const isValid = () => {
    return true;
};

const updateValue = (newValue: AliasedNodeData, attribute_name: string) => {
    console.log(newValue, attribute_name);
};

const isConsented = ref(false);
const timeOfConsentData = ref<AliasedNodeData | null>(null);

const handleConsent = () => {
    if (isConsented.value) {
        const now = currentDateValue() as unknown as AliasedNodeData;
        timeOfConsentData.value = now;
        updateValue(now, 'time_of_consent');
    } else {
        timeOfConsentData.value = null;
        updateValue(null as unknown as AliasedNodeData, 'time_of_consent');
    }
};

defineExpose({ isValid });
</script>
<template>
    <FieldSet>
        <h3>Additional Information:</h3>
        <br />
        <p>
            I certify that I am familiar with the provisions of the Heritage
            Conservation Act, RSBC 1996, c.187 (the “HCA”), of British Columbia,
            and that I will abide by the terms and conditions listed herein, and
            any other conditions the minister may impose, as empowered by s.
            HCA.
        </p>
        <p>PERSONAL INFORMATION</p>
        <p>
            Personal information, including names, addresses, telephone numbers,
            and email addresses, may be collected by the Archaeology Branch (the
            “Branch”) in permit applications, site inventory forms, and/ or
            permit reports under s.26(a) of the Freedom of Information and
            Protection of Privacy Act, RSBC 1996, c. 165 (“FOIPPA”) and
            s.12.4(2) of the HCA. Such personal information is collected for the
            purpose of this permit application and any resulting permit,
            including making archaeological information collected under that
            permit available to approved parties through the Provincial
            Archaeological Report Library (“PARL”). The collection, protection,
            retention, use, and disclosure of personal information by the Branch
            is subject to FOIPPA. Questions regarding the collection, use and
            disclosure of personal information can be directed to
            <a
                class="emailLink"
                href="mailto:archaeology@gov.bc.ca"
            >
                archaeology@gov.bc.ca
            </a>
        </p>
        <p>COPYRIGHT</p>
        <p>
            When submitting any permit deliverables, including site records,
            spatial data, interim reports, summary reports, specialized
            analysis, or final reports (each, a “Deliverable”), a “License
            Grant” signed by an authorized person (the "Grantor”) must also be
            provided. The License Grant confirms how the Deliverable may be
            used, reproduced and distributed by the Province and others (the
            “License”), enabling valuable data, including archaeological data
            contained in the Deliverables, to be used in the protection of
            heritage resources across British Columbia. For clarity, the License
            does not alter the original owner’s (or owners’) retention of
            copyright in the Deliverables. It is the Grantor’s responsibility to
            ensure that it either owns the copyright in all elements of each
            Deliverable, or has obtained all necessary rights to be able to
            grant the License, before the Deliverable is submitted. The Grantor
            will be liable for any costs arising from a failure to have the
            rights necessary for it to grant the License. The Province has
            established appropriate limitations regarding how the Deliverable
            materials may be used and with whom they may be shared. The License
            Grant also creates conditions that must be followed in relation to
            the Province’s disclosure of Indigenous cultural or other sensitive
            information contained in the Deliverables. A copy of the License
            Grant (as may be amended by the Province from time to time) is
            maintained on the Branch’s website.
        </p>
        <p>
            Additional conditions may be added to the s. 12.2 Heritage
            Inspection Permit (“HIP”). As of April 29, 2025, the following are
            the standard terms and conditions applied to HIPs issued under
            Section 12.2 of the Heritage Conservation Act (“HCA”), as
            administered by the Archaeology Branch (the “Branch”):
        </p>
        <ul class="bullet-list ml-4">
            <li>
                Permits shall be valid for the term stipulated on the front of
                the permit unless otherwise suspended or cancelled. Extensions
                to the term of the permit, or other amendments, will be
                considered upon submitting a written request to the Branch at
                least 45 days prior to the expiry date of the permit.
            </li>
            <li>
                The permit holder shall conduct the inspection as described in
                the permit application, unless otherwise specified in the
                permit.
            </li>
            <li>
                A HIP issued under the HCA does not authorize entry onto land or
                into a building without the permission of the owner or occupier.
            </li>
            <li>
                Upon completion of any excavations, the permit holder shall make
                reasonable efforts to ensure all sites are restored as closely
                as possible to their former condition.
            </li>
            <li>
                The permit holder shall arrange for a secure repository to
                curate any materials recovered under authority of the permit.
                Provisions with respect to the "Repository and Curation” section
                shall remain and continue in full force and effect in
                perpetuity, even if the permit is inactive or terminated.
            </li>
            <li>
                Heritage objects and associated materials recovered under
                authority of the permit may not be sold or exchanged for
                financial gain. Any other transfer of heritage objects,
                materials and records, or changes to the conditions identified
                in the permit, may only be carried out with prior consent of the
                minister in writing.
            </li>
            <li>
                The permit holder shall utilize any site recording forms,
                formats or systems required by the minister. To fulfill this
                condition, the site form, mapping, and related documentation
                must comply with Branch directives for site record submission.
                Failure to submit satisfactory site records or reports will be
                considered an outstanding obligation, thereby affecting the
                archaeologists’ ability to hold additional permits.
            </li>
            <li>
                The permit-holder shall provide the Branch with one (1)
                electronic copy in PDF format of a written report, in accordance
                with the standards required by the minister, outlining the work
                carried out under the terms of the permit. The title page of all
                reports must indicate the HCA permit number, and name(s) of the
                copyright owner(s) and, include a Grant of License statement
                completed and signed by the copyright owner(s). The Branch may
                require a hard copy of the report upon request.
            </li>
            <li>
                The permit holder shall submit spatial information in accordance
                with the standards required by the minister of all study areas,
                areas of potential, and negative subsurface test locations that
                were the subject of in-field inspections.
            </li>
            <li>
                The Branch may independently conduct quantitative analysis,
                using assumptions based on expected site type information (site
                area and artifact density) and test location information (tested
                area, individual test size, number of tests).
            </li>
            <li>
                Where known, First Nation file numbers will be referenced in
                permit-related correspondence.
            </li>
            <li>
                As copyright owner, the permit holder will provide affected
                First Nations with electronic copies of any site records and
                reports produced under the permit, unless the parties have
                agreed to alternate arrangements.
            </li>
        </ul>
        <div class="checkboxContainer">
            <input
                type="checkbox"
                v-model="isConsented"
                @change="handleConsent"
                style="width: 18px; height: 18px; margin-top: -5px"
            />
            <label style="font-weight: bold">
                I certify that I have read and agree to the terms and conditions
                above.
            </label>
        </div>
        <div v-if="timeOfConsentData">
            <GenericWidget
                :mode="VIEW"
                :aliased-node-data="timeOfConsentData"
                graph-slug="permit_application"
                node-alias="time_of_consent"
                @update:value="updateValue($event, 'time_of_consent')"
            />
        </div>
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="copyright_authorization"
            @update:value="updateValue($event, 'copyright_authorization')"
        />
        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="grant_of_license_to_ministry"
            @update:value="updateValue($event, 'grant_of_license_to_ministry')"
        />

        <GenericWidget
            :mode="EDIT"
            :aliased-node-data="null"
            graph-slug="permit_application"
            node-alias="applicant_name"
            @update:value="updateValue($event, 'applicant_name')"
        />
    </FieldSet>
    <br />
</template>

<style>
.checkboxContainer {
    display: flex;
    align-items: center;
    gap: 10px;
}
</style>
