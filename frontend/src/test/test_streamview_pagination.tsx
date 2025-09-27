import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Stub IntersectionObserver
beforeAll(() => {
  (global as any).IntersectionObserver = class {
    constructor() {}
    observe() {}
    disconnect() {}
  } as any;
});

// Mock Auth authed
vi.mock('../state/auth', async () => {
  const React = await import('react');
  return {
    useAuth: () => ({ authed: true, ready: true }),
    AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

const getMock = vi.fn();
vi.mock('../lib/api', () => ({
  api: {
    get: (path: string) => getMock(path),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}));

import App from '../App';

beforeEach(() => {
  getMock.mockReset();
});

describe('StreamView pagination (Load more)', () => {
  it('loads first page then appends next page on Load more; guards duplicate fetches while loading', async () => {
    const streamId = 'abc';
    const firstPage = {
      runs: [
        { id: 'r1', started_at: '2025-01-01T00:00:00Z', finished_at: '2025-01-01T00:10:00Z', curations: [{ title: 'First A', hook: 'h', links: [], position: 0 }] },
        { id: 'r2', started_at: '2025-01-02T00:00:00Z', finished_at: '2025-01-02T00:10:00Z', curations: [{ title: 'First B', hook: 'h', links: [], position: 0 }] },
      ],
      next_cursor: 'C1',
    };
    const secondPage = {
      runs: [
        { id: 'r0', started_at: '2024-12-31T00:00:00Z', finished_at: '2024-12-31T00:10:00Z', curations: [{ title: 'Second A', hook: 'h', links: [], position: 0 }] },
      ],
      next_cursor: null,
    };

    getMock.mockImplementation(async (path: string) => {
      if (path === `/streams/${streamId}`) return { id: streamId, mission: 'Test Stream', cadence: 'weekly' };
      if (path === `/streams/${streamId}/runs?limit=5`) return firstPage;
      if (path === `/streams/${streamId}/latest`) return { run_id: 'r2', started_at: '2025-01-02T00:00:00Z', finished_at: '2025-01-02T00:10:00Z' };
      if (path === `/streams/${streamId}/runs?limit=5&before=C1`) return secondPage;
      throw new Error(`Unexpected path ${path}`);
    });

    const u = userEvent.setup();
    render(
      <MemoryRouter initialEntries={[`/streams/${streamId}`]}>
        <App />
      </MemoryRouter>
    );

    // First page curations appear
    expect(await screen.findByText('First A')).toBeInTheDocument();
    expect(screen.getByText('First B')).toBeInTheDocument();

    // Click Load more twice quickly; underlying code should guard duplicate fetches
    const btn = await screen.findByRole('button', { name: /load more/i });
    await u.click(btn);
    await u.click(btn);

    // Second page curation appears
    expect(await screen.findByText('Second A')).toBeInTheDocument();

    // Ensure only one call for the second page was made
    const calls = getMock.mock.calls.filter(([p]) => p === `/streams/${streamId}/runs?limit=5&before=C1`).length;
    expect(calls).toBe(1);
  });
});

