import { useMutation } from '@tanstack/react-query'

import { useAuthStore } from '@/stores/auth-store'

export function useLogin() {
  const login = useAuthStore((s) => s.login)
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
  })
}

export function useRegister() {
  const register = useAuthStore((s) => s.register)
  return useMutation({
    mutationFn: ({
      email,
      name,
      password,
    }: {
      email: string
      name: string
      password: string
    }) => register(email, name, password),
  })
}
