"use client"

import { useState, useEffect, useCallback } from "react"
import { supabase } from "./supabaseClient"

interface User {
  id: string
  email: string
  roles: string[]
}

interface AuthState {
  user: User | null
  loading: boolean
  isAdmin: boolean
  fetchUser: () => Promise<void>
}

export const useAuth = (): AuthState => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)

  const fetchUser = useCallback(async () => {
    setLoading(true)
    try {
      const {
        data: { session },
        error: sessionError,
      } = await supabase.auth.getSession()

      if (sessionError) {
        console.error("Error getting session:", sessionError.message)
        setUser(null)
        setIsAdmin(false)
        setLoading(false)
        return
      }

      if (session) {
        // Fetch user roles from your backend API
        const accessToken = session.access_token
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

        if (!backendUrl) {
          console.error("NEXT_PUBLIC_BACKEND_URL is not defined")
          setUser({ id: session.user.id, email: session.user.email || "", roles: [] })
          setIsAdmin(false)
          setLoading(false)
          return
        }

        const response = await fetch(`${backendUrl}/auth/user`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        })

        if (response.ok) {
          const userData = await response.json()
          const fetchedUser: User = {
            id: userData.id,
            email: userData.email,
            roles: userData.roles || [],
          }
          setUser(fetchedUser)
          setIsAdmin(fetchedUser.roles.includes("admin"))
        } else {
          console.error("Failed to fetch user roles from backend:", response.statusText)
          setUser({ id: session.user.id, email: session.user.email || "", roles: [] }) // Fallback with no roles
          setIsAdmin(false)
        }
      } else {
        setUser(null)
        setIsAdmin(false)
      }
    } catch (error) {
      console.error("Auth fetch error:", error)
      setUser(null)
      setIsAdmin(false)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUser()

    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      // Only refetch if session actually changes or becomes null
      if ((_event === "SIGNED_IN" || _event === "SIGNED_OUT") && !loading) {
        fetchUser()
      }
    })

    return () => {
      authListener.unsubscribe()
    }
  }, [fetchUser]) // Depend on fetchUser to avoid re-running on every render

  return { user, loading, isAdmin, fetchUser }
}
