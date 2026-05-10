import toast from 'react-hot-toast'

export const notify = {
  success: (msg: string) => toast.success(msg),
  error: (msg: string) => toast.error(msg),
  loading: (msg: string) => toast.loading(msg),
  dismiss: (id?: string) => toast.dismiss(id),
  promise: <T,>(
    promise: Promise<T>,
    msgs: { loading: string; success: string; error: string }
  ) =>
    toast.promise(promise, {
      loading: msgs.loading,
      success: msgs.success,
      error: msgs.error,
    }),
}
