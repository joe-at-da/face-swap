import { AuthNavHeader } from "@/app/(publicPages)/(homePage)/components/auth-nav-header";
import { FooterSection } from "@/app/(publicPages)/(homePage)/components/footer-section";

export default function PublicPagesLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex min-h-screen flex-col">
            <AuthNavHeader />

            <main id="main-content" className="flex flex-1 flex-col">
                {children}
            </main>

            <FooterSection />
        </div>
    );
}
