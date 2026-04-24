"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
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
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { updateTeamInformation } from "../actions";

const teamFormSchema = z.object({
  name: z.string().min(1, "Team name is required").max(255, "Team name is too long"),
  description: z.string().max(500, "Description is too long").optional(),
});

type TeamFormValues = z.infer<typeof teamFormSchema>;

interface TeamInformationFormProps {
  teamId: string;
  initialName: string;
  initialDescription?: string | null;
}

export function TeamInformationForm({
  teamId,
  initialName,
  initialDescription,
}: TeamInformationFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  const form = useForm<TeamFormValues>({
    resolver: zodResolver(teamFormSchema),
    defaultValues: {
      name: initialName,
      description: initialDescription || "",
    },
  });

  async function onSubmit(values: TeamFormValues) {
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("name", values.name);
      formData.append("description", values.description || "");

      const result = await updateTeamInformation(teamId, formData);

      if (result.success) {
        toast.success("Team information updated successfully");
        // Update form's default values with the new saved values
        form.reset(values);
        // Refresh the page data
        router.refresh();
      } else {
        toast.error(result.error || "Failed to update team information");
      }
    } catch (error) {
      console.error("Error updating team:", error);
      toast.error("An unexpected error occurred");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Information</CardTitle>
        <CardDescription>
          Update your team&apos;s name and description
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Team Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter team name"
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
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
                      placeholder="Enter team description"
                      className="resize-none"
                      rows={3}
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex items-center gap-2 pt-2">
              <Button
                type="submit"
                disabled={isSubmitting || !form.formState.isDirty}
              >
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Changes
              </Button>
              {form.formState.isDirty && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => form.reset()}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
