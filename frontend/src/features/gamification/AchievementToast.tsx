import { useEffect } from 'react'
import { toast } from 'sonner'

import { useAchievements } from '@/features/gamification/api'

const SEEN_KEY = 'forge:achievements-seen'

/**
 * Watches the workspace's earned achievements and toasts each newly earned
 * one (per browser, tracked in localStorage).
 */
export function AchievementToast() {
  const { data: achievements = [] } = useAchievements()

  useEffect(() => {
    if (achievements.length === 0) return
    let seen: string[] = []
    try {
      seen = JSON.parse(localStorage.getItem(SEEN_KEY) ?? '[]') as string[]
    } catch {
      seen = []
    }
    const fresh = achievements.filter((a) => !seen.includes(a.id))
    if (fresh.length === 0) return

    for (const achievement of fresh) {
      toast.success(`${achievement.icon} ${achievement.title}`, {
        description: achievement.description,
      })
    }
    try {
      localStorage.setItem(
        SEEN_KEY,
        JSON.stringify(achievements.map((a) => a.id)),
      )
    } catch {
      // localStorage unavailable — toast again next load; harmless
    }
  }, [achievements])

  return null
}
