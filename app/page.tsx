"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabaseClient"
import LoginPage from "@/components/LoginPage"
import SidebarLayout from "@/components/SidebarLayout"
import FallbackPage from "@/components/FallbackPage"
import StudentDashboard from "@/components/StudentDashboard"
import AdminUsersPage from "@/components/AdminUsersPage"
import AdminUploadPage from "@/components/AdminUploadPage"
import StudentProfilePage from "@/components/StudentProfilePage"
import ReportsPage from "@/components/ReportsPage"
import EditStudentPage from "@/components/EditStudentPage"
import ProtectedRoute from "@/components/ProtectedRoute"

export default function HomePage() {
  const [session, setSession] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [userRole, setUserRole] = useState<string | null>(null)
  const [activePage, setActivePage] = useState<string>("dashboard") // Default page
  const router = useRouter()

  useEffect(() => {
    const checkUser = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      if (session) {
        router.push("/dashboard")
      } else {
        // User is not logged in, stay on login page
      }
    }
    checkUser()

    const { data: authListener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        router.push("/dashboard")
      } else {
        router.push("/login")
      }
    })

    return () => {
      authListener.subscription.unsubscribe()
    }
  }, [router])

  if (loading) {
    return <FallbackPage message="Loading application..." />
  }

  if (!session) {
    return <LoginPage />
  }

  const renderPage = () => {
    switch (activePage) {
      case "dashboard":
        return (
          <ProtectedRoute allowedRoles={["admin", "teacher", "counselor", "student"]} userRole={userRole}>
            <StudentDashboard setActivePage={setActivePage} />
          </ProtectedRoute>
        )
      case "profile":
        return (
          <ProtectedRoute allowedRoles={["admin", "teacher", "counselor", "student"]} userRole={userRole}>
            <StudentProfilePage />
          </ProtectedRoute>
        )
      case "edit-student":
        return (
          <ProtectedRoute allowedRoles={["admin", "teacher", "counselor"]} userRole={userRole}>
            <EditStudentPage />
          </ProtectedRoute>
        )
      case "reports":
        return (
          <ProtectedRoute allowedRoles={["admin", "teacher", "counselor"]} userRole={userRole}>
            <ReportsPage />
          </ProtectedRoute>
        )
      case "admin-users":
        return (
          <ProtectedRoute allowedRoles={["admin"]} userRole={userRole}>
            <AdminUsersPage />
          </ProtectedRoute>
        )
      case "admin-upload":
        return (
          <ProtectedRoute allowedRoles={["admin"]} userRole={userRole}>
            <AdminUploadPage />
          </ProtectedRoute>
        )
      default:
        return <FallbackPage message="Page not found or unauthorized." />
    }
  }

  return (
    <SidebarLayout userRole={userRole} setActivePage={setActivePage}>
      {renderPage()}
    </SidebarLayout>
  )
}
