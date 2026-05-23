import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { User } from '../types'
import { authApi } from '../api/authApi'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  /** True once the initial getMe check has resolved (or after logout). Prevents spurious re-fetches. */
  bootstrapped: boolean
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  bootstrapped: false,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setUser(state, action: PayloadAction<User | null>) {
      state.user = action.payload
      state.isAuthenticated = action.payload !== null
    },
    clearUser(state) {
      state.user = null
      state.isAuthenticated = false
    },
  },
  extraReducers: (builder) => {
    // Populate auth state from successful getMe / login / register calls
    builder
      .addMatcher(authApi.endpoints.getMe.matchFulfilled, (state, { payload }) => {
        state.user = payload
        state.isAuthenticated = true
        state.bootstrapped = true
      })
      .addMatcher(authApi.endpoints.login.matchFulfilled, (state, { payload }) => {
        state.user = payload
        state.isAuthenticated = true
      })
      .addMatcher(authApi.endpoints.register.matchFulfilled, (state, { payload }) => {
        state.user = payload
        state.isAuthenticated = true
      })
      .addMatcher(authApi.endpoints.logout.matchFulfilled, (state) => {
        state.user = null
        state.isAuthenticated = false
        state.bootstrapped = true
      })
      // If getMe returns an error (e.g. after page refresh with no valid cookie), mark unauthenticated
      .addMatcher(authApi.endpoints.getMe.matchRejected, (state) => {
        state.user = null
        state.isAuthenticated = false
        state.bootstrapped = true
      })
  },
})

export const { setUser, clearUser } = authSlice.actions
export default authSlice.reducer
