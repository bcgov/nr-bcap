<script setup lang="ts">
import FieldSet from 'primevue/fieldset';
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <FieldSet legend="Before you begin">
        <div class="mb-2">
            <p>Stuff you need to know</p>
        </div>

        <ul class="bullet-list ml-4">
            <li>Point 1</li>
            <li>Point 2</li>
            <li>Point 3</li>
        </ul>

        <h3 class="mb-2 font-bold mt-4">Submission Requirements</h3>

        <ul class="bullet-list ml-4">
            <li>
                Steps 2-5 and 10 are
                <i>something</i>
                to complete the basic data requirements for a notification.
            </li>
            <li>
                Information required for Steps 2-5:
                <ul class="bullet-list ml-4 mt-2">
                    <li>First thing</li>
                    <li>Second thing</li>
                    <li>
                        Third things:
                        <ul class="bullet-list-nested ml-4 mt-1">
                            <li>One</li>
                            <li>Two</li>
                        </ul>
                    </li>
                </ul>
            </li>
        </ul>
        <div class="mt-4">
            <span class="red">*</span>
            The system does not have a save for later or draft function, so it
            is important to have all information ready before starting. It is
            highly recommended to complete the remaining steps if information is
            available to improve the historic site’s search ability on the
            register.
        </div>
    </FieldSet>
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

.pdfLink {
    color: #0000ee;
    text-decoration: underline;
}
</style>
