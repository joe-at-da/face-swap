-- UK Parliament Members API Data Tables
-- Migration to store flattened data from:
-- 1. /api/Members/Search?IsCurrentMember=true&IsEligible=true
-- 2. /api/Members/{id}/Contact
-- 3. /api/Members/{id}/Portraits
-- 4. /api/Members/{id}/VotingHistory

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enums for data integrity
CREATE TYPE parliament_house AS ENUM ('Commons', 'Lords');
CREATE TYPE parliament_gender AS ENUM ('M', 'F', 'Other', 'Unknown');
CREATE TYPE parliament_contact_type AS ENUM (
    'Parliamentary', 
    'Constituency', 
    'Website', 
    'Social Media',
    'Email',
    'Phone',
    'Address',
    'Other'
);
CREATE TYPE parliament_vote_type AS ENUM (
    'Aye', 
    'No', 
    'DidNotVote', 
    'Abstain',
    'NoVoteRecorded',
    'SuspendedOrWithdrawnWhip'
);
CREATE TYPE parliament_division_result AS ENUM (
    'Passed', 
    'Rejected', 
    'Tied',
    'NoResult'
);
CREATE TYPE parliament_sync_type AS ENUM (
    'members', 
    'contacts', 
    'portraits', 
    'voting_history',
    'cron_trigger'
);
CREATE TYPE parliament_sync_status_enum AS ENUM (
    'pending', 
    'running', 
    'completed', 
    'failed'
);

-- Main members table (flattened data from search endpoint)
CREATE TABLE parliament_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Member API core fields
    member_id INTEGER UNIQUE NOT NULL, -- API member ID
    
    -- Name information (flattened)
    display_name TEXT,
    given_name TEXT,
    family_name TEXT,
    full_title TEXT,
    list_as TEXT,
    
    -- Status fields
    is_current_member BOOLEAN DEFAULT false,
    is_eligible BOOLEAN DEFAULT false,
    
    -- House information
    house_id INTEGER,
    house_name parliament_house,
    
    -- Party information
    party_id INTEGER,
    party_name TEXT,
    party_abbreviation TEXT,
    party_background_colour TEXT,
    party_foreground_colour TEXT,
    party_is_lord_spiritual BOOLEAN DEFAULT false,
    party_is_independent BOOLEAN DEFAULT false,
    
    -- Constituency information (for Commons members)
    constituency_id INTEGER,
    constituency_name TEXT,
    constituency_start_date DATE,
    constituency_end_date DATE,
    
    -- Membership information
    membership_start_date DATE,
    membership_end_date DATE,
    membership_start_reason TEXT,
    membership_end_reason TEXT,
    
    -- Lords specific fields
    lords_membership_type_id INTEGER,
    lords_membership_type TEXT,
    
    -- Additional member details
    date_of_birth DATE,
    date_of_death DATE,
    gender parliament_gender,
    
    -- Metadata
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contact information table (flattened data from /api/Members/{id}/Contact)
CREATE TABLE parliament_member_contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id INTEGER NOT NULL REFERENCES parliament_members(member_id) ON DELETE CASCADE,
    
    -- Contact type and details
    contact_type parliament_contact_type,
    contact_type_id INTEGER,
    is_primary BOOLEAN DEFAULT false,
    is_physical BOOLEAN DEFAULT false,
    
    -- Address fields (flattened)
    address_line_1 TEXT,
    address_line_2 TEXT,
    address_line_3 TEXT,
    address_line_4 TEXT,
    address_line_5 TEXT,
    postcode TEXT,
    
    -- Communication details
    email TEXT,
    phone TEXT,
    fax TEXT,
    
    -- Web presence
    website_url TEXT,
    website_display_as TEXT,
    
    -- Social media (flattened)
    twitter_url TEXT,
    facebook_url TEXT,
    instagram_url TEXT,
    linkedin_url TEXT,
    youtube_url TEXT,
    
    -- Additional fields
    note TEXT,
    
    -- Metadata
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Portraits table (URLs from /api/Members/{id}/Portrait endpoint)
CREATE TABLE parliament_member_portraits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id INTEGER NOT NULL REFERENCES parliament_members(member_id) ON DELETE CASCADE,
    
    -- Image information (only what we actually get from the API)
    image_url TEXT NOT NULL,
    crop_type INTEGER NOT NULL, -- 0, 1, 2, or 3
    web_version BOOLEAN DEFAULT false, -- Always false for full resolution
    is_primary BOOLEAN DEFAULT false, -- crop_type 0 is primary
    
    -- Metadata
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Voting history table (flattened data from /api/Members/{id}/Voting)
CREATE TABLE parliament_member_voting_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id INTEGER NOT NULL REFERENCES parliament_members(member_id) ON DELETE CASCADE,
    
    -- Division details (from API response)
    division_id INTEGER, -- API field: id
    division_number INTEGER, -- API field: divisionNumber
    division_title TEXT, -- API field: title
    division_date DATE, -- API field: date (converted from string)
    
    -- House information
    house_id INTEGER, -- API field: house (1=Commons, 2=Lords)
    house_name parliament_house,
    
    -- Vote information
    in_affirmative_lobby BOOLEAN, -- API field: inAffirmativeLobby
    acted_as_teller BOOLEAN, -- API field: actedAsTeller
    
    -- Vote counts (from API response)
    number_in_favour INTEGER, -- API field: numberInFavour
    number_against INTEGER, -- API field: numberAgainst
    
    -- Computed division result
    division_result parliament_division_result,
    
    -- Metadata
    last_synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sync status table to track API synchronization
