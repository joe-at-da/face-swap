#!/usr/bin/env node

const https = require('https');
const fs = require('fs');
const path = require('path');

/**
 * Parliament Live TV Scraper
 * Scrapes House of Commons session data from parliamentlive.tv
 * Usage: node scrape-parliament-live.js YYYY-MM-DD YYYY-MM-DD
 */

// Helper function to make HTTP requests
function makeRequest(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                resolve(data);
            });
        }).on('error', (err) => {
            reject(err);
        });
    });
}

// Helper function to parse date and add days
function addDays(date, days) {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
}

// Helper function to format date as YYYY-MM-DD
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// Helper function to get dates between start and end (inclusive)
function getDateRange(startDate, endDate) {
    const dates = [];
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    for (let current = start; current <= end; current = addDays(current, 1)) {
        dates.push(formatDate(current));
    }
    
    return dates;
}

// Extract House of Commons event URLs from HTML
function extractHouseOfCommonsEvents(html, eventDate) {
    const events = [];
    
    // Look for links containing "House of Commons"
    const linkPattern = /<a[^>]*href="([^"]*)"[^>]*>([^<]*House of Commons[^<]*)<\/a>/gi;
    let match;
    
    while ((match = linkPattern.exec(html)) !== null) {
        const url = match[1];
        const linkText = match[2].trim();
        
        // Skip BSL (British Sign Language) sessions
        if (linkText.toLowerCase().includes('bsl')) {
            continue;
        }
        
        // Extract event ID from URL pattern /Event/Index/{guid}
        const eventIdMatch = url.match(/\/Event\/Index\/([a-f0-9-]+)/i);
        if (eventIdMatch) {
            const eventId = eventIdMatch[1];
            const fullUrl = url.startsWith('http') ? url : `https://parliamentlive.tv${url}`;
            
            events.push({
                eventId: eventId,
                status: 'pending',
                title: 'House of Commons',
                title_type: 'House of Commons',
                event_url: fullUrl,
                updated_at: eventDate
            });
        }
    }
    
    return events;
}

// Helper function to scrape a single date
async function scrapeSingleDate(date) {
    try {
        const url = `https://parliamentlive.tv/Guide/EpgDay?date=${date}`;
        const html = await makeRequest(url);
        const events = extractHouseOfCommonsEvents(html, date);
        console.log(`Found ${events.length} House of Commons events for ${date}`);
        return events;
    } catch (error) {
        console.error(`Error scraping ${date}:`, error.message);
        return [];
    }
}

// Main scraping function
async function scrapeParliamentLive(startDate, endDate) {
    console.log(`Scraping Parliament Live TV from ${startDate} to ${endDate}`);

    const dates = getDateRange(startDate, endDate);
    const allEvents = [];

    // Process dates in batches of 3 for faster scraping
    const CONCURRENCY_LIMIT = 3;

    for (let i = 0; i < dates.length; i += CONCURRENCY_LIMIT) {
        const batch = dates.slice(i, i + CONCURRENCY_LIMIT);
        const batchNumber = Math.floor(i / CONCURRENCY_LIMIT) + 1;
        const totalBatches = Math.ceil(dates.length / CONCURRENCY_LIMIT);

        console.log(`Scraping batch ${batchNumber}/${totalBatches}: ${batch.join(', ')}`);

        // Process batch concurrently
        const batchResults = await Promise.all(batch.map(scrapeSingleDate));

        // Flatten and add results
        for (const events of batchResults) {
            allEvents.push(...events);
        }

        // Add delay between batches to be respectful to the server
        if (i + CONCURRENCY_LIMIT < dates.length) {
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }

    return allEvents;
}

// Convert events to CSV format
function eventsToCSV(events) {
    const headers = ['eventId', 'status', 'title', 'title_type', 'event_url', 'updated_at'];
    const csvRows = [headers.join(',')];
    
    for (const event of events) {
        const row = [
            event.eventId,
            event.status,
            `"${event.title}"`,
            `"${event.title_type}"`,
            `"${event.event_url}"`,
            event.updated_at
        ];
        csvRows.push(row.join(','));
    }
    
    return csvRows.join('\n');
}

// Save CSV file
function saveCSV(csvContent, filename) {
    const filePath = path.join(__dirname, filename);
    fs.writeFileSync(filePath, csvContent, 'utf8');
    console.log(`CSV saved to: ${filePath}`);
}

// Validate date format
function isValidDate(dateString) {
    const regex = /^\d{4}-\d{2}-\d{2}$/;
    if (!regex.test(dateString)) return false;
    
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date) && dateString === formatDate(date);
}

// Main execution
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length !== 2) {
        console.error('Usage: node scrape-parliament-live.js YYYY-MM-DD YYYY-MM-DD');
        console.error('Example: node scrape-parliament-live.js 2025-04-01 2025-04-07');
        process.exit(1);
    }
    
    const [startDate, endDate] = args;
    
    if (!isValidDate(startDate) || !isValidDate(endDate)) {
        console.error('Invalid date format. Use YYYY-MM-DD');
        process.exit(1);
    }
    
    if (new Date(startDate) > new Date(endDate)) {
        console.error('Start date must be before or equal to end date');
        process.exit(1);
    }
    
    try {
        const events = await scrapeParliamentLive(startDate, endDate);
        
        if (events.length === 0) {
            console.log('No House of Commons events found in the specified date range');
            return;
        }
        
        console.log(`Total events found: ${events.length}`);
        
        // Remove duplicates based on eventId
        const uniqueEvents = events.filter((event, index, self) => 
            index === self.findIndex(e => e.eventId === event.eventId)
        );
        
        console.log(`Unique events: ${uniqueEvents.length}`);
        
        const csvContent = eventsToCSV(uniqueEvents);
        const filename = `parliament-events-${startDate}-to-${endDate}.csv`;
        
        saveCSV(csvContent, filename);
        
    } catch (error) {
        console.error('Script failed:', error.message);
        process.exit(1);
    }
}

// Run the script
if (require.main === module) {
    main();
}

module.exports = { scrapeParliamentLive, eventsToCSV };