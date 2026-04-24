export function ClipPageFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-border mt-12">
      <div className="container mx-auto px-4 md:px-6 lg:px-8 py-6">
        <div className="text-center space-y-1">
          <p className="text-sm text-muted-foreground">
            © {currentYear} Parliament Connect. Making parliamentary proceedings
            accessible to all.
          </p>
          <p className="text-xs text-muted-foreground">
            All content is licensed under the Open Parliament Licence v3.0
          </p>
        </div>
      </div>
    </footer>
  );
}
