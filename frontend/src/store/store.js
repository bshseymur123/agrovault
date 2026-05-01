import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  token: localStorage.getItem('agrovault_token') || null,
  user: JSON.parse(localStorage.getItem('agrovault_user') || 'null'),

  setAuth: (token, user) => {
    localStorage.setItem('agrovault_token', token)
    localStorage.setItem('agrovault_user', JSON.stringify(user))
    set({ token, user })
  },

  logout: () => {
    localStorage.removeItem('agrovault_token')
    localStorage.removeItem('agrovault_user')
    set({ token: null, user: null })
  },

  isAuthenticated: () => !!localStorage.getItem('agrovault_token'),
}))

export const useNotifyStore = create((set, get) => ({
  notifications: [],

  push: (type, message) => {
    const id = Date.now()
    set((s) => ({ notifications: [...s.notifications, { id, type, message }] }))
    setTimeout(() => {
      set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) }))
    }, 4000)
  },

  dismiss: (id) => set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),
}))
