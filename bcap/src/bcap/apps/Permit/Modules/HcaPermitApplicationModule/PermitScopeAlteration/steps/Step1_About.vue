<script setup lang="ts">
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <h2 class="bc-step-heading">Permit Scope — Alteration Permit</h2>
    <p class="bc-step-lede">
        Describe the scope of the proposed alteration permit, including the
        project details, affected archaeological sites, related assessments, and
        impact management approach.
    </p>

    <div class="bc-callout">
        <i class="fa-solid fa-circle-info bc-callout-icon"></i>
        <div>
            <p class="bc-callout-title">What you will need</p>
            <ul>
                <li>
                    The project location, description, and timing of planned
                    alterations.
                </li>
                <li>
                    Details of any archaeological sites that will be affected by
                    the proposed work.
                </li>
                <li>
                    Information on any related assessments, including study
                    type, associated HCA permit, and proximity to the alteration
                    area.
                </li>
                <li>
                    Your impact management approach, including any stockpile
                    plan details.
                </li>
                <li>
                    Any related concurrent HCA permits and First Nation file
                    numbers.
                </li>
            </ul>
        </div>
    </div>

    <h2 class="bc-step-heading">Section Overview</h2>

    <ol class="bc-numbered-list">
        <li>
            <strong>Project Details</strong>
            — Describe the project location, the alteration work to be
            undertaken, and the timing of planned alterations.
        </li>
        <li>
            <strong>Affected Sites</strong>
            — Identify the archaeological sites affected by the alteration and
            describe the anticipated impacts on each.
        </li>
        <li>
            <strong>Related Assessments</strong>
            — List any related archaeological assessments and provide context
            from previous assessment work.
        </li>
        <li>
            <strong>Impact Management</strong>
            — Describe how impacts will be managed, including any stockpile plan
            requirements.
        </li>
        <li>
            <strong>Permits &amp; Discussion</strong>
            — Identify any related concurrent permits, provide First Nation file
            numbers, and add any further discussion.
        </li>
    </ol>
</template>

<style>
li {
    color: unset;
    font-size: unset;
}
</style>
