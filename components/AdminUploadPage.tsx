"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "@/hooks/use-toast"
import { Loader2 } from "lucide-react"
import { isAdmin } from "@/lib/authUtils"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { studentProfileSchema, type StudentProfileType } from "@/lib/studentProfileSchema"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import ProtectedRoute from "./ProtectedRoute"
import { useAuth } from "@/lib/authUtils"
import { Skeleton } from "@/components/ui/skeleton"

export default function AdminUploadPage() {
  const router = useRouter()
  const { loading: authLoading } = useAuth()
  const [isUserAdmin, setIsUserAdmin] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

  const form = useForm<StudentProfileType>({
    resolver: zodResolver(studentProfileSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      date_of_birth: "",
      enrollment_date: "",
      major: "",
      email: "",
    },
  })

  useEffect(() => {
    const checkAdmin = async () => {
      const adminStatus = await isAdmin()
      setIsUserAdmin(adminStatus)
      if (!adminStatus) {
        toast({
          title: "Access Denied",
          description: "You do not have administrative privileges to view this page.",
          variant: "destructive",
        })
        router.push("/dashboard")
      }
    }
    checkAdmin()
  }, [router])

  const onSubmit = async (data: StudentProfileType) => {
    setSubmitting(true)
    try {
      const session = await fetch("/api/auth/session").then((res) => res.json())
      if (!session?.access_token) {
        router.push("/login")
        return
      }

      // API endpoint for creating a new student (assuming your backend supports it)
      // This would typically be a POST to /students or similar
      const res = await fetch(`${backendUrl}/students`, {
        // Adjust endpoint if needed
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(data),
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || "Failed to add new student")
      }

      toast({
        title: "Success",
        description: "New student added successfully.",
      })
      form.reset() // Clear form after successful submission
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to add new student.",
        variant: "destructive",
      })
    } finally {
      setSubmitting(false)
    }
  }

  if (authLoading) {
    return (
      <div className="p-8">
        <Skeleton className="h-10 w-1/4 mb-8" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    )
  }

  return (
    <ProtectedRoute adminOnly>
      <div className="container mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-6">Admin Upload Options</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Upload Student CSV/Excel</CardTitle>
              <CardDescription>Upload a file to ingest new student data.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={() => router.push("/admin/upload")}>Go to CSV/Excel Upload</Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Manual Student Entry</CardTitle>
              <CardDescription>Manually add a single student record.</CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="first_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>First Name</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="last_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Last Name</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Email</FormLabel>
                        <FormControl>
                          <Input type="email" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="date_of_birth"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Date of Birth</FormLabel>
                        <FormControl>
                          <Input type="date" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="enrollment_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Enrollment Date</FormLabel>
                        <FormControl>
                          <Input type="date" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="major"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Major</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" disabled={submitting}>
                    {submitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Adding...
                      </>
                    ) : (
                      "Add Student"
                    )}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}
