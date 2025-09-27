import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Stub IntersectionObserver used by StreamView infinite scroll
beforeAll(() => {
  (global as any).IntersectionObserver = class {
    constructor() {}
    observe() {}
    disconnect() {}
  } as any;
});

// Mock Auth to be authed so StreamView mounts
vi.mock('../state/auth', async () => {
  const React = await import('react');
  return {
    useAuth: () => ({ authed: true, ready: true }),
    AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Stateful API mocks
const getMock = vi.fn();
const postMock = vi.fn();
vi.mock('../lib/api', () => ({
  api: {
    get: (path: string) => getMock(path),
    post: (path: string, _body?: any) => postMock(path),
    put: vi.fn(),
    del: vi.fn(),
  },
}));

import App from '../App';

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

describe('Run Now gating (disable until latest finished)', () => {
  it('disables on click when a run is in progress', async () => {
    const streamId = 'abc';
    const baseStarted = '2025-01-01T00:00:00.000Z';
    const newStarted = '2025-10-01T00:00:00.000Z';
    let latestCall = 0;

    getMock.mockImplementation(async (path: string) => {
      if (path === `/streams/${streamId}`) {
        return { id: streamId, mission: 'Test Stream', cadence: 'weekly' };
      }
      if (path === `/streams/${streamId}/runs?limit=5`) {
        return { runs: [], next_cursor: null };
      }
      if (path.startsWith(`/streams/${streamId}/latest`)) {
        latestCall += 1;
        if (latestCall === 1) {
          // Baseline: last finished run exists
          return { run_id: 'old', started_at: baseStarted, finished_at: baseStarted };
        }
        // Immediately after click: new run started but not finished
        return { run_id: 'new', started_at: newStarted, finished_at: null };
      }
      throw new Error(`Unexpected path ${path}`);
    });
    postMock.mockResolvedValue({ job_id: 'job-1', status: 'queued' });

    const u = userEvent.setup();
    render(
      <MemoryRouter initialEntries={[`/streams/${streamId}`]}>
        <App />
      </MemoryRouter>
    );

    // Button initially enabled
    const btn = await screen.findByRole('button', { name: /run now/i });
    expect(btn).toBeEnabled();

    // Click to enqueue
    await u.click(btn);
    // let state flush
    await Promise.resolve();
    await Promise.resolve();
    expect(postMock).toHaveBeenCalledWith(`/streams/${streamId}/run`);

    // Disabled after click (run in progress)
    await waitFor(() => expect(screen.getByRole('button', { name: /run now/i })).toBeDisabled());
  });

  it('re-enables once latest shows a newer finished run', async () => {
    const streamId = 'abc';
    const baseStarted = '2025-01-01T00:00:00.000Z';
    const newStarted = '2025-10-01T00:00:00.000Z';
    let latestCall = 0;

    getMock.mockImplementation(async (path: string) => {
      if (path === `/streams/${streamId}`) {
        return { id: streamId, mission: 'Test Stream', cadence: 'weekly' };
      }
      if (path === `/streams/${streamId}/runs?limit=5`) {
        return { runs: [], next_cursor: null };
      }
      if (path.startsWith(`/streams/${streamId}/latest`)) {
        latestCall += 1;
        if (latestCall === 1) {
          return { run_id: 'old', started_at: baseStarted, finished_at: baseStarted };
        }
        // Immediately after click: finished newer run
        return { run_id: 'new', started_at: newStarted, finished_at: newStarted };
      }
      throw new Error(`Unexpected path ${path}`);
    });
    postMock.mockResolvedValue({ job_id: 'job-1', status: 'queued' });

    const u = userEvent.setup();
    render(
      <MemoryRouter initialEntries={[`/streams/${streamId}`]}>
        <App />
      </MemoryRouter>
    );

    const btn = await screen.findByRole('button', { name: /run now/i });
    await u.click(btn);
    // let state flush
    await Promise.resolve();
    await Promise.resolve();

    // Eventually enabled because latest finished
    await waitFor(() => expect(screen.getByRole('button', { name: /run now/i })).toBeEnabled());
  });
});
