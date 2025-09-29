import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Streams from '../pages/Streams';

describe('Streams page', () => {
  it('lists streams from mock data', () => {
    render(
      <MemoryRouter>
        <Streams />
      </MemoryRouter>
    );
    expect(screen.getByText(/Your Streams/i)).toBeInTheDocument();
  });
});

