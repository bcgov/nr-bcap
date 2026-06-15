import arches from 'arches';
//import type { PermitApplication } from '@/bcap/schema/';

export async function getBlankPermitApplication(): Promise<unknown> {
    const response = await fetch(
        arches.urls.api_resource_blank('permit_application') + '?format=json',
        {},
    );
    return await response.json();
}
