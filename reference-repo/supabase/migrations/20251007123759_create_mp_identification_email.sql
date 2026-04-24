-- MP Identification Email Notification Migration
-- Migration to create function and trigger for sending email notifications
-- when new parliament member clips are added

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS http;

-- Create function to send MP identification email notifications
CREATE OR REPLACE FUNCTION notify_mp_identification_email()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    app_url text;
    cron_secret text;
    response_status jsonb;
    member_id_val integer;
    mp_name text;
    clip_id_val uuid;
    -- Variables for individual user notifications
    individual_user_record record;
    -- Variables for team notifications
    team_record record;
BEGIN
    -- Get the new clip data
    member_id_val := NEW.member_id;
    clip_id_val := NEW.id;
    
    -- Get MP name for logging
    SELECT display_name INTO mp_name
    FROM parliament_members
    WHERE member_id = member_id_val;
    
    -- Get environment variables from vault
    SELECT decrypted_secret INTO app_url 
    FROM vault.decrypted_secrets 
    WHERE name = 'project_url';
    
    SELECT decrypted_secret INTO cron_secret 
    FROM vault.decrypted_secrets 
    WHERE name = 'cron_secret';
    
    -- Fallback if vault is not used
    IF app_url IS NULL THEN
        app_url := 'http://host.docker.internal:3000';
    END IF;
    
    IF cron_secret IS NULL THEN
        cron_secret := 'your-secret-cron-key';
    END IF;
    
    -- Log start of notification process
    RAISE LOG 'Starting MP identification email notifications for MP % (ID: %) and clip %', mp_name, member_id_val, clip_id_val;
    
    -- 1. Send notifications to individual users following this MP
    FOR individual_user_record IN
        SELECT 
            ur.user_id,
            ur.email,
            'individual' as notification_type
        FROM user_roles ur
        WHERE ur.member_id = member_id_val
        AND ur.email IS NOT NULL
    LOOP
        BEGIN
            -- Make HTTP POST request to the MP identification email endpoint
            SELECT content::jsonb INTO response_status
            FROM http((
                'POST',
                app_url || '/api/notifications/mp-identification-email',
                ARRAY[http_header('Authorization', 'Bearer ' || cron_secret)],
                'application/json',
                jsonb_build_object(
                    'userId', individual_user_record.user_id,
                    'userEmail', individual_user_record.email,
                    'memberId', member_id_val,
                    'mpName', mp_name,
                    'clipId', clip_id_val,
                    'notificationType', 'individual'
                )::text
            )::http_request);
            
            RAISE LOG 'Individual notification sent to user % (email: %). Response: %', 
                individual_user_record.user_id, individual_user_record.email, response_status;
                
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Failed to send individual notification to user %: %', 
                    individual_user_record.user_id, SQLERRM;
        END;
    END LOOP;
    
    -- 2. Send notifications to teams following this MP
    FOR team_record IN
        SELECT DISTINCT
            tmf.team_id,
            tm.user_id,
            ur.email,
            'team' as notification_type
        FROM team_mp_follows tmf
        JOIN team_members tm ON tmf.team_id = tm.team_id
        JOIN user_roles ur ON tm.user_id = ur.user_id
        JOIN team_notification_preferences tnp ON (
            tnp.team_id = tmf.team_id 
            AND tnp.user_id = tm.user_id
            AND tnp.mp_activity_notifications = true
            AND tnp.email_notifications = true
        )
        WHERE tmf.member_id = member_id_val
        AND ur.email IS NOT NULL
    LOOP
        BEGIN
            -- Make HTTP POST request to the MP identification email endpoint
            SELECT content::jsonb INTO response_status
            FROM http((
                'POST',
                app_url || '/api/notifications/mp-identification-email',
                ARRAY[http_header('Authorization', 'Bearer ' || cron_secret)],
                'application/json',
                jsonb_build_object(
                    'userId', team_record.user_id,
                    'userEmail', team_record.email,
                    'teamId', team_record.team_id,
                    'memberId', member_id_val,
                    'mpName', mp_name,
                    'clipId', clip_id_val,
                    'notificationType', 'team'
                )::text
            )::http_request);
            
            RAISE LOG 'Team notification sent to user % (email: %) in team %. Response: %', 
                team_record.user_id, team_record.email, team_record.team_id, response_status;
                
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Failed to send team notification to user % in team %: %', 
                    team_record.user_id, team_record.team_id, SQLERRM;
        END;
    END LOOP;
    
    RAISE LOG 'Completed MP identification email notifications for MP % (ID: %)', mp_name, member_id_val;
    
    RETURN NEW;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Log errors but don't fail the original insert
        RAISE WARNING 'MP identification email notification failed for MP % (ID: %): %', 
            member_id_val, member_id_val, SQLERRM;
        -- Don't re-raise the exception as we don't want to block the original operation
        RETURN NEW;
END;
$$;

-- Create trigger on parliament_member_clips table
-- This will fire after INSERT operations when new clips are added
CREATE TRIGGER trigger_notify_mp_identification_email
    AFTER INSERT ON parliament_member_clips
    FOR EACH ROW
    EXECUTE FUNCTION notify_mp_identification_email();

-- Add comment for documentation
COMMENT ON FUNCTION notify_mp_identification_email() IS 
'Function to send email notifications to users and teams following an MP when new clips are added';

COMMENT ON TRIGGER trigger_notify_mp_identification_email ON parliament_member_clips IS 
'Trigger that calls notify_mp_identification_email() after new clips are inserted';
