"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Mail,
  Shield,
  User,
  AlertCircle,
  CheckCircle,
  Loader2,
  Copy,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { createTeamInvitation } from "../actions";
import {
  inviteTeamMemberSchema,
  type InviteTeamMemberData,
} from "@/schemas/teamSchemas";

interface InviteFormClientProps {
  teamId: string;
}

export function InviteFormClient({ teamId }: InviteFormClientProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [successMessage, setSuccessMessage] = useState("");
  const [invitationUrl, setInvitationUrl] = useState("");

  const form = useForm<InviteTeamMemberData>({
    resolver: zodResolver(inviteTeamMemberSchema),
    defaultValues: {
      email: "",
      role: "user",
    },
  });

  async function onSubmit(values: InviteTeamMemberData) {
    setSuccessMessage("");
    setInvitationUrl("");

    startTransition(async () => {
      const result = await createTeamInvitation(
        teamId,
        values.email,
        values.role
      );

      if (result.success && result.invitation) {
        setSuccessMessage(`Invitation email sent to ${values.email}`);
        setInvitationUrl(result.invitation.invitation_url);
        form.reset();
        toast.success("Invitation email sent successfully!");
      } else {
        toast.error(result.error || "Failed to create invitation");
      }
    });
  }

  async function copyInvitationUrl() {
    try {
      await navigator.clipboard.writeText(invitationUrl);
      toast.success("Invitation link copied to clipboard!");
    } catch (error) {
      console.error("Failed to copy:", error);
      toast.error("Failed to copy link");
    }
  }

  return (
    <>
      {successMessage && invitationUrl && (
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle className="h-5 w-5 text-primary" />
              {successMessage}
            </CardTitle>
            <CardDescription>
              An invitation email has been sent. You can also share this link
              directly if needed.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Input
                value={invitationUrl}
                readOnly
                className="flex-1 font-mono text-sm"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={copyInvitationUrl}
                title="Copy invitation link"
              >
                <Copy className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="icon"
                asChild
                title="Open invitation link"
              >
                <a
                  href={invitationUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            </div>
            <Alert className="border-muted">
              <Mail className="h-4 w-4" />
              <AlertDescription className="text-sm">
                The invited member will receive an email with instructions to
                join the team. After accepting the invitation, they&apos;ll
                receive a verification email to complete their account setup.
                {process.env.NODE_ENV === "development" && (
                  <span className="block mt-2 font-medium">
                    In development: Check Mailpit at{" "}
                    <a
                      href="http://127.0.0.1:55324"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      http://127.0.0.1:55324
                    </a>{" "}
                    for emails (including invitation emails when Mailjet is
                    configured)
                  </span>
                )}
              </AlertDescription>
            </Alert>
            <div className="flex gap-3">
              <Button
                onClick={() => {
                  setSuccessMessage("");
                  setInvitationUrl("");
                }}
                variant="outline"
                className="flex-1"
              >
                Send Another Invitation
              </Button>
              <Button
                onClick={() =>
                  router.push(`/dashboard/teams/${teamId}/members`)
                }
                className="flex-1"
              >
                Back to Team Members
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {!invitationUrl && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Send Invitation
            </CardTitle>
            <CardDescription>
              Enter the email address and role for the person you want to invite
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-6"
              >
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email Address</FormLabel>
                      <FormControl>
                        <Input
                          type="email"
                          placeholder="colleague@example.com"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        An invitation email will be sent to this address. Please
                        check spam folder if not received.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="role"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Team Role</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a role" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="user">
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4" />
                              Team Member
                            </div>
                          </SelectItem>
                          <SelectItem value="administrator">
                            <div className="flex items-center gap-2">
                              <Shield className="h-4 w-4" />
                              Administrator
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <FormDescription>
                        Administrators can invite and manage team members
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Alert className="border-primary/20 bg-primary/5">
                  <AlertCircle className="h-4 w-4 text-primary" />
                  <AlertDescription className="text-sm">
                    <strong>Important:</strong> Only MPs with @parliament.gov.uk
                    email addresses can sign up directly. Other users can only
                    join through team invitations. The invitation link will be
                    valid for 7 days.
                  </AlertDescription>
                </Alert>

                <div className="flex gap-3">
                  <Button type="submit" disabled={isPending} className="flex-1">
                    {isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending Invitation...
                      </>
                    ) : (
                      <>
                        <Mail className="mr-2 h-4 w-4" />
                        Send Invitation
                      </>
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      router.push(`/dashboard/teams/${teamId}/members`)
                    }
                    disabled={isPending}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}
    </>
  );
}
