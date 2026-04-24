import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { SignInForm } from "./components/sign-in-form";

export default function SignInPage() {
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
              Welcome Back
            </h1>
            <p className="text-muted-foreground text-base md:text-lg">
              Sign in to Parliament Connect
            </p>
          </div>

          {/* Sign In Card */}
          <Card className="border-border/50 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-xl">Sign in to your account</CardTitle>
              <CardDescription>
                Enter your email to receive a verification code
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SignInForm />
            </CardContent>
          </Card>

          {/* Parliament Member Badge */}
          <div className="text-center space-y-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  Exclusive Platform
                </span>
              </div>
            </div>

            <Badge variant="secondary" className="px-4 py-1.5">
              <Users className="mr-2 h-3 w-3" />
              MPs with @parliament.gov.uk emails get verified access
            </Badge>
          </div>

          {/* Sign Up Link */}
          <div className="text-center text-sm">
            <span className="text-muted-foreground">Don&apos;t have an account? </span>
            <Link
              href="/signup"
              className="font-medium text-secondary-foreground hover:text-primary/90 hover:underline transition-colors"
            >
              Sign up
            </Link>
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