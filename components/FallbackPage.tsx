"use client"

import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"

export default function FallbackPage() {
  const router = useRouter()
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-64px)] bg-background text-foreground p-4 text-center">
      <h1 className="text-4xl font-bold mb-4">404 - Page Not Found</h1>
      <p className="text-lg mb-8">The page you are looking for does not exist.</p>
      <Button onClick={() => router.push("/")}>Go to Dashboard</Button>
    </div>
  )
}
