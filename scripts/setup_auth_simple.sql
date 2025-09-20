-- Simple authentication setup for TaxFix
-- Run this in your Supabase SQL editor

-- Drop existing tables if they exist (be careful!)
-- DROP TABLE IF EXISTS messages CASCADE;
-- DROP TABLE IF EXISTS conversations CASCADE;
-- DROP TABLE IF EXISTS user_profiles CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;

-- Create users table with authentication
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    employment_status TEXT,
    filing_status TEXT,
    annual_income FLOAT,
    dependents INTEGER DEFAULT 0,
    preferred_deductions TEXT[] DEFAULT '{}',
    tax_goals TEXT[] DEFAULT '{}',
    risk_tolerance TEXT DEFAULT 'conservative',
    conversation_count INTEGER DEFAULT 0,
    last_interaction TIMESTAMP,
    preferred_communication_style TEXT DEFAULT 'friendly',
    frequently_asked_questions TEXT[] DEFAULT '{}',
    common_expenses TEXT[] DEFAULT '{}',
    tax_complexity_level TEXT DEFAULT 'beginner',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT,
    title TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    role TEXT NOT NULL,
    message_type TEXT,
    agent_type TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create tax_rules table
CREATE TABLE IF NOT EXISTS tax_rules (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    year INTEGER NOT NULL,
    applicable_income_range TEXT,
    applicable_filing_status TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create deductions table
CREATE TABLE IF NOT EXISTS deductions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    deduction_type TEXT NOT NULL,
    category TEXT NOT NULL,
    max_amount FLOAT,
    income_limit FLOAT,
    requirements TEXT[],
    applicable_filing_status TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Insert sample tax rules
INSERT INTO tax_rules (id, title, description, category, year, applicable_income_range, applicable_filing_status, created_at, updated_at) VALUES
('rule_001', 'Standard Deduction 2024', 'Standard deduction amounts for 2024 tax year', 'deduction', 2024, 'all', '{"single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"}', NOW(), NOW()),
('rule_002', 'Itemized Deductions', 'Itemized deductions for taxpayers who exceed standard deduction', 'deduction', 2024, 'all', '{"single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"}', NOW(), NOW()),
('rule_003', 'Child Tax Credit', 'Child tax credit for qualifying children', 'credit', 2024, 'all', '{"single", "married_joint", "head_of_household", "qualifying_widow"}', NOW(), NOW());

-- Insert sample deductions
INSERT INTO deductions (id, name, description, deduction_type, category, max_amount, income_limit, requirements, applicable_filing_status, created_at, updated_at) VALUES
('ded_001', 'Home Office Deduction', 'Deduction for home office expenses', 'business', 'business', 1500, NULL, '{"dedicated_workspace", "regular_use", "principal_place_of_business"}', '{"single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"}', NOW(), NOW()),
('ded_002', 'Charitable Contributions', 'Deduction for charitable donations', 'itemized', 'charitable', NULL, NULL, '{"qualified_organization", "proper_documentation"}', '{"single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"}', NOW(), NOW()),
('ded_003', 'Student Loan Interest', 'Deduction for student loan interest payments', 'above_line', 'education', 2500, 75000, '{"qualified_loan", "interest_payments"}', '{"single", "married_joint", "married_separate", "head_of_household", "qualifying_widow"}', NOW(), NOW());

-- Grant necessary permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
