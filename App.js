import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import LoginPage from "./components/LoginPage"
import StudentDashboard from "./components/StudentDashboard"
import StudentProfilePage from "./components/StudentProfilePage"
import EditStudentPage from "./components/EditStudentPage"
import ReportsPage from "./components/ReportsPage"
import AdminUsersPage from "./components/AdminUsersPage"
import AdminUploadCSVPage from "./components/AdminUploadCSVPage"
import ProtectedRoute from "./components/ProtectedRoute"
import SidebarLayout from "./components/SidebarLayout"
import FallbackPage from "./components/FallbackPage"

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <SidebarLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<StudentDashboard />} />
          <Route path="students/:id" element={<StudentProfilePage />} />
          <Route path="students/:id/edit" element={<EditStudentPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="admin/users" element={<AdminUsersPage />} />
          <Route path="admin/upload" element={<AdminUploadCSVPage />} />
          <Route path="*" element={<FallbackPage />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
