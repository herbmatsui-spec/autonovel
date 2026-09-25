import React from 'react';
import { render, screen } from '@testing-library/react';

const TestComponent = () => <div>Hello</div>;

test('tsx test', () => {
  render(<TestComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
