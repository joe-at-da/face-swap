#!/usr/bin/env tsx

/**
 * Test script to verify which MP image sources actually work
 * Tests various public sources to find ones that return images
 */

import { chromium, Page } from "playwright";
import { createClient } from "@supabase/supabase-js";
import { Database } from "@/supabaseTypes";

// Create Supabase client for scripts
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "http://127.0.0.1:55321";
const supabaseKey = process.env.SUPABASE_SERVICE_KEY || "";

const supabaseAdminClient = createClient<Database>(
  supabaseUrl,
  supabaseKey ||
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  },
);

const TEST_MEMBER_ID = 5296; // Freddie van Mierlo
const NAVIGATION_TIMEOUT = 30000;

interface SourceTestResult {
  sourceName: string;
  url: string;
  method: "api" | "scraping";
  success: boolean;
  imagesFound: number;
  imageUrls: string[];
  error?: string;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function testSource(
  page: Page,
  sourceName: string,
  url: string,
  method: "api" | "scraping",
  extractImages: (page: Page) => Promise<string[]>,
): Promise<SourceTestResult> {
  const result: SourceTestResult = {
    sourceName,
    url,
    method,
    success: false,
    imagesFound: 0,
    imageUrls: [],
  };

  try {
    console.log(`\n[Testing] ${sourceName}...`);
    console.log(`  URL: ${url}`);
    console.log(`  Method: ${method}`);

    if (method === "api") {
      // Test API endpoint
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        // Try to extract image URLs from API response
        const images = extractImagesFromApiResponse(data);
        result.imagesFound = images.length;
        result.imageUrls = images;
        result.success = images.length > 0;
      } else {
        result.error = `HTTP ${response.status}`;
      }
    } else {
      // Test web scraping
      try {
        const response = await page.goto(url, {
          waitUntil: "domcontentloaded",
          timeout: NAVIGATION_TIMEOUT,
        });

        if (response && response.status() >= 400) {
          result.error = `HTTP ${response.status()}`;
          return result;
        }

        await sleep(2000); // Wait for dynamic content

        const images = await extractImages(page);
        result.imagesFound = images.length;
        result.imageUrls = images;
        result.success = images.length > 0;
      } catch (error) {
        result.error = error instanceof Error ? error.message : String(error);
      }
    }

    console.log(`  Result: ${result.success ? "✓ SUCCESS" : "✗ FAILED"}`);
    console.log(`  Images found: ${result.imagesFound}`);
    if (result.error) {
      console.log(`  Error: ${result.error}`);
    }
    if (result.imagesFound > 0 && result.imagesFound <= 5) {
      console.log(`  Sample URLs: ${result.imageUrls.slice(0, 3).join(", ")}`);
    }
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
    console.log(`  Result: ✗ FAILED`);
    console.log(`  Error: ${result.error}`);
  }

  return result;
}

function extractImagesFromApiResponse(data: unknown): string[] {
  const images: string[] = [];

  // Try to find image URLs in API response
  function traverse(obj: unknown): void {
    if (
      typeof obj === "string" &&
      obj.includes("http") &&
      (obj.includes(".jpg") || obj.includes(".png") || obj.includes(".jpeg"))
    ) {
      images.push(obj);
    } else if (Array.isArray(obj)) {
      obj.forEach(traverse);
    } else if (obj && typeof obj === "object") {
      Object.values(obj).forEach(traverse);
    }
  }

  traverse(data);
  return Array.from(new Set(images));
}

