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
          environment: "frontend",
          release: config.app_version || undefined,
          integrations: [
            Sentry.browserTracingIntegration(),
            Sentry.browserProfilingIntegration(),
            Sentry.replayIntegration({
                // Additional SDK configuration goes in here, for example:
                maskAllText: true,
                blockAllMedia: true,
            }),
            Sentry.feedbackIntegration({ autoInject: false }),
          ],
          sendDefaultPii: false,
          tracesSampleRate: 0.25,
          replaysSessionSampleRate: 0.05,
          replaysOnErrorSampleRate: 1.0,
        })
      }
    }
  } catch {
    // Sentry init is non-critical; proceed without it
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <Provider store={store}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </Provider>
    </StrictMode>,
  )
})()
