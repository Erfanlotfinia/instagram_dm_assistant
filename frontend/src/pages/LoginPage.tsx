import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Navigate, useLocation } from 'react-router-dom';
import { z } from 'zod';

import { Button, Card, CardBody, Field, Input } from '../components/ui';
import { useAuth } from '../contexts/AuthContext';
import { cn } from '../lib/cn';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const location = useLocation();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: 'admin@example.com',
      password: 'changeme123',
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
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-12">
      <Card className="w-full max-w-md">
        <CardBody>
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Modira Command Center</p>
          <h1 className="mt-1 text-xl font-semibold text-fg">Sign in</h1>
          <p className="mt-1 text-sm text-muted">Access your multi-channel social commerce operations console.</p>

          <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            <Field label="Email" htmlFor="login-email">
              <Input id="login-email" type="email" autoComplete="email" {...register('email')} />
              {errors.email ? <span className="text-xs text-danger">{errors.email.message}</span> : null}
            </Field>

            <Field label="Password" htmlFor="login-password">
              <Input id="login-password" type="password" autoComplete="current-password" {...register('password')} />
              {errors.password ? <span className="text-xs text-danger">{errors.password.message}</span> : null}
            </Field>

            {errors.root ? <p className="text-sm text-danger">{errors.root.message}</p> : null}

            <Button type="submit" disabled={isSubmitting} className={cn('w-full')}>
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
