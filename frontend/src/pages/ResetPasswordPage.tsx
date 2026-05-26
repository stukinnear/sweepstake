import { ResetPasswordForm } from '../forms/ResetPasswordForm'
import { PageShell } from '../components/PageShell'

export function ResetPasswordPage() {
  return (
    <PageShell variant="auth">
      <div className="flex flex-col items-center justify-center min-h-screen sm:min-h-0 p-6 sm:p-8">
        <ResetPasswordForm />
      </div>
    </PageShell>
  )
}
