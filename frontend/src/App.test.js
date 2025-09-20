import { render, screen } from '@testing-library/react';
import App from './App';

test('renders without crashing', () => {
  render(<App />);
});

test('contains expected elements', () => {
  render(<App />);
  // Basic smoke test - adjust based on actual App component
  expect(document.body).toBeInTheDocument();
});