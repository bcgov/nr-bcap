import { apiFetch } from './api';

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

    it('throws with status and body text on a non-2xx response', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                status: 400,
                text: vi.fn().mockResolvedValue('bad input'),
            }),
        );

        await expect(
            apiFetch('/z', { method: 'PATCH', body: {} }),
        ).rejects.toThrow('PATCH /z failed (400): bad input');
    });
});
