"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { MoreHorizontalIcon } from "lucide-react"
import ProtectedRoute from "./ProtectedRoute"
import { useAuth } from "@/lib/authUtils"
import { toast } from "@/components/ui/use-toast"
import { Skeleton } from "@/components/ui/skeleton"
import { createClient } from "@supabase/supabase-js"

interface User {
  id: string
  email: string
  created_at: string
  last_sign_in_at: string | null
  roles: string[]
}

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY
const supabase = createClient(supabaseUrl!, supabaseKey!)

export default function AdminUsersPage() {
  const { loading: authLoading, isAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loadingUsers, setLoadingUsers] = useState(true)
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

  const fetchUsers = async () => {
    if (!backendUrl) {
      console.error("NEXT_PUBLIC_BACKEND_URL is not defined")
      setLoadingUsers(false)
      return
    }

    setLoadingUsers(true)
    try {
      const accessToken = (await supabase.auth.getSession()).data.session?.access_token
      if (!accessToken) {
        toast({
          title: "Error",
          description: "Authentication token missing. Please log in again.",
          variant: "destructive",
        })
        setLoadingUsers(false)
        return
      }

      const response = await fetch(`${backendUrl}/users`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      } else {
        const errorData = await response.json()
        toast({
          title: "Error",
          description: errorData.error || "Failed to fetch users.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Error fetching users:", error)
      toast({
        title: "Error",
        description: "An unexpected error occurred while fetching users.",
        variant: "destructive",
      })
    } finally {
      setLoadingUsers(false)
    }
  }

  useEffect(() => {
    if (!authLoading && isAdmin) {
      fetchUsers()
    }
  }, [authLoading, isAdmin])

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (!backendUrl) {
      console.error("NEXT_PUBLIC_BACKEND_URL is not defined")
      return
    }

    setUpdatingUserId(userId)
    try {
      const accessToken = (await supabase.auth.getSession()).data.session?.access_token
      if (!accessToken) {
        toast({
          title: "Error",
          description: "Authentication token missing. Please log in again.",
          variant: "destructive",
        })
        setUpdatingUserId(null)
        return
      }

      const response = await fetch(`${backendUrl}/users/${userId}/roles`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ roles: [newRole] }), // Assuming single role for simplicity
      })

      if (response.ok) {
        toast({
          title: "Success",
          description: `User ${userId} role updated to ${newRole}.`,
        })
        fetchUsers() // Re-fetch users to update the list
      } else {
        const errorData = await response.json()
        toast({
          title: "Error",
          description: errorData.error || "Failed to update user role.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Error updating user role:", error)
      toast({
        title: "Error",
        description: "An unexpected error occurred while updating user role.",
        variant: "destructive",
      })
    } finally {
      setUpdatingUserId(null)
    }
  }

  if (authLoading || loadingUsers) {
    return (
      <div className="p-8">
        <Skeleton className="h-10 w-1/4 mb-8" />
        <Skeleton className="h-12 w-full mb-4" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between h-12 border-b last:border-b-0">
            <Skeleton className="h-6 w-1/4" />
            <Skeleton className="h-6 w-1/4" />
            <Skeleton className="h-6 w-1/6" />
            <Skeleton className="h-8 w-20" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <ProtectedRoute adminOnly>
      <div className="p-4 md:p-8">
        <h1 className="text-3xl font-bold mb-6">Manage Users</h1>
        <Card>
          <CardHeader>
            <CardTitle>User List</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Roles</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead>Last Sign In</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      {user.roles.map((role) => (
                        <Badge key={role} variant="secondary" className="mr-1">
                          {role}
                        </Badge>
                      ))}
                    </TableCell>
                    <TableCell>{new Date(user.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      {user.last_sign_in_at ? new Date(user.last_sign_in_at).toLocaleDateString() : "N/A"}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0" disabled={updatingUserId === user.id}>
                            <span className="sr-only">Open menu</span>
                            <MoreHorizontalIcon className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleRoleChange(user.id, "admin")}>
                            Make Admin
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleRoleChange(user.id, "student")}>
                            Make Student
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
