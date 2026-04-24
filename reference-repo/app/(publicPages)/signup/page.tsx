import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Shield } from "lucide-react";
import Link from "next/link";
import { SignUpForm } from "./components/sign-up-form";

interface SignUpPageProps {
  searchParams: Promise<{
    error?: string;
  }>;
}

export default async function SignUpPage({ searchParams }: SignUpPageProps) {
  const { error } = await searchParams;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Back to Home Link */}
      <div className="p-4 md:p-6">
        <Link 
          href="/" 
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to home
        </Link>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-6">
          {/* Logo/Title */}
          <div className="text-center space-y-2">
            <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground">
              Join Parliament Connect
            </h1>
            <p className="text-muted-foreground text-base md:text-lg">
              Transform parliament footage into viral moments
            </p>
          </div>

          {/* Sign Up Card */}
          <Card className="border-border/50 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-xl">Create your account</CardTitle>
              <CardDescription>
                Start your free trial with instant access
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* MP Verification Info */}
              <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <Shield className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-foreground">
                      Parliament Member?
                    </p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      If you have an authorized MP email address, you&apos;ll automatically
                      get verified MP access with exclusive features.
                    </p>
                  </div>
                </div>
              </div>

              <SignUpForm initialErrorCode={error ?? null} />
            </CardContent>
          </Card>

          {/* Features List */}
          <div className="space-y-3">
            <p className="text-center text-sm text-muted-foreground font-medium">
              What you&apos;ll get:
            </p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex items-center space-x-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span className="text-muted-foreground">AI-powered search</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span className="text-muted-foreground">Video editing tools</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span className="text-muted-foreground">MP notifications</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                <span className="text-muted-foreground">Social scheduling</span>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Background Gradient */}
      <div className="fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
        <div className="absolute left-[50%] top-0 h-[600px] w-[600px] -translate-x-[50%] rounded-full bg-gradient-to-r from-primary/20 via-purple-500/10 to-primary/10 blur-[120px]" />
        <div className="absolute right-0 bottom-0 h-[400px] w-[400px] rounded-full bg-gradient-to-br from-primary/10 to-purple-600/5 blur-[100px]" />
      </div>
    </div>
  );
}
