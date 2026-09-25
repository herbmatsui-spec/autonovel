import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

const SimpleComponent = () => <div>Hello World</div>;

describe('SimpleComponent', () => {
  it('renders hello world', () => {
    render(<SimpleComponent />);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });
});
