import { Section, Text } from "@react-email/components";
import { EmailLayout } from "@/emails/_components/email-layout";
import type { OtpSignupEmailProps } from "@/emails/_components/types";

export const subject = "Your verification code for Parliament Connect";

export function OtpSignupEmail({ token, siteUrl }: OtpSignupEmailProps) {
  return (
    <EmailLayout
      preview={`Your verification code is ${token}`}
      appUrl={siteUrl}
    >
      <Text
        className="text-[28px] font-bold leading-[36px] text-[#1c1a46] mt-[0px] mb-[8px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        Your Verification Code
      </Text>

      <Text
        className="text-[16px] leading-[24px] text-[#4b5563] mt-[0px] mb-[32px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        Enter the code below to verify your Parliament Connect account.
      </Text>

      {/* OTP Code Display */}
      <Section className="text-center mb-[32px]">
        <div
          style={{
            display: "inline-block",
            backgroundColor: "#eff5fc",
            borderRadius: "4px",
            padding: "16px 24px",
            fontSize: "32px",
            fontWeight: "700",
            fontFamily: "Arial, Helvetica, sans-serif",
            color: "#1c1a46",
            lineHeight: "40px",
            letterSpacing: "8px",
          }}
        >
          {token}
        </div>
      </Section>

      <Text
        className="text-[14px] leading-[20px] text-[#6b7280] mt-[0px] mb-[0px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        This code expires in 10 minutes. If you didn&apos;t request this, please
        ignore this email.
      </Text>
    </EmailLayout>
  );
}

OtpSignupEmail.PreviewProps = {
  token: "847293",
  siteUrl: "https://parliamentconnect.com",
} satisfies OtpSignupEmailProps;

export default OtpSignupEmail;