CREATE TABLE parliament_sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Sync details
    sync_type parliament_sync_type NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    next_sync_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status parliament_sync_status_enum DEFAULT 'pending',
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Performance metrics
    duration_seconds INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_parliament_members_member_id ON parliament_members(member_id);
CREATE INDEX idx_parliament_members_house ON parliament_members(house_name);
CREATE INDEX idx_parliament_members_party ON parliament_members(party_name);
CREATE INDEX idx_parliament_members_current ON parliament_members(is_current_member, is_eligible);
CREATE INDEX idx_parliament_members_constituency ON parliament_members(constituency_name);
CREATE INDEX idx_parliament_members_last_synced ON parliament_members(last_synced_at);

CREATE INDEX idx_parliament_member_contacts_member_id ON parliament_member_contacts(member_id);
CREATE INDEX idx_parliament_member_contacts_type ON parliament_member_contacts(contact_type);
CREATE INDEX idx_parliament_member_contacts_primary ON parliament_member_contacts(is_primary);

CREATE INDEX idx_parliament_member_portraits_member_id ON parliament_member_portraits(member_id);
CREATE INDEX idx_parliament_member_portraits_primary ON parliament_member_portraits(is_primary);

CREATE INDEX idx_parliament_member_voting_history_member_id ON parliament_member_voting_history(member_id);
CREATE INDEX idx_parliament_member_voting_history_date ON parliament_member_voting_history(division_date);
CREATE INDEX idx_parliament_member_voting_history_division_id ON parliament_member_voting_history(division_id);
CREATE INDEX idx_parliament_member_voting_history_house ON parliament_member_voting_history(house_id);
CREATE INDEX idx_parliament_member_voting_history_affirmative ON parliament_member_voting_history(in_affirmative_lobby);

CREATE INDEX idx_parliament_sync_status_type ON parliament_sync_status(sync_type);
CREATE INDEX idx_parliament_sync_status_status ON parliament_sync_status(status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_parliament_members_updated_at 
    BEFORE UPDATE ON parliament_members 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parliament_member_contacts_updated_at 
    BEFORE UPDATE ON parliament_member_contacts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parliament_member_portraits_updated_at 
    BEFORE UPDATE ON parliament_member_portraits 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parliament_member_voting_history_updated_at 
    BEFORE UPDATE ON parliament_member_voting_history 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parliament_sync_status_updated_at 
    BEFORE UPDATE ON parliament_sync_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial sync status records
INSERT INTO parliament_sync_status (sync_type, status) 
VALUES 
    ('members', 'pending'),
    ('contacts', 'pending'),
    ('portraits', 'pending'),
    ('voting_history', 'pending');

-- Enable Row Level Security (RLS)
ALTER TABLE parliament_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE parliament_member_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE parliament_member_portraits ENABLE ROW LEVEL SECURITY;
ALTER TABLE parliament_member_voting_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE parliament_sync_status ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users (adjust based on your needs)
CREATE POLICY "Parliament data is viewable by authenticated users" ON parliament_members
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Parliament contacts are viewable by authenticated users" ON parliament_member_contacts
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Parliament portraits are viewable by authenticated users" ON parliament_member_portraits
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Parliament voting history is viewable by authenticated users" ON parliament_member_voting_history
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Parliament sync status is viewable by authenticated users" ON parliament_sync_status
    FOR SELECT USING (auth.role() = 'authenticated');

-- Grant permissions for service role (for cron job)
GRANT ALL ON parliament_members TO service_role;
GRANT ALL ON parliament_member_contacts TO service_role;
GRANT ALL ON parliament_member_portraits TO service_role;
GRANT ALL ON parliament_member_voting_history TO service_role;
GRANT ALL ON parliament_sync_status TO service_role; 