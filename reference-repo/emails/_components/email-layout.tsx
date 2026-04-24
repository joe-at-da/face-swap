import {
  Body,
  Container,
  Head,
  Html,
  Img,
  Link,
  Preview,
  Section,
  Tailwind,
  Text,
} from "@react-email/components";
import { pixelBasedPreset } from "@react-email/components";

interface EmailLayoutProps {
  preview: string;
  children: React.ReactNode;
  appUrl: string;
}

export function EmailLayout({ preview, children, appUrl }: EmailLayoutProps) {
  // Extract origin (protocol + host) from appUrl, falling back to appUrl as-is
  // for GoTrue template variables like "{{ .SiteURL }}" that aren't valid URLs
  let baseUrl: string;
  try {
    baseUrl = new URL(appUrl).origin;
  } catch {
    baseUrl = appUrl;
  }

  return (
    <Html>
      <Tailwind config={{ presets: [pixelBasedPreset] }}>
        <Head />
        <Preview>{preview}</Preview>
        <Body className="bg-[#f4f4f5] my-[0px] mx-[0px] py-[32px] px-[0px]">
          <Container className="max-w-[600px] mx-auto">
            {/* Header */}
            <Section className="bg-[#1c1a46] rounded-t-[8px] py-[32px] px-[32px] text-center">
              <Img
                src={`${baseUrl}/emails/parlament-connect-logo-white.png`}
                alt="Parliament Connect"
                height="48"
                className="mx-auto"
                style={{ margin: "0 auto" }}
              />
            </Section>

            {/* Body */}
            <Section className="bg-[#ffffff] pt-[40px] pb-[32px] px-[40px]">
              {children}
            </Section>

            {/* Support line */}
            <Section className="bg-[#ffffff] pb-[32px] px-[40px]">
              <Text
                className="text-[13px] leading-[20px] text-[#9ca3af] text-center mt-[0px] mb-[0px]"
                style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
              >
                Having trouble? Contact our support team at{" "}
                <Link
                  href="mailto:support@parliamentconnect.com"
                  className="text-[#1c1a46] underline"
                >
                  support@parliamentconnect.com
                </Link>
              </Text>
            </Section>

            {/* Footer */}
            <Section
              className="bg-[#f9fafb] rounded-b-[8px] py-[32px] px-[40px] text-center"
              style={{ borderTop: "0.8px solid #e5e7eb" }}
            >
              <Text
                className="text-[11px] leading-[16px] text-[#9ca3af] mt-[0px] mb-[16px]"
                style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
              >
                You&apos;re receiving this email because you have an active
                Parliament Connect account.
              </Text>
              <Link
                href={`${baseUrl}/dashboard/settings`}
                className="text-[11px] text-[#6d747d] underline"
                style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
              >
                Manage email preferences
              </Link>
              <Text
                className="text-[11px] leading-[16px] text-[#9ca3af] mt-[16px] mb-[0px]"
                style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
              >
                &copy; 2026 Parliament Connect. All rights reserved.
              </Text>
            </Section>
          </Container>
        </Body>
      </Tailwind>
    </Html>
  );
}
