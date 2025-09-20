-- =====================================================
-- TaxFix Multi-Agent System - Minimal Supabase Schema
-- =====================================================
-- This script creates only the essential tables actually used in the application

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- 1. USERS TABLE (Core Authentication)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- =====================================================
-- 2. USER_PROFILES TABLE (User Profile Management)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Personal Information
    employment_status TEXT CHECK (employment_status IN ('employed', 'self_employed', 'unemployed', 'retired', 'student')),
    filing_status TEXT CHECK (filing_status IN ('single', 'married_joint', 'married_separate', 'head_of_household', 'qualifying_widow')),
    annual_income DECIMAL(12,2),
    dependents INTEGER DEFAULT 0,
    
    -- Tax Preferences (stored as JSON arrays)
    preferred_deductions JSONB DEFAULT '[]'::jsonb,
    tax_goals JSONB DEFAULT '[]'::jsonb,
    risk_tolerance TEXT DEFAULT 'conservative' CHECK (risk_tolerance IN ('conservative', 'moderate', 'aggressive')),
    
    -- Interaction History
    conversation_count INTEGER DEFAULT 0,
    last_interaction TIMESTAMPTZ,
    preferred_communication_style TEXT DEFAULT 'friendly' CHECK (preferred_communication_style IN ('friendly', 'professional', 'detailed', 'concise')),
    
    -- Learned Preferences (stored as JSON arrays)
    frequently_asked_questions JSONB DEFAULT '[]'::jsonb,
    common_expenses JSONB DEFAULT '[]'::jsonb,
    tax_complexity_level TEXT DEFAULT 'beginner' CHECK (tax_complexity_level IN ('beginner', 'intermediate', 'advanced')),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 3. CONVERSATIONS TABLE (Chat History)
-- =====================================================
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 4. MESSAGES TABLE (Chat Messages)
-- =====================================================
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'agent')),
    content TEXT NOT NULL,
    message_type TEXT DEFAULT 'text' CHECK (message_type IN ('text', 'action', 'suggestion', 'reasoning', 'error')),
    agent_type TEXT CHECK (agent_type IN ('orchestrator', 'profile', 'tax_knowledge', 'memory', 'action')),
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 5. USER_LEARNING TABLE (AI Learning from Conversations)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_learning (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    learning_type TEXT NOT NULL DEFAULT 'user_profile_summary',
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 0.9 CHECK (confidence >= 0 AND confidence <= 1),
    source TEXT DEFAULT 'conversation_analysis',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, learning_type, key)
);

-- =====================================================
-- 6. TAX_DOCUMENTS TABLE (User Tax Documents)
-- =====================================================
CREATE TABLE IF NOT EXISTS tax_documents (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    amount DECIMAL(12,2),
    description TEXT NOT NULL,
    file_path TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 7. VECTOR EMBEDDINGS TABLES (For AI Knowledge)
-- =====================================================

-- Tax rules embeddings (used by vector service)
CREATE TABLE IF NOT EXISTS tax_rules_embeddings (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    content TEXT NOT NULL,
    embedding VECTOR(384), -- Adjust dimension based on your embedding model
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deductions embeddings (used by vector service)
CREATE TABLE IF NOT EXISTS deductions_embeddings (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    content TEXT NOT NULL,
    embedding VECTOR(384), -- Adjust dimension based on your embedding model
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User context embeddings (used by vector service)
CREATE TABLE IF NOT EXISTS user_context_embeddings (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(384), -- Adjust dimension based on your embedding model
    context_type TEXT DEFAULT 'conversation',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 8. INDEXES FOR PERFORMANCE
-- =====================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- User profiles indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_employment ON user_profiles(employment_status);
CREATE INDEX IF NOT EXISTS idx_user_profiles_income ON user_profiles(annual_income);

-- Conversations indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);

-- Messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_messages_agent_type ON messages(agent_type);

-- User learning indexes
CREATE INDEX IF NOT EXISTS idx_user_learning_user_id ON user_learning(user_id);
CREATE INDEX IF NOT EXISTS idx_user_learning_type ON user_learning(learning_type);

-- Tax documents indexes
CREATE INDEX IF NOT EXISTS idx_tax_documents_user_id ON tax_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_tax_documents_year ON tax_documents(year);
CREATE INDEX IF NOT EXISTS idx_tax_documents_type ON tax_documents(document_type);

-- Vector embeddings indexes
CREATE INDEX IF NOT EXISTS idx_tax_rules_embeddings_created_at ON tax_rules_embeddings(created_at);
CREATE INDEX IF NOT EXISTS idx_deductions_embeddings_created_at ON deductions_embeddings(created_at);
CREATE INDEX IF NOT EXISTS idx_user_context_embeddings_user_id ON user_context_embeddings(user_id);

-- =====================================================
-- 9. FUNCTIONS FOR AUTOMATIC UPDATES
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_learning_updated_at BEFORE UPDATE ON user_learning
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tax_documents_updated_at BEFORE UPDATE ON tax_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 10. ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_learning ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_context_embeddings ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid()::text = id);

CREATE POLICY "Users can insert own profile" ON users
    FOR INSERT WITH CHECK (auth.uid()::text = id);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid()::text = id);

-- User profiles policies
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid()::text = user_id);

