import { Button, Section, Text } from "@react-email/components";
import { EmailLayout } from "@/emails/_components/email-layout";
import type { ResetPasswordEmailProps } from "@/emails/_components/types";

export const subject = "Reset your Parliament Connect password";

export function ResetPasswordEmail({
  confirmationUrl,
  siteUrl,
}: ResetPasswordEmailProps) {
  return (
    <EmailLayout
      preview="Reset your Parliament Connect password"
      appUrl={siteUrl}
    >
      <Text
        className="text-[28px] font-bold leading-[36px] text-[#1c1a46] mt-[0px] mb-[8px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        Reset Your Password
      </Text>

      <Text
        className="text-[16px] leading-[24px] text-[#4b5563] mt-[0px] mb-[32px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        We received a request to reset the password for your Parliament Connect
        account. Click the button below to choose a new password.
      </Text>

      {/* CTA Button */}
      <Section className="text-center mt-[32px] mb-[24px]">
        <Button
          href={confirmationUrl}
          className="bg-[#1c1a46] text-[#ffffff] text-[16px] font-semibold py-[14px] px-[24px] rounded-[4px] text-center"
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            boxShadow: "2px 2px 4px rgba(131, 94, 243, 0.1)",
            width: "100%",
            boxSizing: "border-box",
          }}
        >
          Reset Password
        </Button>
      </Section>

      <Text
        className="text-[14px] leading-[20px] text-[#6b7280] mt-[0px] mb-[0px]"
        style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
      >
        If you didn&apos;t request a password reset, you can safely ignore this
        email. Your password will remain unchanged.
      </Text>
    </EmailLayout>
  );
}

ResetPasswordEmail.PreviewProps = {
  confirmationUrl:
    "https://parliamentconnect.com/auth/confirm?token_hash=abc123&type=recovery",
  siteUrl: "https://parliamentconnect.com",
} satisfies ResetPasswordEmailProps;

export default ResetPasswordEmail;
