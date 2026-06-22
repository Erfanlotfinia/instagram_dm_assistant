import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Callout, Card, CardBody, CardHeader, Field, Input, StatusBanner } from '../components/ui';
import type { BadgeTone } from '../components/ui';
import { LoadingState } from '../components/data';
import { Icons } from '../components/icons';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { UserRole } from '../types/auth';

const profileSchema = z.object({
  full_name: z.string().trim().min(1, 'Display name is required').max(255, 'Display name is too long'),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(8, 'Current password must be at least 8 characters'),
    new_password: z.string().min(8, 'New password must be at least 8 characters'),
    confirm_password: z.string().min(8, 'Confirm your new password'),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

type ProfileFormValues = z.infer<typeof profileSchema>;
type PasswordFormValues = z.infer<typeof passwordSchema>;

function roleLabel(role: UserRole): string {
  return { owner: 'Owner', admin: 'Admin', operator: 'Operator' }[role];
}

function roleTone(role: UserRole): BadgeTone {
  switch (role) {
    case 'owner':
      return 'accent';
    case 'admin':
      return 'info';
    case 'operator':
      return 'neutral';
  }
}

export function ProfilePage() {
  const { refreshUser } = useAuth();
  const { shops, isLoading: shopsLoading } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const profileQuery = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: () => apiClient.getMe(),
  });

  const user = profileQuery.data;

  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    values: {
      full_name: user?.full_name ?? '',
    },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const updateProfileMutation = useMutation({
    mutationFn: (values: ProfileFormValues) => apiClient.updateMe(values),
    onSuccess: async (updatedUser) => {
      showToast('Profile updated.', 'success');
      queryClient.setQueryData(queryKeys.currentUser, updatedUser);
      await refreshUser();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Update failed', 'error'),
  });

  const changePasswordMutation = useMutation({
    mutationFn: (values: PasswordFormValues) =>
      apiClient.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      }),
    onSuccess: () => {
      showToast('Password updated.', 'success');
      passwordForm.reset();
      setShowCurrentPassword(false);
      setShowNewPassword(false);
      setShowConfirmPassword(false);
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Password update failed', 'error'),
  });

  const inputErrorClass = (hasError: boolean) => cn(hasError && 'border-danger focus:border-danger');

  return (
    <HubPage
      eyebrow="Account"
      title="Profile"
      description="Manage your personal details, password, and workspace access."
    >
      {profileQuery.isLoading ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading profile…" />
          </CardBody>
        </Card>
      ) : null}

      {profileQuery.error ? (
        <Card>
          <CardBody>
            <StatusBanner
              tone="failed"
              title="Could not load profile"
              description={
                profileQuery.error instanceof Error ? profileQuery.error.message : 'Try again shortly.'
              }
            />
          </CardBody>
        </Card>
      ) : null}

      {user ? (
        <>
          <Card>
            <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <span
                  className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-accent text-xl font-semibold text-accent-fg"
                  aria-hidden="true"
                >
                  {user.full_name.charAt(0).toUpperCase()}
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold text-fg">{user.full_name}</h2>
                    <Badge tone={roleTone(user.role)}>{roleLabel(user.role)}</Badge>
                    <Badge tone={user.is_active ? 'success' : 'danger'} dot>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <p className="mt-1 truncate text-sm text-muted">{user.email}</p>
                </div>
              </div>
              <Callout
                icon="i"
                title="Managed by your organization"
                className="mt-0 w-full sm:max-w-sm"
              >
                Email address and role are assigned by an administrator and cannot be changed here.
              </Callout>
            </CardBody>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="Personal information" description="Update the name shown across the command center." />
              <CardBody>
                <form
                  className="flex flex-col gap-4"
                  onSubmit={profileForm.handleSubmit((values) => updateProfileMutation.mutate(values))}
                  noValidate
                >
                  <Field label="Display name" htmlFor="profile-full-name">
                    <Input
                      id="profile-full-name"
                      autoComplete="name"
                      aria-invalid={profileForm.formState.errors.full_name ? true : undefined}
                      aria-describedby={
                        profileForm.formState.errors.full_name ? 'profile-full-name-error' : undefined
                      }
                      className={inputErrorClass(Boolean(profileForm.formState.errors.full_name))}
                      {...profileForm.register('full_name')}
                    />
                    {profileForm.formState.errors.full_name ? (
                      <span id="profile-full-name-error" className="text-xs text-danger" role="alert">
                        {profileForm.formState.errors.full_name.message}
                      </span>
                    ) : null}
                  </Field>

                  <Field label="Email">
                    <Input value={user.email} disabled readOnly aria-readonly="true" />
                  </Field>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={updateProfileMutation.isPending || !profileForm.formState.isDirty}>
                      Save changes
                    </Button>
                  </div>
                </form>
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Change password" description="Use a strong password with at least 8 characters." />
              <CardBody>
                <form
                  className="flex flex-col gap-4"
                  onSubmit={passwordForm.handleSubmit((values) => changePasswordMutation.mutate(values))}
                  noValidate
                >
                  <Field label="Current password" htmlFor="profile-current-password">
                    <div className="relative">
                      <Input
                        id="profile-current-password"
                        type={showCurrentPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        className={cn('pr-10', inputErrorClass(Boolean(passwordForm.formState.errors.current_password)))}
                        aria-invalid={passwordForm.formState.errors.current_password ? true : undefined}
                        {...passwordForm.register('current_password')}
                      />
                      <PasswordToggle
                        visible={showCurrentPassword}
                        onToggle={() => setShowCurrentPassword((value) => !value)}
                      />
                    </div>
                    {passwordForm.formState.errors.current_password ? (
                      <span className="text-xs text-danger" role="alert">
                        {passwordForm.formState.errors.current_password.message}
                      </span>
                    ) : null}
                  </Field>

                  <Field label="New password" htmlFor="profile-new-password">
                    <div className="relative">
                      <Input
                        id="profile-new-password"
                        type={showNewPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        className={cn('pr-10', inputErrorClass(Boolean(passwordForm.formState.errors.new_password)))}
                        aria-invalid={passwordForm.formState.errors.new_password ? true : undefined}
                        {...passwordForm.register('new_password')}
                      />
                      <PasswordToggle
                        visible={showNewPassword}
                        onToggle={() => setShowNewPassword((value) => !value)}
                      />
                    </div>
                    {passwordForm.formState.errors.new_password ? (
                      <span className="text-xs text-danger" role="alert">
                        {passwordForm.formState.errors.new_password.message}
                      </span>
                    ) : null}
                  </Field>

                  <Field label="Confirm new password" htmlFor="profile-confirm-password">
                    <div className="relative">
                      <Input
                        id="profile-confirm-password"
                        type={showConfirmPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        className={cn('pr-10', inputErrorClass(Boolean(passwordForm.formState.errors.confirm_password)))}
                        aria-invalid={passwordForm.formState.errors.confirm_password ? true : undefined}
                        {...passwordForm.register('confirm_password')}
                      />
                      <PasswordToggle
                        visible={showConfirmPassword}
                        onToggle={() => setShowConfirmPassword((value) => !value)}
                      />
                    </div>
                    {passwordForm.formState.errors.confirm_password ? (
                      <span className="text-xs text-danger" role="alert">
                        {passwordForm.formState.errors.confirm_password.message}
                      </span>
                    ) : null}
                  </Field>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={changePasswordMutation.isPending}>
                      Update password
                    </Button>
                  </div>
                </form>
              </CardBody>
            </Card>
          </div>

          <Card>
            <CardHeader title="Shop access" description="Shops you can operate in this workspace." />
            <CardBody>
              {shopsLoading ? <LoadingState label="Loading shops…" /> : null}
              {!shopsLoading && shops.length === 0 ? (
                <p className="text-sm text-muted">You are not assigned to any shops yet.</p>
              ) : null}
              {!shopsLoading && shops.length > 0 ? (
                <ul className="divide-y divide-border rounded-lg border border-border">
                  {shops.map((shop) => (
                    <li key={shop.id} className="flex items-center justify-between gap-3 px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-fg">{shop.name}</p>
                        <p className="truncate text-xs text-subtle">{shop.slug}</p>
                      </div>
                      <Badge tone={shop.status === 'active' ? 'success' : 'warning'}>{shop.status}</Badge>
                    </li>
                  ))}
                </ul>
              ) : null}
            </CardBody>
          </Card>
        </>
      ) : null}
    </HubPage>
  );
}

function PasswordToggle({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute inset-y-0 right-0 inline-flex w-10 items-center justify-center rounded-r-lg text-muted hover:text-fg focus-visible:outline-none"
      aria-label={visible ? 'Hide password' : 'Show password'}
      aria-pressed={visible}
    >
      {visible ? <Icons.eyeOff size={16} /> : <Icons.eye size={16} />}
    </button>
  );
}
