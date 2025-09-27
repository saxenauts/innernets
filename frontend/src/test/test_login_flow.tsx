import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock Auth
const mockSignIn = vi.fn();
vi.mock('../state/auth', async () => {
  const React = await import('react');
  return {
    useAuth: () => ({ authed: false, ready: true, signIn: mockSignIn }),
    AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

import Login from '../pages/Login';

beforeEach(() => {
  mockNavigate.mockReset();
});

describe('Login flow', () => {
  it('signs in and navigates to /streams', async () => {
    mockSignIn.mockResolvedValueOnce(undefined);
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    await u.type(screen.getByPlaceholderText(/you@example.com/i), 'a@b.com');
    await u.type(screen.getByPlaceholderText(/•/i), 'passw0rd');
    await u.click(screen.getByRole('button', { name: /sign in/i }));
    expect(mockSignIn).toHaveBeenCalledWith('a@b.com', 'passw0rd');
    expect(mockNavigate).toHaveBeenCalledWith('/streams');
  });

  it('shows error on sign-in failure', async () => {
    mockSignIn.mockRejectedValueOnce(new Error('Invalid credentials'));
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    await u.type(screen.getByPlaceholderText(/you@example.com/i), 'x@y.com');
    await u.type(screen.getByPlaceholderText(/•/i), 'bad');
    await u.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid credentials/i);
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
