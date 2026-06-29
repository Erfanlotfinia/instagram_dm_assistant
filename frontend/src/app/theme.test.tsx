import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import React from 'react';

import { ThemeToggle } from '../components/shell/ThemeToggle';
import { Button } from '../components/ui/Button';
import { themeStore } from '../stores/themeStore';
describe('Modira theme', () => {
  beforeEach(() => {
    localStorage.clear();
    themeStore.setPreference('light');
  });

  afterEach(() => {
    themeStore.setPreference('system');
  });

  it('sets data-theme on document when preference changes', () => {
    themeStore.setPreference('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    themeStore.setPreference('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('resolves system preference to light or dark', () => {
    themeStore.setPreference('light');
    expect(themeStore.getResolved()).toBe('light');

    themeStore.setPreference('dark');
    expect(themeStore.getResolved()).toBe('dark');
  });

  it('cycles theme preference via ThemeToggle', () => {
    themeStore.setPreference('light');
    render(<ThemeToggle />);

    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }));
    expect(themeStore.getPreference()).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');

    fireEvent.click(screen.getByRole('button', { name: 'Switch to system theme' }));
    expect(themeStore.getPreference()).toBe('system');

    fireEvent.click(screen.getByRole('button', { name: 'Switch to light theme' }));
    expect(themeStore.getPreference()).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('renders primary button with Modira semantic utility classes', () => {
    render(<Button>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button.className).toContain('bg-accent');
    expect(button.className).toContain('text-accent-fg');
    expect(button.className).toContain('hover:bg-accent-hover');
  });
});
