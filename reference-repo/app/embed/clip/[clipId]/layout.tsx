export default function EmbedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="m-0 p-0 bg-black">
        {children}
      </body>
    </html>
  );
}
