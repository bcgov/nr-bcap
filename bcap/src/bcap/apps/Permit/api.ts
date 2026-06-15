import arches from 'arches';
import { getCsrfToken } from '@/bcap/util.ts';
import type { ArchesDraftData } from '@/bcap/types.ts';

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

export const submitApplication = async (
    draftId: string,
    payload: ArchesDraftData,
    graphSlug: string = 'permit_application',
): Promise<boolean> => {
    try {
        const submitUrl = arches.urls.api_resource_create(graphSlug);
        const cleanPayload = JSON.parse(JSON.stringify(payload));

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

        return true;
    } catch (error) {
        console.error('Submission API failed:', error);
        throw error;
    }
};
