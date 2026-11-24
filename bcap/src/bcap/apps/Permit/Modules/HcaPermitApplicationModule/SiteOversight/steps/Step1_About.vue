<script setup lang="ts">
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <h2 class="bc-step-heading">Personnel & Site Oversight</h2>
    <p class="bc-step-lede">
        Identify the personnel responsible for directing and overseeing the
        archaeological work, and assign oversight responsibilities by cultural
        area.
    </p>

    <div class="bc-callout">
        <i class="fa-solid fa-circle-info bc-callout-icon"></i>
        <div>
            <p class="bc-callout-title">What you will need</p>
            <ul>
                <li>
                    The name and role of the directing archaeologist, or details
                    of applicant responsibility if no directing archaeologist
                    will be engaged.
                </li>
                <li>
                    For each cultural area covered by the permit, the name of
                    the responsible person and their role.
                </li>
            </ul>
        </div>
    </div>

    <h2 class="bc-step-heading">Section Overview</h2>

    <ol class="bc-numbered-list">
        <li>
            <strong>Personnel</strong>
            — Indicate whether a directing archaeologist will be engaged and
            provide the relevant details.
        </li>
        <li>
            <strong>Assessment Oversight</strong>
            — Select each cultural area covered by the permit and assign a
            responsible person and role for each.
        </li>
    </ol>
</template>

<style>
li {
    color: unset;
    font-size: unset;
}
</style>
