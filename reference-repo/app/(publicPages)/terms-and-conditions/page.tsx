import { FileText } from "lucide-react";
import { getTermsHtml } from "@/lib/legal/fibery-documents";
import { LegalArticle } from "@/app/(publicPages)/components/legal-article";

export const revalidate = 60;

export default async function TermsAndConditionsPage() {
  const result = await getTermsHtml();

  return (
    <div className="flex-1 px-4 py-12 sm:py-16">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <div className="text-center space-y-3">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
            <FileText className="h-7 w-7 text-primary" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Terms &amp; Conditions
          </h1>
          <p className="text-muted-foreground text-base sm:text-lg">
            Please review our terms before using Parliament Connect
          </p>
        </div>

        {result.ok ? (
          <LegalArticle html={result.html} />
        ) : (
          <div className="rounded-2xl border border-dashed border-border bg-muted/30 p-6 text-sm leading-6 text-muted-foreground">
            {result.reason}
          </div>
        )}
      </div>
    </div>
  );
}
