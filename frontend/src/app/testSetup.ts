import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach } from 'vitest';

beforeEach(() => {
  localStorage.setItem('dm_assistant_access_token', 'test-token');
});

afterEach(() => {
  localStorage.clear();
});
