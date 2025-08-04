"use client"

import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { supabase } from "@/lib/supabaseClient"

export default function LogoutButton() {
  const router = useRouter()

  const handleLogout = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) {
      console.error("Error logging out:", error.message)
    } else {
      router.push("/login")
    }
  }

  return (
    <Button onClick={handleLogout} variant="ghost" className="w-full justify-start">
      Logout
    </Button>
  )
}
