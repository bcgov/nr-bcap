<script setup lang="ts">
import FieldSet from 'primevue/fieldset';
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <FieldSet>
        <h3>Reference Documents</h3>
        <br />
        <a
            class="pdfLink"
            href="https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/natural-resource-use/archaeology/forms-publications/archaeological_impact_assessment_guidelines.pdf"
        >
            Arch Impact Assessment Guidelines
        </a>
        <br />
        <a
            class="pdfLink"
            href="https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/natural-resource-use/archaeology/forms-publications/site_form_mapping_and_spatial_requirements.pdf"
        >
            Mapping and Shapefile Requirements
        </a>
        <br />
        <a
            class="pdfLink"
            href="https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/natural-resource-use/archaeology/forms-publications/bulletin_26_-_archaeological_materials.pdf"
        >
            Treatment of Archaeological Materials information
        </a>
    </FieldSet>
    <br />
</template>

<style></style>
