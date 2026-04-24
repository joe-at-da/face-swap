import { Button, Section, Text } from "@react-email/components";
import { format, parseISO } from "date-fns";
import { ClipCard } from "@/emails/_components/clip-card";
import { EmailLayout } from "@/emails/_components/email-layout";
import type { NewContentAddedEmailProps } from "@/emails/_components/types";

const MAX_CLIPS = 8;

export const subject = "New content added to your Parliament Connect account";

export function NewContentAddedEmail({
  clips,
  date,
  appUrl,
}: NewContentAddedEmailProps) {
  const formattedDate = format(parseISO(date), "EEEE do MMMM yyyy");
  const visibleClips = clips.slice(0, MAX_CLIPS);
  const remainingCount = clips.length - MAX_CLIPS;

  return (
    <EmailLayout
      preview="New clips have been added to your Parliament Connect account"
      appUrl={appUrl}
    >
      <Text
        className="text-[28px] font-bold leading-[36px] text-[#1c1a46] mt-[0px] mb-[8px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        New Content Added
      </Text>

      <Text
        className="text-[16px] leading-[24px] text-[#4b5563] mt-[0px] mb-[32px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        New content has been prepared and added to your Parliament Connect
        account.
      </Text>

      {/* Date badge */}
      <Section className="mb-[24px]">
        <div
          style={{
            display: "inline-block",
            backgroundColor: "#eff5fc",
            borderRadius: "4px",
            padding: "8px 16px",
            fontSize: "14px",
            fontWeight: "500",
            fontFamily: "Arial, Helvetica, sans-serif",
            color: "#1c1a46",
            lineHeight: "20px",
          }}
        >
          {formattedDate}
        </div>
      </Section>

      {/* Clip cards */}
      {visibleClips.map((clip, index) => (
        <ClipCard key={index} {...clip} />
      ))}

      {/* Show remaining count if clips were truncated */}
      {remainingCount > 0 && (
        <Text
          className="text-[14px] leading-[20px] text-[#6b7280] text-center mb-[24px]"
          style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
        >
          +{remainingCount} more clip{remainingCount > 1 ? "s" : ""} available
        </Text>
      )}

      {/* CTA Button */}
      <Section className="text-center mt-[32px] mb-[0px]">
        <Button
          href={appUrl}
          className="bg-[#1c1a46] text-[#ffffff] text-[16px] font-semibold py-[14px] px-[24px] rounded-[4px] text-center"
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            boxShadow: "2px 2px 4px rgba(131, 94, 243, 0.1)",
            width: "100%",
            boxSizing: "border-box",
          }}
        >
          Login to Access New Content
        </Button>
      </Section>
    </EmailLayout>
  );
}

NewContentAddedEmail.PreviewProps = {
  clips: [
    {
      title: "Your Speech on Healthcare Reform",
      description:
        "Questions to the Secretary of State for Health - Your intervention on GP waiting times in your constituency",
      image: "https://placehold.co/600x340/374151/ffffff?text=Healthcare+Reform",
      duration: "2:34",
    },
    {
      title: "PMQs Contribution",
      description:
        "Prime Minister's Questions - Your question regarding local infrastructure investment",
      image: "https://placehold.co/600x340/374151/ffffff?text=PMQs+Contribution",
      duration: "1:43",
    },
  ],
  date: "2026-02-03",
  appUrl: "https://parliamentconnect.com/dashboard/create-clips",
} satisfies NewContentAddedEmailProps;

export default NewContentAddedEmail;
