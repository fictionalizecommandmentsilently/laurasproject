"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { useAuth } from "@/lib/authUtils"
import ProtectedRoute from "./ProtectedRoute"
import { Skeleton } from "@/components/ui/skeleton"

export default function ReportsPage() {
  const { loading } = useAuth()

  if (loading) {
    return (
      <div className="p-8">
        <Skeleton className="h-10 w-1/4 mb-8" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    )
  }

  return (
    <ProtectedRoute adminOnly>
      <div className="p-4 md:p-8">
        <h1 className="text-3xl font-bold mb-6">Reports</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Enrollment Trends</CardTitle>
              <CardDescription>Analyze student enrollment over time.</CardDescription>
            </CardHeader>
            <CardContent>
              <p>Coming Soon: Interactive charts and data for enrollment trends.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>GPA Distribution</CardTitle>
              <CardDescription>View the distribution of GPAs across all students.</CardDescription>
            </CardHeader>
            <CardContent>
              <p>Coming Soon: Histograms and statistical summaries for GPA distribution.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Academic Standing Overview</CardTitle>
              <CardDescription>Breakdown of students by academic standing.</CardDescription>
            </CardHeader>
            <CardContent>
              <p>Coming Soon: Pie charts and tables for academic standing.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Major Popularity</CardTitle>
              <CardDescription>See which majors are most popular among students.</CardDescription>
            </CardHeader>
            <CardContent>
              <p>Coming Soon: Bar charts showing student counts per major.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}