-- Conversations policies
CREATE POLICY "Users can view own conversations" ON conversations
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own conversations" ON conversations
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own conversations" ON conversations
    FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Users can delete own conversations" ON conversations
    FOR DELETE USING (auth.uid()::text = user_id);

-- Messages policies
CREATE POLICY "Users can view messages from own conversations" ON messages
    FOR SELECT USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE user_id = auth.uid()::text
        )
    );

CREATE POLICY "Users can insert messages to own conversations" ON messages
    FOR INSERT WITH CHECK (
        conversation_id IN (
            SELECT id FROM conversations WHERE user_id = auth.uid()::text
        )
    );

CREATE POLICY "Users can update messages from own conversations" ON messages
    FOR UPDATE USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE user_id = auth.uid()::text
        )
    );

CREATE POLICY "Users can delete messages from own conversations" ON messages
    FOR DELETE USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE user_id = auth.uid()::text
        )
    );

-- User learning policies
CREATE POLICY "Users can view own learning data" ON user_learning
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own learning data" ON user_learning
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own learning data" ON user_learning
    FOR UPDATE USING (auth.uid()::text = user_id);

-- Tax documents policies
CREATE POLICY "Users can view own tax documents" ON tax_documents
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own tax documents" ON tax_documents
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own tax documents" ON tax_documents
    FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Users can delete own tax documents" ON tax_documents
    FOR DELETE USING (auth.uid()::text = user_id);

-- User context embeddings policies
CREATE POLICY "Users can view own context embeddings" ON user_context_embeddings
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own context embeddings" ON user_context_embeddings
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own context embeddings" ON user_context_embeddings
    FOR UPDATE USING (auth.uid()::text = user_id);

-- Public read access for knowledge base embeddings (no user-specific data)
CREATE POLICY "Anyone can view tax rules embeddings" ON tax_rules_embeddings
    FOR SELECT USING (true);

CREATE POLICY "Anyone can view deductions embeddings" ON deductions_embeddings
    FOR SELECT USING (true);

-- =====================================================
-- 11. GRANT PERMISSIONS
-- =====================================================

-- Grant necessary permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;

-- Grant permissions to anon users for public data
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON tax_rules_embeddings TO anon;
GRANT SELECT ON deductions_embeddings TO anon;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE 'TaxFix Minimal Supabase schema created successfully!';
    RAISE NOTICE 'Tables created: users, user_profiles, conversations, messages, user_learning, tax_documents, tax_rules_embeddings, deductions_embeddings, user_context_embeddings';
    RAISE NOTICE 'Functions created: update_updated_at_column';
    RAISE NOTICE 'RLS policies enabled for data security';
    RAISE NOTICE 'Only essential tables included - optimized for actual usage';
END $$;
