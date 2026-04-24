"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { createTeamSchema, CreateTeamData } from "@/schemas/teamSchemas";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { ArrowLeft, Users } from "lucide-react";
import Link from "next/link";
import { useTeamActions } from "@/stores/teamStore";

export function CreateTeamForm() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const teamActions = useTeamActions();

  const form = useForm<CreateTeamData>({
    resolver: zodResolver(createTeamSchema),
    defaultValues: {
      name: "",
      description: "",
    },
  });

  async function onSubmit(data: CreateTeamData) {
    setIsLoading(true);
    try {
      const team = await teamActions.createTeam(data.name, data.description);
      toast.success("Team created successfully!");
      router.push(`/dashboard/teams/${team.id}`);
    } catch (error) {
      console.error("Failed to create team:", error);
      toast.error("Failed to create team. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="container max-w-3xl py-10">
      <div className="mb-8">
        <Link
          href="/dashboard"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Users className="h-6 w-6" />
            <CardTitle>Create a New Team</CardTitle>
          </div>
          <CardDescription>
            Teams allow you to collaborate with others on creating and managing clips.
            As the team owner, you&apos;ll have full control over team settings and members.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Team Name</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g., Parliamentary Research Team"
                        {...field}
                        disabled={isLoading}
                      />
                    </FormControl>
                    <FormDescription>
                      Choose a name that clearly identifies your team.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description (Optional)</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Describe your team's purpose and goals..."
                        className="min-h-[100px]"
                        {...field}
                        disabled={isLoading}
                      />
                    </FormControl>
                    <FormDescription>
                      Help team members understand the team&apos;s objectives.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.back()}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? "Creating..." : "Create Team"}
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      <div className="mt-8 p-6 border rounded-lg bg-muted/50">
        <h3 className="font-semibold mb-2">What happens next?</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>• You&apos;ll become the team owner with full administrative rights</li>
          <li>• You can invite team members via email</li>
          <li>• Team members can collaborate on creating and editing clips</li>
          <li>• You can assign administrator roles to trusted members</li>
          <li>• All team clips are shared among team members</li>
        </ul>
      </div>
    </div>
  );
}