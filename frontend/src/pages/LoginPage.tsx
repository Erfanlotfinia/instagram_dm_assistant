import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Navigate, useLocation } from 'react-router-dom';
import { z } from 'zod';

import { Icons } from '../components/icons';
import { ThemeToggle } from '../components/shell/ThemeToggle';
import { Button, Card, CardBody, Field, Input, StatusBanner } from '../components/ui';
import { useAuth } from '../contexts/AuthContext';
import { cn } from '../lib/cn';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

function LoginSpinner() {
  return (
    <span
      className="h-4 w-4 animate-spin rounded-full border-2 border-accent-fg/30 border-t-accent-fg"
      aria-hidden="true"
    />
  );
}

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: import.meta.env.DEV ? 'admin@example.com' : '',
      password: import.meta.env.DEV ? 'changeme123' : '',
    },
  });

  const redirectTo =
    (location.state as { from?: string } | null)?.from && (location.state as { from?: string }).from !== '/login'
      ? (location.state as { from: string }).from
      : '/';

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  async function onSubmit(values: LoginFormValues) {
    try {
      await login(values.email, values.password);
    } catch (err) {
      setError('root', {
        message: err instanceof Error ? err.message : 'Login failed',
      });
    }
  }

  return (
    <main className="relative flex min-h-screen flex-col bg-canvas">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute -left-24 top-0 h-80 w-80 rounded-full bg-accent/10 blur-3xl" />
        <div className="absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-accent/5 blur-3xl" />
      </div>

      <header className="relative z-10 flex justify-end p-4 sm:p-6">
        <ThemeToggle />
      </header>

      <div className="relative z-10 flex flex-1 items-center justify-center px-4 pb-12 sm:px-6">
        <Card
          className="w-full max-w-[420px] overflow-hidden shadow-[0_20px_45px_rgba(15,23,42,0.08)] dark:shadow-[0_20px_45px_rgba(0,0,0,0.35)]"
          aria-labelledby="login-heading"
        >
          <div className="border-b border-border bg-gradient-to-br from-accent-soft/80 to-surface px-5 py-6 sm:px-6">
            <div className="flex items-center gap-3">
              <div
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-fg shadow-sm"
                aria-hidden="true"
              >
                <Icons.overview size={22} />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-accent">Modira Command Center</p>
                <h1 id="login-heading" className="text-lg font-semibold text-fg">
                  Sign in
                </h1>
              </div>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              Access your multi-channel social commerce operations console.
            </p>
          </div>

          <CardBody className="px-5 py-6 sm:px-6">
            <form
              className="flex flex-col gap-5"
              onSubmit={handleSubmit(onSubmit)}
              noValidate
              aria-label="Sign in"
            >
              {errors.root ? (
                <StatusBanner tone="failed" title="Sign in failed" description={errors.root.message} />
              ) : null}

              <Field label="Email" htmlFor="login-email">
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  placeholder="you@company.com"
                  aria-invalid={errors.email ? true : undefined}
                  aria-describedby={errors.email ? 'login-email-error' : undefined}
                  className={cn(errors.email && 'border-danger focus:border-danger')}
                  {...register('email')}
                />
                {errors.email ? (
                  <span id="login-email-error" className="text-xs text-danger" role="alert">
                    {errors.email.message}
                  </span>
                ) : null}
              </Field>

              <Field label="Password" htmlFor="login-password">
                <div className="relative">
                  <Input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    aria-invalid={errors.password ? true : undefined}
                    aria-describedby={errors.password ? 'login-password-error' : undefined}
                    className={cn('pr-10', errors.password && 'border-danger focus:border-danger')}
                    {...register('password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    className="absolute inset-y-0 right-0 inline-flex w-10 items-center justify-center rounded-r-lg text-muted hover:text-fg focus-visible:outline-none"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? <Icons.eyeOff size={16} /> : <Icons.eye size={16} />}
                  </button>
                </div>
                {errors.password ? (
                  <span id="login-password-error" className="text-xs text-danger" role="alert">
                    {errors.password.message}
                  </span>
                ) : null}
              </Field>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="mt-1 w-full"
                leadingIcon={isSubmitting ? <LoginSpinner /> : undefined}
              >
                {isSubmitting ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>

            {import.meta.env.DEV ? (
              <p className="mt-5 rounded-lg border border-dashed border-border bg-surface-sunken px-3 py-2 text-center text-xs text-subtle">
                Demo credentials: <span className="font-mono text-muted">admin@example.com</span> /{' '}
                <span className="font-mono text-muted">changeme123</span>
              </p>
            ) : null}
          </CardBody>
        </Card>
      </div>
    </main>
  );
}
