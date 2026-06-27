import { z } from 'zod';
import { zApiHcaPermitListResponse } from '@/bcap/client/zod.gen.ts';

export type zApiHcaPermitListResponseType = z.infer<
    typeof zApiHcaPermitListResponse
>;
