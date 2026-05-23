import { baseApi, addPolling } from './baseApi'
import type {
  User,
  UserUpdate,
  LoginRequest,
  RegisterRequest,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
} from '../types'

export const authApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    getMe: build.query<User, void>({
      query: () => '/auth/me',
      providesTags: ['Me'],
    }),

    updateMe: build.mutation<User, UserUpdate>({
      query: (body) => ({ url: '/auth/me', method: 'PATCH', body }),
      invalidatesTags: ['Me'],
    }),

    login: build.mutation<User, LoginRequest>({
      query: (body) => ({ url: '/auth/login', method: 'POST', body }),
      invalidatesTags: ['Me'],
    }),

    register: build.mutation<User, RegisterRequest>({
      query: (body) => ({ url: '/auth/register', method: 'POST', body }),
      invalidatesTags: ['Me'],
    }),

    logout: build.mutation<void, void>({
      query: () => ({ url: '/auth/logout', method: 'POST' }),
      invalidatesTags: ['Me'],
    }),

    refresh: build.mutation<void, void>({
      query: () => ({ url: '/auth/refresh', method: 'POST' }),
    }),

    changePassword: build.mutation<void, ChangePasswordRequest>({
      query: (body) => ({ url: '/auth/change-password', method: 'POST', body }),
    }),

    forgotPassword: build.mutation<void, ForgotPasswordRequest>({
      query: (body) => ({ url: '/auth/forgot-password', method: 'POST', body }),
    }),

    resetPassword: build.mutation<void, ResetPasswordRequest>({
      query: (body) => ({ url: '/auth/reset-password', method: 'POST', body }),
    }),
  }),
})

const {
  useGetMeQuery: _useGetMeQuery,
  useUpdateMeMutation,
  useLoginMutation,
  useRegisterMutation,
  useLogoutMutation,
  useRefreshMutation,
  useChangePasswordMutation,
  useForgotPasswordMutation,
  useResetPasswordMutation,
} = authApi

export const useGetMeQuery = addPolling(_useGetMeQuery, 60 * 60 * 1000)

export {
  useUpdateMeMutation,
  useLoginMutation,
  useRegisterMutation,
  useLogoutMutation,
  useRefreshMutation,
  useChangePasswordMutation,
  useForgotPasswordMutation,
  useResetPasswordMutation,
}
