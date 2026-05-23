import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import * as Sentry from '@sentry/react'
import { store } from './store/store'
import App from './App'
import './index.css'

;(async () => {
  try {
    const res = await fetch('/api/config')
    if (res.ok) {
      const config = await res.json()
      if (config.sentry_dsn) {
        Sentry.init({
          dsn: config.sentry_dsn,
          integrations: [
            Sentry.browserTracingIntegration(),
            Sentry.feedbackIntegration({ autoInject: false }),
          ],
          tracesSampleRate: 0.1,
        })
      }
    }
  } catch {
    // Sentry init is non-critical; proceed without it
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <Provider store={store}>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <App />
        </BrowserRouter>
      </Provider>
    </StrictMode>,
  )
})()