async function main() {
  console.log("=".repeat(80));
  console.log("MP Image Sources Test Script");
  console.log("=".repeat(80));
  console.log(`Testing with Member ID: ${TEST_MEMBER_ID}`);

  // Fetch MP data
  const { data: mp, error } = await supabaseAdminClient
    .from("parliament_members")
    .select("member_id, display_name, given_name, family_name")
    .eq("member_id", TEST_MEMBER_ID)
    .single();

  if (error || !mp) {
    console.error("Error fetching MP:", error);
    process.exit(1);
  }

  console.log(`MP: ${mp.display_name || `${mp.given_name} ${mp.family_name}`}`);
  console.log("=".repeat(80));

  const mpName = mp.display_name || `${mp.given_name} ${mp.family_name}`;
  const searchQuery = encodeURIComponent(mpName);

  const browser = await chromium.launch({
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
    ],
  });

  const context = await browser.newContext({
    userAgent:
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    viewport: { width: 1920, height: 1080 },
  });

  const page = await context.newPage();
  const results: SourceTestResult[] = [];

  try {
    // Test 1: UK Parliament Official Portraits
    results.push(
      await testSource(
        page,
        "UK Parliament Official Portraits",
        `https://members.parliament.uk/member/${TEST_MEMBER_ID}/portrait`,
        "scraping",
        async (p) => {
          const images = await p.$$eval("img", (imgs) => {
            return imgs
              .map((img) => {
                const src =
                  img.getAttribute("src") || img.getAttribute("data-src");
                if (
                  src &&
                  (src.includes("portrait") || src.includes("member"))
                ) {
                  return src.startsWith("http")
                    ? src
                    : `https://members.parliament.uk${src}`;
                }
                return null;
              })
              .filter(
                (url): url is string =>
                  url !== null &&
                  (url.includes(".jpg") || url.includes(".png")),
              );
          });
          return images;
        },
      ),
    );

    // Test 2: Wikimedia Commons API
    const wikimediaApiUrl = `https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=${searchQuery}+UK+Parliament&srnamespace=6&srlimit=20&origin=*`;
    try {
      console.log(`\n[Testing] Wikimedia Commons API...`);
      console.log(`  URL: ${wikimediaApiUrl}`);
      console.log(`  Method: api`);

      const response = await fetch(wikimediaApiUrl);
      if (response.ok) {
        const data = await response.json();
        const imageUrls: string[] = [];

        if (data.query && data.query.search) {
          for (const item of data.query.search) {
            const title = item.title;
            if (title && title.startsWith("File:")) {
              // Get image URL from file title
              const fileUrl = `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(
                title.replace("File:", ""),
              )}`;
              imageUrls.push(fileUrl);
            }
          }
        }

        const result: SourceTestResult = {
          sourceName: "Wikimedia Commons API",
          url: wikimediaApiUrl,
          method: "api",
          success: imageUrls.length > 0,
          imagesFound: imageUrls.length,
          imageUrls: imageUrls,
        };

        console.log(`  Result: ${result.success ? "✓ SUCCESS" : "✗ FAILED"}`);
        console.log(`  Images found: ${result.imagesFound}`);
        results.push(result);
      } else {
        results.push({
          sourceName: "Wikimedia Commons API",
          url: wikimediaApiUrl,
          method: "api",
          success: false,
          imagesFound: 0,
          imageUrls: [],
          error: `HTTP ${response.status}`,
        });
      }
    } catch (error) {
      results.push({
        sourceName: "Wikimedia Commons API",
        url: wikimediaApiUrl,
        method: "api",
        success: false,
        imagesFound: 0,
        imageUrls: [],
        error: error instanceof Error ? error.message : String(error),
      });
    }

    // Test 3: Wikimedia Commons Search Page
    results.push(
      await testSource(
        page,
        "Wikimedia Commons Search",
        `https://commons.wikimedia.org/w/index.php?search=${searchQuery}+UK+Parliament&title=Special:Search&go=Go&ns0=1&ns6=1&ns14=1`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='commons.wikimedia.org']",
            (imgs) => {
              return imgs
                .map((img) => {
                  let src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  if (src && src.includes("/thumb/")) {
                    src = src
                      .replace(/\/thumb\//, "/")
                      .split("/")
                      .slice(0, -1)
                      .join("/");
                  }
                  if (src && src.startsWith("//")) {
                    src = "https:" + src;
                  }
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 4: Openverse (CC Search)
    results.push(
      await testSource(
        page,
        "Openverse (CC Search)",
        `https://openverse.org/search/?q=${searchQuery}&type=image`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='openverse.org'], img[data-src*='openverse.org']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null && url.startsWith("http"),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 5: TheyWorkForYou
    results.push(
      await testSource(
        page,
        "TheyWorkForYou",
        `https://www.theyworkforyou.com/mp/${TEST_MEMBER_ID}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval("img", (imgs) => {
            return imgs
              .map((img) => {
                const src =
                  img.getAttribute("src") || img.getAttribute("data-src");
                if (
                  src &&
                  (src.includes("theyworkforyou") || src.includes("portrait"))
                ) {
                  return src.startsWith("http")
                    ? src
                    : `https://www.theyworkforyou.com${src}`;
                }
                return null;
              })
              .filter(
                (url): url is string =>
                  url !== null &&
                  (url.includes(".jpg") || url.includes(".png")),
              );
          });
          return images;
        },
      ),
    );

    // Test 6: BBC News Search
    results.push(
      await testSource(
        page,
        "BBC News Search",
        `https://www.bbc.co.uk/search?q=${searchQuery}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval("img[src*='bbc.co.uk']", (imgs) => {
            return imgs
              .map((img) => {
                const src =
                  img.getAttribute("src") || img.getAttribute("data-src");
                return src;
              })
              .filter(
                (url): url is string =>
                  url !== null &&
                  url.startsWith("http") &&
                  (url.includes(".jpg") || url.includes(".png")),
              );
          });
          return images;
        },
      ),
    );

    // Test 7: Guardian Search
    results.push(
      await testSource(
        page,
        "Guardian Search",
        `https://www.theguardian.com/search?q=${searchQuery}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval("img[src*='guardian']", (imgs) => {
            return imgs
              .map((img) => {
                const src =
                  img.getAttribute("src") || img.getAttribute("data-src");
                return src;
              })
              .filter(
                (url): url is string =>
                  url !== null &&
                  url.startsWith("http") &&
                  (url.includes(".jpg") || url.includes(".png")),
              );
          });
          return images;
        },
      ),
    );

    // Test 8: Europeana
    results.push(
      await testSource(
        page,
        "Europeana",
        `https://www.europeana.eu/en/search?q=${searchQuery}&qf=TYPE:IMAGE`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='europeana'], img[data-src*='europeana']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null && url.startsWith("http"),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 9: Google Images (via DuckDuckGo image search)
    results.push(
      await testSource(
        page,
        "DuckDuckGo Images",
        `https://duckduckgo.com/?q=${searchQuery}+UK+Parliament+MP&iax=images&ia=images`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[data-src], img.tile--img__img",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("data-src") || img.getAttribute("src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") ||
                      url.includes(".png") ||
                      url.includes(".jpeg")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 10: Bing Images
    results.push(
      await testSource(
        page,
        "Bing Images",
        `https://www.bing.com/images/search?q=${searchQuery}+UK+Parliament+MP`,
        "scraping",
        async (p) => {
          const images = await p.$$eval("img.mimg", (imgs) => {
            return imgs
              .map((img) => {
                const src =
                  img.getAttribute("src") || img.getAttribute("data-src");
                return src;
              })
              .filter(
                (url): url is string =>
                  url !== null &&
                  url.startsWith("http") &&
                  (url.includes(".jpg") ||
                    url.includes(".png") ||
                    url.includes(".jpeg")),
              );
          });
          return images;
        },
      ),
    );

    // Test 11: Reuters Search
    results.push(
      await testSource(
        page,
        "Reuters Search",
        `https://www.reuters.com/search/news?blob=${searchQuery}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='reuters'], img[data-src*='reuters']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 12: AP Images (Associated Press)
    results.push(
      await testSource(
        page,
        "AP Images",
        `https://www.apimages.com/search?q=${searchQuery}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='apimages'], img[data-src*='apimages']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 13: Getty Images (public search)
    results.push(
      await testSource(
        page,
        "Getty Images Search",
        `https://www.gettyimages.com/photos/${searchQuery.replace(
          /\s+/g,
          "-",
        )}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='gettyimages'], img[data-src*='gettyimages']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 14: Alamy (stock photos)
    results.push(
      await testSource(
        page,
        "Alamy Search",
        `https://www.alamy.com/stock-photo/${searchQuery.replace(
          /\s+/g,
          "-",
        )}.html`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='alamy'], img[data-src*='alamy']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 15: Shutterstock (public search)
    results.push(
      await testSource(
        page,
        "Shutterstock Search",
        `https://www.shutterstock.com/search/${searchQuery.replace(
          /\s+/g,
          "-",
        )}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='shutterstock'], img[data-src*='shutterstock']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 16: Unsplash (free stock photos)
    results.push(
      await testSource(
        page,
        "Unsplash Search",
        `https://unsplash.com/s/photos/${searchQuery.replace(/\s+/g, "-")}`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='unsplash'], img[data-src*='unsplash']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 17: Pexels (free stock photos)
    results.push(
      await testSource(
        page,
        "Pexels Search",
        `https://www.pexels.com/search/${searchQuery.replace(/\s+/g, "%20")}/`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='pexels'], img[data-src*='pexels']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );

    // Test 18: Pixabay (free images)
    results.push(
      await testSource(
        page,
        "Pixabay Search",
        `https://pixabay.com/images/search/${searchQuery.replace(
          /\s+/g,
          "%20",
        )}/`,
        "scraping",
        async (p) => {
          const images = await p.$$eval(
            "img[src*='pixabay'], img[data-src*='pixabay']",
            (imgs) => {
              return imgs
                .map((img) => {
                  const src =
                    img.getAttribute("src") || img.getAttribute("data-src");
                  return src;
                })
                .filter(
                  (url): url is string =>
                    url !== null &&
                    url.startsWith("http") &&
                    (url.includes(".jpg") || url.includes(".png")),
                );
            },
          );
          return images;
        },
      ),
    );
  } finally {
    await page.close();
    await context.close();
    await browser.close();
  }

  // Print summary
  console.log("\n" + "=".repeat(80));
  console.log("TEST RESULTS SUMMARY");
  console.log("=".repeat(80));

  const successful = results.filter((r) => r.success);
  const failed = results.filter((r) => !r.success);

  console.log(`\n✓ Successful sources: ${successful.length}`);
  successful.forEach((r) => {
    console.log(`  - ${r.sourceName}: ${r.imagesFound} images (${r.method})`);
  });

  console.log(`\n✗ Failed sources: ${failed.length}`);
  failed.forEach((r) => {
    console.log(
      `  - ${r.sourceName}: ${r.error || "No images found"} (${r.method})`,
    );
  });

  console.log("\n" + "=".repeat(80));
  console.log("RECOMMENDED SOURCES TO USE:");
  console.log("=".repeat(80));

  if (successful.length > 0) {
    successful.forEach((r) => {
      console.log(`\n${r.sourceName}:`);
      console.log(`  URL Pattern: ${r.url}`);
      console.log(`  Method: ${r.method}`);
      console.log(`  Images Found: ${r.imagesFound}`);
    });
  } else {
    console.log("\nNo working sources found. Manual investigation needed.");
  }

  console.log("\n");
}

if (require.main === module) {
  main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
}
