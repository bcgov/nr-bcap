import { apiFetch, ApiError, UNEXPECTED_ERROR } from './api';

describe('apiFetch', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('attaches CSRF + JSON headers and serializes the body on writes', async () => {
        document.cookie = 'csrftoken=tok-123';
        const fetchMock = vi.fn().mockResolvedValue({ ok: true });
        vi.stubGlobal('fetch', fetchMock);

        await apiFetch('/x', { method: 'POST', body: { a: 1 } });

        expect(fetchMock).toHaveBeenCalledWith('/x', {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'X-CSRFToken': 'tok-123',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ a: 1 }),
        });
    });

    it('defaults to GET with no body and no Content-Type', async () => {
        const fetchMock = vi.fn().mockResolvedValue({ ok: true });
        vi.stubGlobal('fetch', fetchMock);

        await apiFetch('/y');

        const [, init] = fetchMock.mock.calls[0];
        expect(init.method).toBe('GET');
        expect(init.body).toBeUndefined();
        expect(init.headers).not.toHaveProperty('Content-Type');
    });

    const failWith = (status: number, body: string) => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                status,
                text: vi.fn().mockResolvedValue(body),
            }),
        );
        return apiFetch('/z', { method: 'PATCH', body: {} });
    };

    it('throws an ApiError carrying the status', async () => {
        const error = await failWith(400, '{"detail": "Bad input."}').catch(
            (e) => e,
        );
        expect(error).toBeInstanceOf(ApiError);
        expect(error.status).toBe(400);
        expect(error.message).toBe('Bad input.');
    });

    it('flattens DRF field errors into one message per line', async () => {
        await expect(
            failWith(
                400,
                JSON.stringify({
                    submission_type: ['Submission Type is required.'],
                    new_contributor: { email: ['Enter a valid email.'] },
                }),
            ),
        ).rejects.toThrow('Submission Type is required.\nEnter a valid email.');
    });

    it('shows a message repeated under several fields once', async () => {
        const missing =
            'This card requires values for the following: Name, Number';
        const error = await failWith(
            400,
            JSON.stringify({ name: [missing], number: [missing] }),
        ).catch((e) => e);
        expect(error.message).toBe(missing);
    });

    it('never shows a non-JSON body such as a debug page', async () => {
        await expect(
            failWith(
                500,
                '<html>ValidationError at /bcap/api Traceback</html>',
            ),
        ).rejects.toThrow(UNEXPECTED_ERROR);
    });

    it('falls back by status when the body carries no message', async () => {
        await expect(failWith(403, '')).rejects.toThrow(
            "You don't have access to do that.",
        );
        await expect(failWith(404, '{}')).rejects.toThrow(
            'That item could not be found.',
        );
    });
});
