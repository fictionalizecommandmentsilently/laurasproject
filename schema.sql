-- Enable the "uuid-ossp" extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for user roles
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL
);

-- Insert default roles if they don't exist
INSERT INTO roles (name) VALUES ('admin') ON CONFLICT (name) DO NOTHING;
INSERT INTO roles (name) VALUES ('student') ON CONFLICT (name) DO NOTHING;

-- Junction table for users and roles
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Students Table
CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- Link to Supabase auth.users
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth DATE,
    gender TEXT,
    email TEXT UNIQUE,
    phone_number TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    enrollment_date DATE,
    major TEXT,
    current_gpa NUMERIC(3, 2),
    academic_standing TEXT,
    advisor TEXT,
    expected_graduation_date DATE,
    profile_picture_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- GPA History Table
CREATE TABLE IF NOT EXISTS gpa_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    gpa NUMERIC(3, 2) NOT NULL,
    date_recorded DATE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to set updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at on students table
DROP TRIGGER IF EXISTS set_updated_at ON students;
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON students
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- RLS for students table
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

-- Policy for authenticated users to view their own student profile
CREATE POLICY "Students can view their own profile."
ON students FOR SELECT
USING (auth.uid() = user_id);

-- Policy for admins to view all student profiles
CREATE POLICY "Admins can view all student profiles."
ON students FOR SELECT
USING (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- Policy for admins to insert students
CREATE POLICY "Admins can insert students."
ON students FOR INSERT
WITH CHECK (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- Policy for admins to update students
CREATE POLICY "Admins can update students."
ON students FOR UPDATE
USING (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- Policy for admins to delete students
CREATE POLICY "Admins can delete students."
ON students FOR DELETE
USING (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- RLS for gpa_history table
ALTER TABLE gpa_history ENABLE ROW LEVEL SECURITY;

-- Policy for authenticated users to view their own GPA history
CREATE POLICY "GPA history can be viewed by student owner."
ON gpa_history FOR SELECT
USING (EXISTS (SELECT 1 FROM students s WHERE s.id = gpa_history.student_id AND s.user_id = auth.uid()));

-- Policy for admins to view all GPA history
CREATE POLICY "Admins can view all GPA history."
ON gpa_history FOR SELECT
USING (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- Policy for admins to insert GPA history
CREATE POLICY "Admins can insert GPA history."
ON gpa_history FOR INSERT
WITH CHECK (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- Policy for admins to update GPA history
CREATE POLICY "Admins can update GPA history."
ON gpa_history FOR UPDATE
USING (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- Policy for admins to delete GPA history
CREATE POLICY "Admins can delete GPA history."
ON gpa_history FOR DELETE
USING (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- RLS for roles table (read-only for all authenticated users)
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all authenticated users" ON roles FOR SELECT USING (auth.role() = 'authenticated');

-- RLS for user_roles table
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- Policy for admins to manage user roles
CREATE POLICY "Admins can manage user roles."
ON user_roles FOR ALL
USING (EXISTS (SELECT 1 FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = auth.uid() AND r.name = 'admin'));

-- Trigger to assign 'student' role to new users by default
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    student_role_id UUID;
BEGIN
    -- Get the ID of the 'student' role
    SELECT id INTO student_role_id FROM roles WHERE name = 'student';

    -- Insert a record into user_roles for the new user with the 'student' role
    INSERT INTO user_roles (user_id, role_id)
    VALUES (NEW.id, student_role_id);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the trigger
DROP TRIGGER IF EXISTS assign_student_role ON auth.users;
CREATE TRIGGER assign_student_role
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION handle_new_user();
