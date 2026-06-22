export type Gender = 'male' | 'female' | 'other'

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string | null
  user_name: string | null
  gender: Gender | null
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface UserUpdate {
  email?: string
  first_name?: string
  last_name?: string
  user_name?: string
  gender?: Gender
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  first_name: string
  last_name?: string
  user_name?: string
  gender?: Gender
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface ForgotPasswordRequest {
  email: string
}

export interface ResetPasswordRequest {
  token: string
  new_password: string
}
