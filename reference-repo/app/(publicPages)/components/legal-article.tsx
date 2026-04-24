import { cn } from "@/lib/utils";

const LEGAL_ARTICLE_CLASS_NAME =
  "max-w-none text-[15px] leading-7 text-foreground " +
  "[&_a]:break-words [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 " +
  "[&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground " +
  "[&_h1]:mt-10 [&_h1:first-child]:mt-0 [&_h1]:text-3xl [&_h1]:font-semibold [&_h1]:tracking-tight " +
  "[&_h2]:mt-8 [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:tracking-tight " +
  "[&_h3]:mt-6 [&_h3]:text-xl [&_h3]:font-semibold " +
  "[&_hr]:my-8 [&_hr]:border-border " +
  "[&_img]:h-auto [&_img]:max-w-full [&_img]:rounded-2xl " +
  "[&_li]:ml-6 [&_li]:pl-1 " +
  "[&_ol]:my-4 [&_ol]:list-decimal [&_ol]:space-y-2 " +
  "[&_p]:my-4 " +
  "[&_table]:my-6 [&_table]:w-full [&_table]:border-collapse [&_table]:overflow-hidden " +
  "[&_td]:border [&_td]:border-border [&_td]:p-3 [&_td]:align-top " +
  "[&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:p-3 [&_th]:text-left " +
  "[&_ul]:my-4 [&_ul]:list-disc [&_ul]:space-y-2";

type LegalArticleProps = {
  html: string;
  className?: string;
};

export function LegalArticle({ html, className }: LegalArticleProps) {
  return (
    <article
      className={cn(LEGAL_ARTICLE_CLASS_NAME, className)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
