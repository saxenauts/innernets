import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock Auth
const mockSignUp = vi.fn();
vi.mock('../state/auth', async () => {
  const React = await import('react');
  return {
    useAuth: () => ({ authed: false, ready: true, signUp: mockSignUp }),
    AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

import SignUp from '../pages/SignUp';

import { beforeEach } from 'vitest';

beforeEach(() => {
  mockNavigate.mockReset();
});

describe('SignUp flow', () => {
  it('navigates to onboarding when a session is created (confirmation disabled)', async () => {
    mockSignUp.mockResolvedValueOnce({ hasSession: true });
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <SignUp />
      </MemoryRouter>
    );
    await u.type(screen.getByPlaceholderText(/you@example.com/i), 'a@b.com');
    await u.type(screen.getByPlaceholderText(/•/i), 'passw0rd');
    await u.click(screen.getByRole('button', { name: /sign up/i }));
    expect(mockSignUp).toHaveBeenCalledWith('a@b.com', 'passw0rd');
    expect(mockNavigate).toHaveBeenCalledWith('/onboarding');
  });

  it('shows check-email message when session is not created (confirmation enabled)', async () => {
    mockSignUp.mockResolvedValueOnce({ hasSession: false });
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <SignUp />
      </MemoryRouter>
    );
    await u.type(screen.getByPlaceholderText(/you@example.com/i), 'x@y.com');
    await u.type(screen.getByPlaceholderText(/•/i), 'passw0rd');
    await u.click(screen.getByRole('button', { name: /sign up/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/check your email/i);
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
