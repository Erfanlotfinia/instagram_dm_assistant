export type UserRole = 'owner' | 'admin' | 'operator';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  session_id: string;
  csrf_token?: string;
}

export interface UserProfileUpdate {
  full_name: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}
