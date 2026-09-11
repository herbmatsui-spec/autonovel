import { test, expect } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';

const Component = () => <div>Hello</div>;

test('simple tsx test', () => {
  render(<Component />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
