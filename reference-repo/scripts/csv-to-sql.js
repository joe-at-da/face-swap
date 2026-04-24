import fs from 'fs';
import path from 'path';

// Helper function to escape SQL strings
function escapeSqlString(value, allowEmptyString = true) {
  if (value === null || value === undefined) {
    return 'NULL';
  }
  if (value === '' && !allowEmptyString) {
    return 'NULL';
  }
  // Replace single quotes with two single quotes for SQL escaping
  const escaped = String(value).replace(/'/g, "''");
  return `'${escaped}'`;
}

// Helper function to parse CSV line (handles quoted fields with commas)
function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        // Escaped quote
        current += '"';
        i++; // Skip next quote
      } else {
        // Toggle quote state
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      // End of field
      result.push(current.trim()); // Trim whitespace and carriage returns
      current = '';
    } else if (char !== '\r' && char !== '\n') { // Skip carriage returns and newlines
      current += char;
    }
  }

  // Add last field
  result.push(current.trim());

  return result;
}

// Convert portraits CSV to SQL
function convertPortraitsCSV(csvPath) {
  const csvContent = fs.readFileSync(csvPath, 'utf-8');
  const lines = csvContent.split('\n').filter(line => line.trim());

  // Skip header
  const headers = parseCSVLine(lines[0]);
  console.log('Portraits headers:', headers);

  const values = [];
  const seenIds = new Set(); // Track IDs to remove duplicates

  for (let i = 1; i < lines.length; i++) {
    const fields = parseCSVLine(lines[i]);

    if (fields.length < 11) continue; // Skip malformed lines

    const [id, member_id, image_url, crop_type, web_version, is_primary,
           last_synced_at, created_at, updated_at, is_deleted, deleted_at] = fields;

    // Skip duplicates
    if (seenIds.has(id)) {
      console.log(`  Skipping duplicate portrait ID: ${id}`);
      continue;
    }
    seenIds.add(id);

    const row = `(${escapeSqlString(id)}, ${member_id || 'NULL'}, ${escapeSqlString(image_url)}, ` +
                `${crop_type || 'NULL'}, ${web_version === 'true' ? 'true' : 'false'}, ` +
                `${is_primary === 'true' ? 'true' : 'false'}, ${escapeSqlString(last_synced_at)}, ` +
                `${escapeSqlString(created_at)}, ${escapeSqlString(updated_at)}, ` +
                `${is_deleted === 'true' ? 'true' : 'false'}, ${escapeSqlString(deleted_at, false)})`;

    values.push(row);
  }

  const sql = `-- Data for parliament_member_portraits from production\n` +
              `INSERT INTO "public"."parliament_member_portraits" \n` +
              `("id", "member_id", "image_url", "crop_type", "web_version", "is_primary", ` +
              `"last_synced_at", "created_at", "updated_at", "is_deleted", "deleted_at")\n` +
              `VALUES\n${values.join(',\n')};\n\n`;

  return sql;
}

// Convert contacts CSV to SQL
function convertContactsCSV(csvPath) {
  const csvContent = fs.readFileSync(csvPath, 'utf-8');
  const lines = csvContent.split('\n').filter(line => line.trim());

  // Skip header
  const headers = parseCSVLine(lines[0]);
  console.log('Contacts headers:', headers);

  const values = [];
  const seenIds = new Set(); // Track IDs to remove duplicates

  for (let i = 1; i < lines.length; i++) {
    const fields = parseCSVLine(lines[i]);

    if (fields.length < 28) continue; // Skip malformed lines

    const [id, member_id, contact_type, contact_type_id, is_primary, is_physical,
           address_line_1, address_line_2, address_line_3, address_line_4, address_line_5,
           postcode, email, phone, fax, website_url, website_display_as,
           twitter_url, facebook_url, instagram_url, linkedin_url, youtube_url, note,
           last_synced_at, created_at, updated_at, is_deleted, deleted_at] = fields;

    // Skip duplicates
    if (seenIds.has(id)) {
      console.log(`  Skipping duplicate contact ID: ${id}`);
      continue;
    }
    seenIds.add(id);

    const row = `(${escapeSqlString(id)}, ${member_id || 'NULL'}, ${escapeSqlString(contact_type, false)}, ` +
                `${contact_type_id || 'NULL'}, ${is_primary === 'true' ? 'true' : 'false'}, ` +
                `${is_physical === 'true' ? 'true' : 'false'}, ${escapeSqlString(address_line_1, false)}, ` +
                `${escapeSqlString(address_line_2, false)}, ${escapeSqlString(address_line_3, false)}, ` +
                `${escapeSqlString(address_line_4, false)}, ${escapeSqlString(address_line_5, false)}, ` +
                `${escapeSqlString(postcode, false)}, ${escapeSqlString(email, false)}, ${escapeSqlString(phone, false)}, ` +
                `${escapeSqlString(fax, false)}, ${escapeSqlString(website_url, false)}, ${escapeSqlString(website_display_as, false)}, ` +
                `${escapeSqlString(twitter_url, false)}, ${escapeSqlString(facebook_url, false)}, ` +
                `${escapeSqlString(instagram_url, false)}, ${escapeSqlString(linkedin_url, false)}, ` +
                `${escapeSqlString(youtube_url, false)}, ${escapeSqlString(note, false)}, ` +
                `${escapeSqlString(last_synced_at)}, ${escapeSqlString(created_at)}, ` +
                `${escapeSqlString(updated_at)}, ${is_deleted === 'true' ? 'true' : 'false'}, ` +
                `${escapeSqlString(deleted_at, false)})`;

    values.push(row);
  }

  const sql = `-- Data for parliament_member_contacts from production\n` +
              `INSERT INTO "public"."parliament_member_contacts" \n` +
              `("id", "member_id", "contact_type", "contact_type_id", "is_primary", "is_physical", ` +
              `"address_line_1", "address_line_2", "address_line_3", "address_line_4", "address_line_5", ` +
              `"postcode", "email", "phone", "fax", "website_url", "website_display_as", ` +
              `"twitter_url", "facebook_url", "instagram_url", "linkedin_url", "youtube_url", "note", ` +
              `"last_synced_at", "created_at", "updated_at", "is_deleted", "deleted_at")\n` +
              `VALUES\n${values.join(',\n')};\n\n`;

  return sql;
}

// Main execution
const portraitsCsvPath = path.join(process.env.HOME, 'Downloads', 'parliament_member_portraits_rows (3).csv');
const contactsCsvPath = path.join(process.env.HOME, 'Downloads', 'parliament_member_contacts_rows (2).csv');
const outputPath = path.join(__dirname, '..', 'supabase', 'parliament_seed_data.sql');

try {
  console.log('Converting portraits CSV...');
  const portraitsSql = convertPortraitsCSV(portraitsCsvPath);
  console.log(`Generated ${portraitsSql.split('\n').length} lines for portraits`);

  console.log('Converting contacts CSV...');
  const contactsSql = convertContactsCSV(contactsCsvPath);
  console.log(`Generated ${contactsSql.split('\n').length} lines for contacts`);

  const fullSql = portraitsSql + contactsSql;

  fs.writeFileSync(outputPath, fullSql, 'utf-8');
  console.log(`\nSuccessfully wrote SQL to: ${outputPath}`);
  console.log(`Total size: ${(fullSql.length / 1024 / 1024).toFixed(2)} MB`);
} catch (error) {
  console.error('Error:', error.message);
  process.exit(1);
}
