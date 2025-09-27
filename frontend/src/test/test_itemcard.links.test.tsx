import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import React from 'react';
import ItemCard from '../components/ItemCard';

describe('ItemCard links', () => {
  it('renders title as anchor when first link exists', () => {
    const item = {
      title: 'Example Title',
      summary: 'Example summary',
      links: [
        { label: 'Site', url: 'https://example.com' },
        { label: 'Docs', url: 'https://example.com/docs' },
      ],
    };
    render(<ItemCard item={item as any} />);
    const titleLink = screen.getByRole('link', { name: /example title/i });
    expect(titleLink).toHaveAttribute('href', 'https://example.com');
    expect(titleLink).toHaveAttribute('target', '_blank');
  });

  it('renders title as text when no links exist', () => {
    const item = {
      title: 'No Link Title',
      summary: 'Example summary',
      links: [],
    };
    render(<ItemCard item={item as any} />);
    expect(screen.queryByRole('link', { name: /no link title/i })).toBeNull();
    expect(screen.getByText('No Link Title')).toBeInTheDocument();
  });

  it('renders pill links for all links', () => {
    const item = {
      title: 'Pills',
      summary: 'Example',
      links: [
        { label: 'A', url: 'https://a.example' },
        { label: 'B', url: 'https://b.example' },
      ],
    };
    render(<ItemCard item={item as any} />);
    expect(screen.getByRole('link', { name: 'A' })).toHaveAttribute('href', 'https://a.example');
    expect(screen.getByRole('link', { name: 'B' })).toHaveAttribute('href', 'https://b.example');
  });
});
