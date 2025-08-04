"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "@/components/ui/use-toast"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isSigningUp, setIsSigningUp] = useState(false)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL

  const handleAuth = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)

    if (!backendUrl) {
      toast({
        title: "Configuration Error",
        description: "Backend URL is not configured. Please check environment variables.",
        variant: "destructive",
      })
      setLoading(false)
      return
    }

    try {
      const endpoint = isSigningUp ? `${backendUrl}/auth/signup` : `${backendUrl}/auth/login`
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      })

      const data = await response.json()

      if (response.ok) {
        // Supabase client will automatically pick up the session from cookies/local storage
        // after the backend successfully signs in/signs up the user.
        toast({
          title: "Success",
          description: data.message,
        })
        router.push("/") // Redirect to dashboard
      } else {
        toast({
          title: "Error",
          description: data.error || "Authentication failed.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error("Auth error:", error)
      toast({
        title: "Error",
        description: "An unexpected error occurred. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-950">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold">{isSigningUp ? "Sign Up" : "Login"}</CardTitle>
          <CardDescription>
            {isSigningUp
              ? "Create your account to get started."
              : "Enter your email and password to access your account."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (isSigningUp ? "Signing Up..." : "Logging In...") : isSigningUp ? "Sign Up" : "Login"}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm">
            {isSigningUp ? "Already have an account?" : "Don't have an account?"}{" "}
            <Button variant="link" onClick={() => setIsSigningUp(!isSigningUp)} disabled={loading}>
              {isSigningUp ? "Login" : "Sign Up"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
