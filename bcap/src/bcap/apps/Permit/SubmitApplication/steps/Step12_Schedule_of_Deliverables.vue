<script setup lang="ts">
import FieldSet from 'primevue/fieldset';
const isValid = () => {
    return true;
};

defineExpose({ isValid });
</script>
<template>
    <FieldSet>
        <h3>Schedule of Deliverables</h3>
        <br />
        <ul>
            <li>
                A Schedule of Deliverables ensures the permit holder is
                consistently meeting terms and conditions of the permit and
                allows First Nations and the Branch to make informed decisions.
            </li>
        </ul>
        <table>
            <thead>
                <tr>
                    <th>Deliverable</th>
                    <th>Timelines</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Site records</td>
                    <td>
                        Within eight (8) weeks of the completion of site
                        investigations, or as directed by the Branch
                    </td>
                </tr>
                <tr>
                    <td>Interim reports</td>
                    <td>
                        As required to provide management recommendations to the
                        proponent, including areas where no archaeological sites
                        were found but development is proceeding
                    </td>
                </tr>
                <tr>
                    <td>
                        Spatial files
                        <sup>1</sup>
                    </td>
                    <td>Annually, on the anniversary of permit issuance</td>
                </tr>
                <tr>
                    <td>Summary reports</td>
                    <td>Annually, on the anniversary of permit issuance</td>
                </tr>
            </tbody>
        </table>

        <ul>
            <li>
                The summary report is intended to summarise assessments (and
                results) and, when possible, indicate what further work is
                anticipated.
            </li>

            <li>
                Though First Nations or the Branch may request specific
                information in a summary report, summary reports are anticipated
                to contain:

                <ol>
                    <li>Project description(s) and location(s)</li>
                    <li>Summary of surveyed areas</li>

                    <li>
                        Brief description of sites identified or revisited
                        within the study area, including:

                        <ol type="a">
                            <li>Site function</li>
                            <li>Site dimensions</li>
                            <li>
                                Artifacts and faunal remains (e.g., nature,
                                density, counts)
                            </li>
                            <li>Significant artifacts or features</li>
                            <li>
                                Whether ancestral remains were identified and
                                their present status (i.e., have they been
                                reburied?)
                            </li>
                        </ol>
                    </li>
                    <li>Other important information</li>
                </ol>
            </li>
            <li>
                The permit holder will provide permission to the Branch to
                distribute reports to inform work conducted near the permitted
                study area.
            </li>
        </ul>
    </FieldSet>
    <br />
</template>

<style scoped>
ul,
ol {
    padding-left: 2.5rem;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
}
table {
    border-collapse: collapse;
    width: 100%;
    max-width: 800px;
    font-family: Arial, sans-serif;
    font-size: 16px;
    line-height: 1.4;
}

th,
td {
    border: 1px solid black;
    padding: 8px 12px;
    vertical-align: top;
}

th {
    background-color: #d9d9d9;
    font-weight: bold;
}

th:first-child {
    text-align: left;
    width: 30%;
}

th:last-child {
    text-align: center;
}

td:first-child {
    font-weight: bold;
}
</style>
