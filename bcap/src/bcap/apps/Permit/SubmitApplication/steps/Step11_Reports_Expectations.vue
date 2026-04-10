<script setup lang="ts">
import FieldSet from 'primevue/fieldset';
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <FieldSet>
        <h3>Reports</h3>
        <br />
        <ol>
            <li>Permit report titles must include the HCA permit number.</li>
            <li>Reports must include a distribution list.</li>
            <li>
                Permit report citations in the References sections of reports
                must include the relevant HCA permit number.
            </li>
            <li>
                Final Reports are expected to comply with Provincial Guidelines
                (Archaeological Impact Assessment Guidelines)
            </li>
            <li>
                Interim Reports submitted under this permit and are expected to
                comply with Provincial guidance (Interim Permit Reporting
                Policy).
            </li>
            <li>
                Management summaries and recommendations must clearly outline
                the proponent’s responsibilities under the HCA and make
                recommendations for further study (as appropriate).
            </li>
            <li>
                Reports must describe how pre-field background research
                influenced the study.
            </li>
            <li>
                Reports must contain detailed descriptions of every part of each
                proposed development area assessed, in terms of the criteria
                used to evaluate archaeological potential, and why the field
                director chose specific in-field methods (e.g., survey transect
                spacing; subsurface testing density). This includes all proposed
                development areas that are inspected in the field, as well as
                those development areas reviewed solely through map and document
                review if the permit would have authorized field inspection of
                those developments.
            </li>
            <li>
                A summary description of each site recorded or revisited must be
                included in the report, including a synthesis of previous
                archaeological work relating to the site.
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
