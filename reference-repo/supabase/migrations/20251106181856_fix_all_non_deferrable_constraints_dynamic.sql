-- Fix All Non-Deferrable Foreign Key Constraints Dynamically
-- This migration finds all non-deferrable foreign key constraints and makes them deferrable
-- This approach is more robust as it doesn't rely on exact constraint names

DO $$
DECLARE
    constraint_record RECORD;
    drop_sql TEXT;
    add_sql TEXT;
    table_name TEXT;
    constraint_name TEXT;
    column_name TEXT;
    foreign_table_schema TEXT;
    foreign_table_name TEXT;
    foreign_column_name TEXT;
    delete_rule TEXT;
    fixed_count INTEGER := 0;
BEGIN
    -- Loop through all non-deferrable foreign key constraints in public schema
    FOR constraint_record IN
        SELECT 
            con.oid AS constraint_oid,
            con.conname AS constraint_name,
            t.relname AS table_name,
            a.attname AS column_name,
            nf.nspname AS foreign_table_schema,
            tf.relname AS foreign_table_name,
            af.attname AS foreign_column_name,
            CASE 
                WHEN con.confdeltype = 'c' THEN 'CASCADE'
                WHEN con.confdeltype = 'n' THEN 'SET NULL'
                WHEN con.confdeltype = 'r' THEN 'RESTRICT'
                WHEN con.confdeltype = 'd' THEN 'NO ACTION'
                ELSE 'NO ACTION'
            END AS delete_rule
        FROM pg_constraint con
        JOIN pg_class t ON con.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(con.conkey)
        LEFT JOIN pg_class tf ON con.confrelid = tf.oid
        LEFT JOIN pg_namespace nf ON tf.relnamespace = nf.oid
        LEFT JOIN pg_attribute af ON af.attrelid = tf.oid AND af.attnum = ANY(con.confkey)
        WHERE con.contype = 'f'
            AND n.nspname = 'public'
            AND NOT con.condeferrable
            AND t.relname IN (
                'teams', 'team_members', 'team_invitations', 'team_mp_follows',
                'team_notification_preferences', 'user_clips', 'video_jobs',
                'parliament_member_contacts', 'parliament_member_portraits',
                'parliament_member_voting_history', 'parliament_member_face_encodings'
            )
        ORDER BY t.relname, con.conname
    LOOP
        -- Build DROP CONSTRAINT statement
        drop_sql := format(
            'ALTER TABLE public.%I DROP CONSTRAINT %I',
            constraint_record.table_name,
            constraint_record.constraint_name
        );
        
        -- Execute DROP
        BEGIN
            EXECUTE drop_sql;
            RAISE NOTICE 'Dropped constraint: %.%', constraint_record.table_name, constraint_record.constraint_name;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Failed to drop constraint %.%: %', 
                    constraint_record.table_name, constraint_record.constraint_name, SQLERRM;
                CONTINUE;
        END;
        
        -- Build ADD CONSTRAINT statement with DEFERRABLE INITIALLY DEFERRED
        -- Handle schema qualification for foreign table
        IF constraint_record.foreign_table_schema = 'auth' THEN
            add_sql := format(
                'ALTER TABLE public.%I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %I.%I(%I) ON DELETE %s DEFERRABLE INITIALLY DEFERRED',
                constraint_record.table_name,
                constraint_record.constraint_name,
                constraint_record.column_name,
                constraint_record.foreign_table_schema,
                constraint_record.foreign_table_name,
                constraint_record.foreign_column_name,
                constraint_record.delete_rule
            );
        ELSE
            add_sql := format(
                'ALTER TABLE public.%I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %I.%I(%I) ON DELETE %s DEFERRABLE INITIALLY DEFERRED',
                constraint_record.table_name,
                constraint_record.constraint_name,
                constraint_record.column_name,
                constraint_record.foreign_table_schema,
                constraint_record.foreign_table_name,
                constraint_record.foreign_column_name,
                constraint_record.delete_rule
            );
        END IF;
        
        -- Execute ADD
        BEGIN
            EXECUTE add_sql;
            fixed_count := fixed_count + 1;
            RAISE NOTICE 'Added deferrable constraint: %.%', constraint_record.table_name, constraint_record.constraint_name;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE WARNING 'Failed to add constraint %.%: %', 
                    constraint_record.table_name, constraint_record.constraint_name, SQLERRM;
        END;
    END LOOP;
    
    RAISE NOTICE 'Fixed % non-deferrable foreign key constraints', fixed_count;
END $$;

-- Verify all constraints are now deferrable
DO $$
DECLARE
    non_deferrable_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO non_deferrable_count
    FROM pg_constraint con
    JOIN pg_class t ON con.conrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    WHERE con.contype = 'f'
        AND n.nspname = 'public'
        AND NOT con.condeferrable
        AND t.relname IN (
            'teams', 'team_members', 'team_invitations', 'team_mp_follows',
            'team_notification_preferences', 'user_clips', 'video_jobs',
            'parliament_member_contacts', 'parliament_member_portraits',
            'parliament_member_voting_history', 'parliament_member_face_encodings'
        );
    
    IF non_deferrable_count > 0 THEN
        RAISE WARNING 'Still have % non-deferrable foreign key constraints!', non_deferrable_count;
    ELSE
        RAISE NOTICE 'SUCCESS: All foreign key constraints are now deferrable!';
    END IF;
END $$;

