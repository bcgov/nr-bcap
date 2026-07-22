<script setup lang="ts">
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <h2 class="bc-step-heading">Before you begin</h2>
    <p class="bc-step-lede">
        Review the requirements below so your submission goes through without
        delays.
    </p>

    <div class="bc-callout">
        <i class="fa-solid fa-circle-info bc-callout-icon"></i>
        <div>
            <p class="bc-callout-title">Stuff you need to know</p>
            <ul>
                <li>Point 1</li>
                <li>Point 2</li>
                <li>Point 3</li>
            </ul>
        </div>
    </div>

    <h2 class="bc-step-heading">Submission Requirements</h2>

    <ol class="bc-numbered-list">
        <li>
            Steps 2-5 and 10 are
            <i>required</i>
            to complete the basic data requirements for a notification.
        </li>
        <li>
            <div>
                Information required for Steps 2-5:
                <ul class="bc-pill-list">
                    <li>First thing</li>
                    <li>Second thing</li>
                    <li>Third things</li>
                </ul>
            </div>
        </li>
    </ol>
</template>

<style>
li {
    color: unset;
    font-size: unset;
}

.emailLink {
    color: #0000ee;
    text-decoration: underline;
}

.pdfLink {
    color: #0000ee;
    text-decoration: underline;
}
</style>
