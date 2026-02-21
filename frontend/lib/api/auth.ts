import apiClient from './client'
import { User } from '@/lib/store/authStore'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export interface AuthResponse {
  access_token: string
  user: User
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post('/auth/login', data)
  return response.data
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await apiClient.post('/auth/register', data)
  return response.data
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get('/auth/me')
  return response.data
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}
