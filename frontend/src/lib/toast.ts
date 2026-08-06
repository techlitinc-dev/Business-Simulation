import { toast } from 'sonner'

import { useNotificationsStore } from '@/stores/notifications'

/** Toast helpers — the only place feature code may import sonner from. */
export function toastSuccess(msg: string, title?: string) {
  toast.success(title ?? msg, { description: title ? msg : undefined })
  useNotificationsStore.getState().addNotification({
    title: title ?? msg,
    body: title ? msg : '',
    kind: 'success',
  })
}

export function toastError(msg: string, title?: string) {
  toast.error(title ?? msg, { description: title ? msg : undefined })
  useNotificationsStore.getState().addNotification({
    title: title ?? msg,
    body: title ? msg : '',
    kind: 'error',
  })
}

export function toastInfo(msg: string, title?: string) {
  toast.info(title ?? msg, { description: title ? msg : undefined })
  useNotificationsStore.getState().addNotification({
    title: title ?? msg,
    body: title ? msg : '',
    kind: 'info',
  })
}
