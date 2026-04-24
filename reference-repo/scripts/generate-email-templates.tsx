import { render } from "@react-email/components";
import { createElement } from "react";
import { writeFileSync, mkdirSync } from "fs";
import { MagicLinkEmail } from "../emails/magic-link";
import { OtpSignupEmail } from "../emails/otp-signup";
import { ResetPasswordEmail } from "../emails/reset-password";

const OUTPUT_DIR = "public/emails/templates";

const templates = [
  {
    name: "magic-link",
    component: MagicLinkEmail,
    props: {
      confirmationUrl: "{{ .ConfirmationURL }}",
      token: "{{ .Token }}",
      siteUrl: "{{ .SiteURL }}",
    },
  },
  {
    name: "otp-signup",
    component: OtpSignupEmail,
    props: {
      token: "{{ .Token }}",
      siteUrl: "{{ .SiteURL }}",
    },
  },
  {
    name: "reset-password",
    component: ResetPasswordEmail,
    props: {
      confirmationUrl: "{{ .ConfirmationURL }}",
      siteUrl: "{{ .SiteURL }}",
    },
  },
];

async function generate() {
  mkdirSync(OUTPUT_DIR, { recursive: true });

  for (const { name, component, props } of templates) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const html = await render(createElement(component as any, props as any));
    const outputPath = `${OUTPUT_DIR}/${name}.html`;
    writeFileSync(outputPath, html);
    console.log(`Generated ${outputPath}`);
  }

  console.log(`\nDone! ${templates.length} templates generated in ${OUTPUT_DIR}/`);
}

generate().catch((err) => {
  console.error("Failed to generate email templates:", err);
  process.exit(1);
});
