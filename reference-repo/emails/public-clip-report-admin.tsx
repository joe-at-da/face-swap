import { Button, Section, Text } from "@react-email/components";
import { EmailLayout } from "@/emails/_components/email-layout";
import type { PublicClipReportAdminEmailProps } from "@/emails/_components/types";

export const subject = "Clip reported for review";

export function PublicClipReportAdminEmail({
  recipientName,
  clipTitle,
  clipId,
  reason,
  submittedAt,
  detailsExcerpt,
  clipUrl,
  appUrl,
}: PublicClipReportAdminEmailProps) {
  return (
    <EmailLayout
      preview={`A public clip has been reported: ${clipTitle}`}
      appUrl={appUrl}
    >
      <Text
        className="text-[28px] font-bold leading-[36px] text-[#1c1a46] mt-[0px] mb-[8px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        Public Clip Report Received
      </Text>

      <Text
        className="text-[16px] leading-[24px] text-[#4b5563] mt-[0px] mb-[32px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        Hi {recipientName}, a public clip has been reported and needs manual
        review.
      </Text>

      {/* Report details card */}
      <Section
        className="mb-[32px]"
        style={{
          backgroundColor: "#f9fafb",
          border: "1px solid #e5e7eb",
          borderRadius: "8px",
          padding: "20px",
        }}
      >
        <Text
          className="text-[14px] leading-[22px] text-[#374151] mt-[0px] mb-[12px]"
          style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
        >
          <strong>Clip title:</strong> {clipTitle}
        </Text>
        <Text
          className="text-[14px] leading-[22px] text-[#374151] mt-[0px] mb-[12px]"
          style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
        >
          <strong>Clip ID:</strong> {clipId}
        </Text>
        <Text
          className="text-[14px] leading-[22px] text-[#374151] mt-[0px] mb-[12px]"
          style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
        >
          <strong>Reason:</strong> {reason}
        </Text>
        <Text
          className="text-[14px] leading-[22px] text-[#374151] mt-[0px] mb-[12px]"
          style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
        >
          <strong>Submitted at:</strong> {submittedAt} UTC
        </Text>
        {detailsExcerpt ? (
          <Text
            className="text-[14px] leading-[22px] text-[#374151] mt-[0px] mb-[0px]"
            style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
          >
            <strong>Reporter details:</strong> {detailsExcerpt}
          </Text>
        ) : (
          <Text
            className="text-[14px] leading-[22px] text-[#6b7280] mt-[0px] mb-[0px]"
            style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
          >
            No additional details were provided.
          </Text>
        )}
      </Section>

      {/* CTA Button */}
      <Section className="text-center mt-[0px] mb-[0px]">
        <Button
          href={clipUrl}
          className="bg-[#1c1a46] text-[#ffffff] text-[16px] font-semibold py-[14px] px-[24px] rounded-[4px] text-center"
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            boxShadow: "2px 2px 4px rgba(131, 94, 243, 0.1)",
            width: "100%",
            boxSizing: "border-box",
          }}
        >
          Review Clip
        </Button>
      </Section>
    </EmailLayout>
  );
}

PublicClipReportAdminEmail.PreviewProps = {
  recipientName: "Admin",
  clipTitle: "Speech on Healthcare Reform",
  clipId: "abc-123-def-456",
  reason: "misleading",
  submittedAt: "24 Mar 2026, 14:30",
  detailsExcerpt:
    "The clip appears to misattribute a statement to the wrong MP.",
  clipUrl: "https://parliamentconnect.com/clips/abc-123-def-456",
  appUrl: "https://parliamentconnect.com",
} satisfies PublicClipReportAdminEmailProps;

export default PublicClipReportAdminEmail;
