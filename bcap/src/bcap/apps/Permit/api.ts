import arches from 'arches';
import { getCsrfToken } from '@/bcap/util.ts';
import type { ArchesDraftData, DraftNode } from '@/bcap/types.ts';
import { zPermitApplication } from '@/bcap/client/zod.gen.ts';
import * as z from 'zod';
import { type PermitAliasedData } from '@/bcap/util.ts';

export async function getBlankPermitApplication(): Promise<unknown> {
    const response = await fetch(
        arches.urls.api_resource_blank('permit_application') + '?format=json',
        {},
    );
    return await response.json();
}

export const fetchDrafts = async () => {
    try {
        const response = await fetch(
            arches.urls.api_resource_draft('permit_application'),
        );
        if (!response.ok) throw new Error('Network response was not ok');

        const data = await response.json();
        return data.results || data || [];
    } catch (error) {
        console.error('Failed to load drafts for dashboard:', error);
        return [];
    }
};

export const fetchMyProjects = async () => {
    try {
        const url = `${arches.urls.bcap_api_dashboard_external}?status=CREATED_BY_ME`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                Accept: 'application/json',
            },
        });

        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        return data.results || data || [];
    } catch (error) {
        console.error('Failed to load submitted projects:', error);
        return [];
    }
};

export type PermitApplicationResponse = z.infer<typeof zPermitApplication>;

export const submitApplication = async (
    draftId: string,
    payload: ArchesDraftData,
    graphSlug: string = 'permit_application',
): Promise<PermitApplicationResponse> => {
    try {
        const submitUrl = arches.urls.api_resource_create(graphSlug);
        const cleanPayload = JSON.parse(
            JSON.stringify(payload),
        ) as ArchesDraftData;
        // dummy application ID for POST
        cleanPayload.application_identification ??= {};
        cleanPayload.application_identification.aliased_data ??= {};
        cleanPayload.application_identification.aliased_data.application_id = {
            node_value: {
                en: {
                    value: 'DUMMY-APP-0000',
                    direction: 'ltr',
                },
            },
        } as unknown as DraftNode;

        // Submit the final resource
        const postResponse = await fetch(submitUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                draft_id: draftId,
                aliased_data: cleanPayload,
            }),
        });

        if (!postResponse.ok) {
            const errorDetails = await postResponse
                .json()
                .catch(() => 'No additional details provided by server.');
            console.error('Django 400 Error Details:', errorDetails);
            throw new Error(
                `Status ${postResponse.status}: ${JSON.stringify(errorDetails)}`,
            );
        }

        const finalResource = await postResponse.json();
        console.log('Final resource created successfully!', finalResource);

        // Delete the draft after successful submission
        const deleteUrl = `${arches.urls.api_resource_draft(graphSlug)}/${draftId}`;

        await fetch(deleteUrl, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': getCsrfToken() },
        });

        return finalResource;
    } catch (error) {
        console.error('Submission API failed:', error);
        throw error;
    }
};

// Fetch permit data
export const fetchPermitDetails = async (
    permitId: string,
): Promise<PermitAliasedData | null | undefined> => {
    const url = arches.urls.bcap_api_resource('permit_application', permitId);

    const response = await fetch(url, {
        method: 'GET',
        headers: { accept: 'application/json' },
    });

    if (!response.ok) throw new Error('Network response was not ok');

    const rawJson = await response.json();

    if (!rawJson || !rawJson.aliased_data) {
        console.warn('API payload did not contain aliased_data');
        return null;
    }

    return rawJson.aliased_data as PermitAliasedData;
};

// Submit permit date BROKEN I think it needs a backend fix
export const patchPermitSubmissionDate = async (
    permitId: string,
    adminPayload: {
        tileid?: string;
        aliased_data: { application_submission_date: string };
    },
): Promise<void> => {
    const url = arches.urls.bcap_api_resource('permit_application', permitId);

    const response = await fetch(url, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            accept: 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({
            aliased_data: {
                application_admin: adminPayload,
            },
        }),
    });

    if (!response.ok) {
        const errorBody = await response.text();
        console.error('🚨 DJANGO ERROR:', errorBody);
        throw new Error(`Failed to submit permit: ${response.statusText}`);
    }
};
