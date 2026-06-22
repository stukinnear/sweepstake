import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export interface ApiError {
  id: string
  message: string
  url: string
  status: number | string
}

interface ApiErrorState {
  errors: ApiError[]
}

const initialState: ApiErrorState = { errors: [] }

const apiErrorSlice = createSlice({
  name: 'apiError',
  initialState,
  reducers: {
    addApiError(state, action: PayloadAction<ApiError>) {
      state.errors.push(action.payload)
    },
    dismissApiError(state, action: PayloadAction<string>) {
      state.errors = state.errors.filter((e) => e.id !== action.payload)
    },
  },
})

export const { addApiError, dismissApiError } = apiErrorSlice.actions
export default apiErrorSlice.reducer
