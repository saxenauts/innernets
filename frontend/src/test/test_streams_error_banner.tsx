import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock API get to reject
vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockRejectedValue(new Error('HTTP 401: Unauthorized')),
  },
}));

// Mock Auth to be authed so Streams mounts
vi.mock('../state/auth', async () => {
  const React = await import('react');
  return {
    useAuth: () => ({ authed: true, ready: true }),
    AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

import Streams from '../pages/Streams';

describe('Streams error banner', () => {
  it('shows inline error when API fails (e.g., 401)', async () => {
    render(
      <MemoryRouter>
        <Streams />
      </MemoryRouter>
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(/failed to load streams/i);
  });
});
