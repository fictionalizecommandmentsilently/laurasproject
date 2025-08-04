"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/lib/authUtils"
import ProtectedRoute from "./ProtectedRoute"
import { toast } from "@/components/ui/use-toast"
import { Skeleton } from "@/components/ui/skeleton"
import { supabase } from "@/lib/supabaseClient" // Import supabase

export default function AdminUploadCSVPage() {
  const { loading: authLoading } = useAuth()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState("")

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0])
      setUploadMessage("")
    } else {
      setSelectedFile(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      toast({
        title: "No file selected",
        description: "Please choose an Excel file to upload.",
        variant: "destructive",
      })
      return
    }

    if (!backendUrl) {
      toast({
        title: "Configuration Error",
        description: "Backend URL is not configured. Please check environment variables.",
        variant: "destructive",
      })
      return
    }

    setUploading(true)
    setUploadMessage("Uploading...")

    const formData = new FormData()
    formData.append("file", selectedFile)

    try {
      const accessToken = (await supabase.auth.getSession()).data.session?.access_token // Use supabase here
      if (!accessToken) {
        toast({
          title: "Error",
          description: "Authentication token missing. Please log in again.",
          variant: "destructive",
        })
        setUploading(false)
        setUploadMessage("Upload failed: Authentication error.")
        return
      }

      const response = await fetch(`${backendUrl}/students/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      const data = await response.json()

      if (response.ok) {
        setUploadMessage(data.message || "File uploaded successfully!")
        toast({
          title: "Upload Success",
          description: data.message || "Student data uploaded successfully.",
        })
        setSelectedFile(null) // Clear selected file
      } else {
        setUploadMessage(`Upload failed: ${data.error || "Unknown error"}`)
        toast({
          title: "Upload Failed",
          description: data.error || "Failed to upload student data.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Upload error:", error)
      setUploadMessage("An error occurred during upload.")
      toast({
        title: "Upload Error",
        description: "An unexpected error occurred during upload.",
        variant: "destructive",
      })
    } finally {
      setUploading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="p-8">
        <Skeleton className="h-10 w-1/4 mb-8" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <ProtectedRoute adminOnly>
      <div className="p-4 md:p-8">
        <h1 className="text-3xl font-bold mb-6">Upload Student Data (CSV/Excel)</h1>
        <Card className="max-w-lg mx-auto">
          <CardHeader>
            <CardTitle>Upload Excel File</CardTitle>
            <CardDescription>Upload an Excel file (.xlsx, .xls) containing student data.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="file">Choose File</Label>
              <Input id="file" type="file" accept=".xlsx, .xls" onChange={handleFileChange} disabled={uploading} />
            </div>
            <Button onClick={handleUpload} disabled={!selectedFile || uploading}>
              {uploading ? "Uploading..." : "Upload Data"}
            </Button>
            {uploadMessage && <p className="text-sm text-muted-foreground mt-2">{uploadMessage}</p>}
            <p className="text-xs text-gray-500 mt-4">
              Ensure your Excel file has columns matching the student profile schema (e.g., "First Name", "Last Name",
              "Email", "Current GPA", etc.).
            </p>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
</merged_code>
