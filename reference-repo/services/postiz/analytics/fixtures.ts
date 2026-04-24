import type {
  AnalyticsFixture,
  AnalyticsFixtureScenario,
  AnalyticsDateRange,
  ChannelAnalyticsPoint,
} from "./types";

function buildSeries(
  range: AnalyticsDateRange,
  values: number[]
): ChannelAnalyticsPoint[] {
  const dateMap: Record<AnalyticsDateRange, string[]> = {
    7: [
      "2026-03-20",
      "2026-03-21",
      "2026-03-22",
      "2026-03-23",
      "2026-03-24",
      "2026-03-25",
      "2026-03-26",
    ],
    30: ["2026-02-25", "2026-03-04", "2026-03-11", "2026-03-18", "2026-03-26"],
    90: ["2025-12-27", "2026-01-26", "2026-02-25", "2026-03-26"],
  };

  return dateMap[range].map((date, index) => ({
    date,
    total: values[index] ?? values[values.length - 1] ?? 0,
  }));
}

export function getAnalyticsFixture(
  scenario: AnalyticsFixtureScenario,
  range: AnalyticsDateRange
): AnalyticsFixture {
  if (scenario === "no_supported_channels") {
    return {
      channels: [],
      metricsByIntegrationId: {},
    };
  }

  const channels = [
    {
      integrationId: "fixture-x-main",
      organizationId: "fixture-org-main",
      platform: "x",
      label: "MP AI on X",
      avatarUrl: null,
    },
    {
      integrationId: "fixture-facebook-main",
      organizationId: "fixture-org-main",
      platform: "facebook",
      label: "MP AI Facebook",
      avatarUrl: null,
    },
    {
      integrationId: "fixture-facebook-secondary",
      organizationId: "fixture-org-main",
      platform: "facebook",
      label: "MP AI Campaign Page",
      avatarUrl: null,
    },
    {
      integrationId: "fixture-youtube-main",
      organizationId: "fixture-org-main",
      platform: "youtube",
      label: "MP AI YouTube",
      avatarUrl: null,
    },
  ] as const;

  const emptyMetrics = scenario === "empty_channel" ? [] : undefined;

  return {
    channels: [...channels],
    metricsByIntegrationId: {
      "fixture-x-main":
        emptyMetrics ??
        [
          {
            label: "IMPRESSION",
            data: buildSeries(range, range === 7 ? [1200, 1400, 1500, 1700, 1800, 1900, 2100] : range === 30 ? [6200, 7100, 7800, 8200, 9100] : [12000, 14500, 17100, 19800]),
            percentageChange: 18.4,
          },
          {
            label: "LIKE",
            data: buildSeries(range, range === 7 ? [60, 70, 75, 88, 90, 102, 110] : range === 30 ? [240, 255, 310, 345, 380] : [490, 555, 630, 715]),
            percentageChange: 9.2,
          },
          {
            label: "RETWEET",
            data: buildSeries(range, range === 7 ? [30, 35, 38, 44, 45, 51, 55] : range === 30 ? [120, 127, 155, 172, 190] : [245, 277, 315, 357]),
            percentageChange: 7.1,
          },
          {
            label: "REPLY",
            data: buildSeries(range, range === 7 ? [15, 18, 19, 22, 23, 26, 28] : range === 30 ? [60, 64, 78, 86, 95] : [122, 139, 158, 179]),
            percentageChange: 5.4,
          },
          {
            label: "QUOTE",
            data: buildSeries(range, range === 7 ? [8, 10, 11, 13, 14, 16, 17] : range === 30 ? [36, 38, 46, 52, 57] : [74, 83, 95, 107]),
            percentageChange: 4.2,
          },
          {
            label: "BOOKMARK",
            data: buildSeries(range, range === 7 ? [7, 7, 7, 9, 8, 10, 10] : range === 30 ? [24, 26, 31, 35, 38] : [49, 56, 62, 72]),
            percentageChange: 3.1,
          },
        ],
      "fixture-facebook-main": [
        {
          label: "IMPRESSION",
          data: buildSeries(range, range === 7 ? [800, 920, 980, 1010, 1100, 1200, 1380] : range === 30 ? [3100, 3600, 3950, 4300, 4700] : [6100, 7200, 8300, 9100]),
          percentageChange: 12.1,
        },
        {
          label: "LIKE",
          data: buildSeries(range, range === 7 ? [31, 34, 37, 40, 43, 47, 51] : range === 30 ? [105, 120, 140, 155, 173] : [205, 230, 255, 295]),
          percentageChange: 6.7,
        },
        {
          label: "RETWEET",
          data: buildSeries(range, range === 7 ? [15, 17, 19, 20, 21, 23, 25] : range === 30 ? [53, 60, 70, 78, 86] : [103, 115, 128, 148]),
          percentageChange: 5.3,
        },
        {
          label: "REPLY",
          data: buildSeries(range, range === 7 ? [8, 9, 10, 10, 11, 12, 13] : range === 30 ? [26, 30, 35, 39, 43] : [51, 58, 64, 74]),
          percentageChange: 3.8,
        },
        {
          label: "QUOTE",
          data: buildSeries(range, range === 7 ? [4, 5, 5, 6, 6, 7, 7] : range === 30 ? [16, 18, 21, 23, 26] : [31, 35, 39, 44]),
          percentageChange: 2.9,
        },
        {
          label: "BOOKMARK",
          data: buildSeries(range, range === 7 ? [3, 3, 3, 3, 4, 4, 5] : range === 30 ? [10, 12, 14, 15, 17] : [20, 22, 24, 29]),
          percentageChange: 2.1,
        },
      ],
      "fixture-facebook-secondary": [
        {
          label: "IMPRESSION",
          data: buildSeries(range, range === 7 ? [320, 350, 390, 420, 450, 480, 530] : range === 30 ? [1400, 1550, 1700, 1820, 1980] : [2500, 2900, 3200, 3600]),
          percentageChange: 8.3,
        },
        {
          label: "LIKE",
          data: buildSeries(range, range === 7 ? [10, 12, 15, 16, 17, 19, 20] : range === 30 ? [48, 54, 60, 66, 75] : [90, 103, 112, 124]),
          percentageChange: 4.8,
        },
        {
          label: "RETWEET",
          data: buildSeries(range, range === 7 ? [5, 6, 7, 8, 8, 9, 10] : range === 30 ? [24, 27, 30, 33, 37] : [45, 51, 56, 62]),
          percentageChange: 3.5,
        },
        {
          label: "REPLY",
          data: buildSeries(range, range === 7 ? [3, 3, 4, 4, 5, 5, 5] : range === 30 ? [12, 14, 15, 17, 19] : [23, 26, 28, 31]),
          percentageChange: 2.2,
        },
        {
          label: "QUOTE",
          data: buildSeries(range, range === 7 ? [1, 2, 2, 2, 2, 3, 3] : range === 30 ? [6, 7, 8, 9, 10] : [11, 13, 14, 16]),
          percentageChange: 1.8,
        },
        {
          label: "BOOKMARK",
          data: buildSeries(range, range === 7 ? [1, 1, 1, 1, 2, 1, 2] : range === 30 ? [5, 6, 7, 7, 8] : [11, 12, 14, 15]),
          percentageChange: 1.2,
        },
      ],
      "fixture-youtube-main": [
        {
          label: "VIEWS",
          data: buildSeries(range, range === 7 ? [110, 140, 180, 210, 260, 320, 380] : range === 30 ? [520, 690, 830, 980, 1160] : [1200, 1550, 1920, 2350]),
          percentageChange: 21.4,
        },
        {
          label: "WATCH_TIME",
          data: buildSeries(range, range === 7 ? [35, 42, 46, 55, 61, 70, 82] : range === 30 ? [180, 220, 265, 310, 370] : [420, 520, 610, 760]),
          percentageChange: 11.6,
        },
      ],
    },
  };
}
