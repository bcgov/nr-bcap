<script setup lang="ts">
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <h2 class="bc-step-heading">Permit Scope — Heritage Inspection Permit</h2>
    <p class="bc-step-lede">
        Describe the scope of the proposed Heritage Inspection Permit, including
        the development(s) to be assessed, relevant archaeological studies, and
        any proposed alterations to recorded archaeological sites.
    </p>

    <div class="bc-callout">
        <i class="fa-solid fa-circle-info bc-callout-icon"></i>
        <div>
            <p class="bc-callout-title">What you will need</p>
            <ul>
                <li>The type of project and its goals and objectives.</li>
                <li>
                    Details of the proposed assessment area (size in ha for
                    single development applications, or MAP scope if
                    applicable).
                </li>
                <li>
                    Information on any previously recorded archaeological sites
                    and relevant prior studies within or near the permit area.
                </li>
                <li>
                    Details of any proposed alterations to recorded
                    archaeological sites, and any First Nation file numbers.
                </li>
            </ul>
        </div>
    </div>

    <h2 class="bc-step-heading">Section Overview</h2>

    <ol class="bc-numbered-list">
        <li>
            <strong>Proposed Development</strong>
            — Identify the project type, goals and objectives, assessment area
            size, and whether chance finds provisions apply (s. 2.1).
        </li>
        <li>
            <strong>Objectives</strong>
            — Confirm that the HIP objectives align with Appendix A and describe
            any additional objectives (s. 2.2).
        </li>
        <li>
            <strong>Archaeological Studies</strong>
            — Identify relevant prior studies and previously recorded
            archaeological sites near the permit area (s. 2.3).
        </li>
        <li>
            <strong>Alterations &amp; Discussion</strong>
            — Describe any proposed alterations to recorded sites, provide First
            Nation file numbers, and add any further discussion (s. 2.4–2.5).
        </li>
    </ol>
</template>

<style>
li {
    color: unset;
    font-size: unset;
}
</style>
