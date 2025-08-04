"use client"

import { useRouter } from "next/navigation"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SearchIcon } from "lucide-react"
import Link from "next/link"
import type { StudentProfileType } from "@/lib/studentProfileSchema"
import { useAuth } from "@/lib/authUtils"
import { toast } from "@/hooks/use-toast"
import { Loader2, Users, Book, GraduationCap, FileText } from "lucide-react"

export default function StudentDashboard() {
  const { user, loading: authLoading, isAdmin } = useAuth()
  const [students, setStudents] = useState<StudentProfileType[]>([])
  const [loadingStudents, setLoadingStudents] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const router = useRouter()

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

  useEffect(() => {
    if (!authLoading && user && backendUrl) {
      const fetchStudents = async () => {
        setLoadingStudents(true)
        try {
          const session = await fetch("/api/auth/session").then((res) => res.json())
          if (!session?.access_token) {
            router.push("/login")
            return
          }

          let data: StudentProfileType[] = []
          if (isAdmin) {
            // Admins fetch all students
            const res = await fetch(`${backendUrl}/students`, {
              headers: {
                Authorization: `Bearer ${session.access_token}`,
              },
            })
            if (!res.ok) throw new Error("Failed to fetch all students")
            data = await res.json()
          } else {
            // Non-admins fetch their own student profile
            const userRes = await fetch(`${backendUrl}/users/me`, {
              headers: {
                Authorization: `Bearer ${session.access_token}`,
              },
            })
            if (!userRes.ok) throw new Error("Failed to fetch user profile")
            const userData = await userRes.json()

            if (userData.email) {
              const studentRes = await fetch(`${backendUrl}/students?email=${userData.email}`, {
                headers: {
                  Authorization: `Bearer ${session.access_token}`,
                },
              })
              if (!studentRes.ok) throw new Error("Failed to fetch student profile for current user")
              const studentData = await studentRes.json()
              if (studentData && studentData.length > 0) {
                data = [studentData[0]] // Assuming one student per user email
              }
            }
          }
          setStudents(data)
        } catch (error: any) {
          toast({
            title: "Error",
            description: error.message || "Failed to load student data.",
            variant: "destructive",
          })
        } finally {
          setLoadingStudents(false)
        }
      }

      fetchStudents()
    }
  }, [router, backendUrl, user, authLoading, isAdmin])

  const filteredStudents = students.filter(
    (student) =>
      student.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.major?.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  if (authLoading || loadingStudents) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-64px)]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Student Dashboard</h1>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Students</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{students.length}</div>
            <p className="text-xs text-muted-foreground">
              {isAdmin ? "All enrolled students" : "Your student profile"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. GPA (Overall)</CardTitle>
            <Book className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {students.length > 0 && students[0].gpa_history && students[0].gpa_history.length > 0
                ? (
                    students[0].gpa_history.reduce((sum, entry) => sum + entry.gpa, 0) / students[0].gpa_history.length
                  ).toFixed(2)
                : "N/A"}
            </div>
            <p className="text-xs text-muted-foreground">{isAdmin ? "Across all students" : "Your average GPA"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Majors</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isAdmin ? new Set(students.map((s) => s.major)).size : students.length > 0 && students[0].major ? 1 : 0}
            </div>
            <p className="text-xs text-muted-foreground">{isAdmin ? "Unique majors offered" : "Your declared major"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Reports Available</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isAdmin ? "Full Access" : "Limited"}</div>
            <p className="text-xs text-muted-foreground">
              {isAdmin ? "Comprehensive analytics" : "Personal profile only"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{isAdmin ? "All Students" : "Your Profile"}</CardTitle>
          <CardDescription>
            {isAdmin ? "Overview of all student profiles." : "Your personal student profile details."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-6">
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 dark:text-gray-400" />
              <Input
                type="text"
                placeholder="Search students..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 pr-4 py-2 rounded-md border border-gray-300 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-full"
              />
            </div>
            {/* Add Student button could go here for admins */}
          </div>
          {students.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Major</TableHead>
                    <TableHead>GPA</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredStudents.map((student) => (
                    <TableRow key={student.id}>
                      <TableCell className="font-medium">
                        {student.first_name} {student.last_name}
                      </TableCell>
                      <TableCell>{student.email}</TableCell>
                      <TableCell>{student.major || "N/A"}</TableCell>
                      <TableCell>{student.current_gpa?.toFixed(2) || "N/A"}</TableCell>
                      <TableCell className="text-right">
                        <Link href={`/student/${student.id}`} passHref>
                          <Button variant="outline" size="sm">
                            View Profile
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-muted-foreground">No student data available.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
