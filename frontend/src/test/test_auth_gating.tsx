import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';

// Mock Auth module to control ready/authed
const mockUseAuth = vi.fn();
vi.mock('../state/auth', async () => {
  const React = await import('react');
  return {
    useAuth: () => mockUseAuth(),
    AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Mock API to avoid real network in Streams
vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}));

import App from '../App';

describe('Auth gating', () => {
  it('redirects to Login when not authed', async () => {
    mockUseAuth.mockReturnValue({ authed: false, ready: true });
    render(
      <MemoryRouter initialEntries={[{ pathname: '/streams' }]}>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByText(/Welcome back/i)).toBeInTheDocument();
  });

  it('renders Streams when authed', async () => {
    mockUseAuth.mockReturnValue({ authed: true, ready: true });
    render(
      <MemoryRouter initialEntries={[{ pathname: '/streams' }]}>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByText(/Your Streams/i)).toBeInTheDocument();
  });
});

