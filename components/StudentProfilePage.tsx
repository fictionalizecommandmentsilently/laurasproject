"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import type { StudentProfile, GpaHistory } from "@/lib/studentProfileSchema"
import GpaChart from "./GpaChart"
import { useAuth } from "@/lib/authUtils"
import { toast } from "@/components/ui/use-toast"
import { Skeleton } from "@/components/ui/skeleton"
import { PencilIcon, TrashIcon } from "lucide-react"
import { createClient } from "@supabase/supabase-js"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY
const supabase = createClient(supabaseUrl!, supabaseKey!)

export default function StudentProfilePage() {
  const router = useRouter()
  const params = useParams()
  const studentId = params.id as string
  const { user, loading: authLoading, isAdmin } = useAuth()
  const [student, setStudent] = useState<StudentProfile | null>(null)
  const [gpaHistory, setGpaHistory] = useState<GpaHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

  useEffect(() => {
    if (!authLoading && (!user || (!isAdmin && user.id !== studentId))) {
      // Redirect if not authenticated or not authorized (not admin and not own profile)
      router.push("/login") // Or a more appropriate unauthorized page
      return
    }

    if (user && studentId && backendUrl) {
      const fetchStudentData = async () => {
        setLoading(true)
        try {
          const accessToken = (await supabase.auth.getSession()).data.session?.access_token
          if (!accessToken) {
            toast({
              title: "Error",
              description: "Authentication token missing. Please log in again.",
              variant: "destructive",
            })
            setLoading(false)
            return
          }

          const studentResponse = await fetch(`${backendUrl}/students/${studentId}`, {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          })
          if (studentResponse.ok) {
            const studentData = await studentResponse.json()
            setStudent(studentData)
          } else {
            toast({
              title: "Error",
              description: "Failed to load student profile.",
              variant: "destructive",
            })
            router.push("/") // Redirect if student not found or access denied
            setLoading(false)
            return
          }

          const gpaResponse = await fetch(`${backendUrl}/gpa_history/${studentId}`, {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          })
          if (gpaResponse.ok) {
            const gpaData = await gpaResponse.json()
            setGpaHistory(gpaData)
          } else {
            console.error("Failed to load GPA history")
            setGpaHistory([])
          }
        } catch (error) {
          console.error("Error fetching student data:", error)
          toast({
            title: "Error",
            description: "An unexpected error occurred while fetching student data.",
            variant: "destructive",
          })
          router.push("/")
        } finally {
          setLoading(false)
        }
      }
      fetchStudentData()
    }
  }, [studentId, user, authLoading, isAdmin, router, backendUrl])

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this student profile? This action cannot be undone.")) {
      return
    }

    setDeleting(true)
    try {
      const accessToken = (await supabase.auth.getSession()).data.session?.access_token
      if (!accessToken) {
        toast({
          title: "Error",
          description: "Authentication token missing. Please log in again.",
          variant: "destructive",
        })
        setDeleting(false)
        return
      }

      const response = await fetch(`${backendUrl}/students/${studentId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (response.ok) {
        toast({
          title: "Success",
          description: "Student profile deleted successfully.",
        })
        router.push("/") // Redirect to dashboard after deletion
      } else {
        const errorData = await response.json()
        toast({
          title: "Error",
          description: errorData.error || "Failed to delete student profile.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Error deleting student:", error)
      toast({
        title: "Error",
        description: "An unexpected error occurred during deletion.",
        variant: "destructive",
      })
    } finally {
      setDeleting(false)
    }
  }

  if (authLoading || loading) {
    return (
      <div className="p-8">
        <div className="flex items-center gap-4 mb-8">
          <Skeleton className="h-24 w-24 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-96 w-full col-span-full" />
        </div>
      </div>
    )
  }

  if (!student) {
    return <div className="p-8 text-center text-muted-foreground">Student not found.</div>
  }

  return (
    <div className="p-4 md:p-8">
      <Card className="max-w-4xl mx-auto">
        <CardHeader className="flex flex-col md:flex-row items-center gap-4">
          <Avatar className="h-24 w-24">
            <AvatarImage
              src={student.profile_picture_url || "/placeholder.svg?height=96&width=96&query=student profile"}
              alt={`${student.first_name} ${student.last_name}`}
            />
            <AvatarFallback>{`${student.first_name[0]}${student.last_name[0]}`}</AvatarFallback>
          </Avatar>
          <div className="flex-1 text-center md:text-left">
            <CardTitle className="text-3xl">
              {student.first_name} {student.last_name}
            </CardTitle>
            <CardDescription className="text-lg">{student.major}</CardDescription>
            <p className="text-muted-foreground">Current GPA: {student.current_gpa?.toFixed(2) || "N/A"}</p>
          </div>
          {(isAdmin || user?.id === student.user_id) && (
            <div className="flex gap-2 mt-4 md:mt-0">
              <Button variant="outline" onClick={() => router.push(`/students/${student.id}/edit`)}>
                <PencilIcon className="mr-2 h-4 w-4" /> Edit Profile
              </Button>
              {isAdmin && ( // Only admin can delete
                <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
                  <TrashIcon className="mr-2 h-4 w-4" /> {deleting ? "Deleting..." : "Delete"}
                </Button>
              )}
            </div>
          )}
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <h3 className="font-semibold text-lg">Personal Information</h3>
            <p>
              <strong>Email:</strong> {student.email}
            </p>
            <p>
              <strong>Phone:</strong> {student.phone_number}
            </p>
            <p>
              <strong>Date of Birth:</strong> {student.date_of_birth}
            </p>
            <p>
              <strong>Gender:</strong> {student.gender}
            </p>
            <p>
              <strong>Address:</strong> {student.address}, {student.city}, {student.state} {student.zip_code}
            </p>
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold text-lg">Academic Information</h3>
            <p>
              <strong>Enrollment Date:</strong> {student.enrollment_date}
            </p>
            <p>
              <strong>Academic Standing:</strong> {student.academic_standing}
            </p>
            <p>
              <strong>Advisor:</strong> {student.advisor}
            </p>
            <p>
              <strong>Expected Graduation:</strong> {student.expected_graduation_date}
            </p>
          </div>
          <div className="md:col-span-2">
            <GpaChart gpaData={gpaHistory} />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
