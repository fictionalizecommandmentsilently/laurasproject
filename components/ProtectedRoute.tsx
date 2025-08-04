"use client"

import type React from "react"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/authUtils"
import LoginPage from "./LoginPage"
import { Skeleton } from "@/components/ui/skeleton"

interface ProtectedRouteProps {
  children: React.ReactNode
  adminOnly?: boolean
}

export default function ProtectedRoute({ children, adminOnly = false }: ProtectedRouteProps) {
  const { user, loading, isAdmin } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.push("/login")
      } else if (adminOnly && !isAdmin) {
        // Redirect to dashboard or a forbidden page if not admin
        router.push("/")
      }
    }
  }, [user, loading, isAdmin, adminOnly, router])

  if (loading) {
    return (
      <div className="flex h-screen w-full">
        <div className="hidden md:block w-64 border-r bg-gray-100/40 dark:bg-gray-800/40 p-4">
          <Skeleton className="h-8 w-3/4 mb-6" />
          <Skeleton className="h-6 w-full mb-2" />
          <Skeleton className="h-6 w-full mb-2" />
          <Skeleton className="h-6 w-full mb-2" />
        </div>
        <div className="flex-1 p-8">
          <Skeleton className="h-10 w-1/2 mb-8" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    )
  }

  if (!user || (adminOnly && !isAdmin)) {
    return <LoginPage /> // Or a custom unauthorized page
  }

  return <>{children}</>
}
