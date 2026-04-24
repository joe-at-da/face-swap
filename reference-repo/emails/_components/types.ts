export interface ClipData {
  title: string;
  description: string;
  image: string;
  duration: string;
}

export interface NewContentAddedEmailProps {
  clips: ClipData[];
  date: string;
  appUrl: string;
}

export interface MagicLinkEmailProps {
  confirmationUrl?: string;
  token: string;
  siteUrl: string;
}

export interface OtpSignupEmailProps {
  token: string;
  siteUrl: string;
}

export interface ResetPasswordEmailProps {
  confirmationUrl: string;
  siteUrl: string;
}

export interface PublicClipReportAdminEmailProps {
  recipientName: string;
  clipTitle: string;
  clipId: string;
  reason: string;
  submittedAt: string;
  detailsExcerpt: string | null;
  clipUrl: string;
  appUrl: string;
}
