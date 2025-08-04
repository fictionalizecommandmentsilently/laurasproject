"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { type StudentProfile, studentProfileSchema } from "@/lib/studentProfileSchema"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/lib/authUtils"
import { toast } from "@/components/ui/use-toast"
import { Skeleton } from "@/components/ui/skeleton"
import { supabase } from "@/lib/supabase" // Declare the supabase variable

export default function EditStudentPage() {
  const router = useRouter()
  const params = useParams()
  const studentId = params.id as string
  const { user, loading: authLoading, isAdmin } = useAuth()
  const [studentLoading, setStudentLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StudentProfile>({
    resolver: zodResolver(studentProfileSchema),
  })

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

  useEffect(() => {
    if (!authLoading && (!user || (!isAdmin && user.id !== studentId))) {
      // Redirect if not authenticated or not authorized (not admin and not own profile)
      router.push("/login") // Or a more appropriate unauthorized page
      return
    }

    if (user && studentId && backendUrl) {
      const fetchStudent = async () => {
        setStudentLoading(true)
        try {
          const response = await fetch(`${backendUrl}/students/${studentId}`, {
            headers: {
              Authorization: `Bearer ${(await user.id) ? (await supabase.auth.getSession()).data.session?.access_token : ""}`,
            },
          })
          if (response.ok) {
            const data = await response.json()
            reset(data) // Populate form with fetched data
          } else {
            toast({
              title: "Error",
              description: "Failed to load student data.",
              variant: "destructive",
            })
            router.push("/") // Redirect if student not found or access denied
          }
        } catch (error) {
          console.error("Error fetching student:", error)
          toast({
            title: "Error",
            description: "An unexpected error occurred while fetching student data.",
            variant: "destructive",
          })
          router.push("/")
        } finally {
          setStudentLoading(false)
        }
      }
      fetchStudent()
    }
  }, [studentId, user, authLoading, isAdmin, router, reset, backendUrl])

  const onSubmit = async (data: StudentProfile) => {
    setIsSubmitting(true)
    try {
      const accessToken = (await supabase.auth.getSession()).data.session?.access_token
      if (!accessToken) {
        toast({
          title: "Error",
          description: "Authentication token missing. Please log in again.",
          variant: "destructive",
        })
        setIsSubmitting(false)
        return
      }

      const response = await fetch(`${backendUrl}/students/${studentId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(data),
      })

      if (response.ok) {
        toast({
          title: "Success",
          description: "Student profile updated successfully.",
        })
        router.push(`/students/${studentId}`)
      } else {
        const errorData = await response.json()
        toast({
          title: "Error",
          description: errorData.error || "Failed to update student profile.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Error updating student:", error)
      toast({
        title: "Error",
        description: "An unexpected error occurred.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (authLoading || studentLoading) {
    return (
      <div className="p-8">
        <Skeleton className="h-10 w-1/3 mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>
        <Skeleton className="h-10 w-32 mt-6" />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-8">
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle>Edit Student Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="first_name">First Name</Label>
              <Input id="first_name" {...register("first_name")} />
              {errors.first_name && <p className="text-red-500 text-sm">{errors.first_name.message}</p>}
            </div>
            <div>
              <Label htmlFor="last_name">Last Name</Label>
              <Input id="last_name" {...register("last_name")} />
              {errors.last_name && <p className="text-red-500 text-sm">{errors.last_name.message}</p>}
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...register("email")} />
              {errors.email && <p className="text-red-500 text-sm">{errors.email.message}</p>}
            </div>
            <div>
              <Label htmlFor="phone_number">Phone Number</Label>
              <Input id="phone_number" {...register("phone_number")} />
              {errors.phone_number && <p className="text-red-500 text-sm">{errors.phone_number.message}</p>}
            </div>
            <div>
              <Label htmlFor="date_of_birth">Date of Birth</Label>
              <Input id="date_of_birth" type="date" {...register("date_of_birth")} />
              {errors.date_of_birth && <p className="text-red-500 text-sm">{errors.date_of_birth.message}</p>}
            </div>
            <div>
              <Label htmlFor="gender">Gender</Label>
              <Input id="gender" {...register("gender")} />
              {errors.gender && <p className="text-red-500 text-sm">{errors.gender.message}</p>}
            </div>
            <div>
              <Label htmlFor="address">Address</Label>
              <Input id="address" {...register("address")} />
              {errors.address && <p className="text-red-500 text-sm">{errors.address.message}</p>}
            </div>
            <div>
              <Label htmlFor="city">City</Label>
              <Input id="city" {...register("city")} />
              {errors.city && <p className="text-red-500 text-sm">{errors.city.message}</p>}
            </div>
            <div>
              <Label htmlFor="state">State</Label>
              <Input id="state" {...register("state")} />
              {errors.state && <p className="text-red-500 text-sm">{errors.state.message}</p>}
            </div>
            <div>
              <Label htmlFor="zip_code">Zip Code</Label>
              <Input id="zip_code" {...register("zip_code")} />
              {errors.zip_code && <p className="text-red-500 text-sm">{errors.zip_code.message}</p>}
            </div>
            <div>
              <Label htmlFor="enrollment_date">Enrollment Date</Label>
              <Input id="enrollment_date" type="date" {...register("enrollment_date")} />
              {errors.enrollment_date && <p className="text-red-500 text-sm">{errors.enrollment_date.message}</p>}
            </div>
            <div>
              <Label htmlFor="major">Major</Label>
              <Input id="major" {...register("major")} />
              {errors.major && <p className="text-red-500 text-sm">{errors.major.message}</p>}
            </div>
            <div>
              <Label htmlFor="current_gpa">Current GPA</Label>
              <Input id="current_gpa" type="number" step="0.01" {...register("current_gpa")} />
              {errors.current_gpa && <p className="text-red-500 text-sm">{errors.current_gpa.message}</p>}
            </div>
            <div>
              <Label htmlFor="academic_standing">Academic Standing</Label>
              <Input id="academic_standing" {...register("academic_standing")} />
              {errors.academic_standing && <p className="text-red-500 text-sm">{errors.academic_standing.message}</p>}
            </div>
            <div>
              <Label htmlFor="advisor">Advisor</Label>
              <Input id="advisor" {...register("advisor")} />
              {errors.advisor && <p className="text-red-500 text-sm">{errors.advisor.message}</p>}
            </div>
            <div>
              <Label htmlFor="expected_graduation_date">Expected Graduation Date</Label>
              <Input id="expected_graduation_date" type="date" {...register("expected_graduation_date")} />
              {errors.expected_graduation_date && (
                <p className="text-red-500 text-sm">{errors.expected_graduation_date.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="profile_picture_url">Profile Picture URL</Label>
              <Input id="profile_picture_url" type="url" {...register("profile_picture_url")} />
              {errors.profile_picture_url && (
                <p className="text-red-500 text-sm">{errors.profile_picture_url.message}</p>
              )}
            </div>
            <div className="col-span-1 md:col-span-2 flex justify-end">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
