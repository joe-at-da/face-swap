-- Create a helper function to safely retrieve user information from user_roles table
-- This function uses SECURITY DEFINER to bypass RLS policies when needed for team operations

CREATE OR REPLACE FUNCTION get_user_info(p_user_id UUID)
RETURNS TABLE(email TEXT, username TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
BEGIN
    -- Return email and username from user_roles table
    RETURN QUERY
    SELECT ur.email, ur.username
    FROM user_roles ur
    WHERE ur.user_id = p_user_id;
END;
$$;

-- Grant execute permission on the helper function to authenticated users
GRANT EXECUTE ON FUNCTION get_user_info TO authenticated;

-- Add comment explaining the function
COMMENT ON FUNCTION get_user_info IS 'Safely retrieves user email and username from user_roles table for authenticated users, bypassing RLS for team-related operations';