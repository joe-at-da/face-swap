"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  contactSchema,
  productInterestOptions,
  type ContactFormData,
} from "@/schemas/contactSchema";
import { submitContactForm } from "@/app/actions/contact";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  Send,
  ArrowLeft,
} from "lucide-react";

export function ContactForm() {
  const [isSuccess, setIsSuccess] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      contactName: "",
      contactEmail: "",
      phoneNumber: "",
      productInterest: [],
      message: "",
    },
    mode: "onBlur",
  });

  const { isSubmitting } = form.formState;

  async function onSubmit(data: ContactFormData) {
    setServerError(null);
    try {
      const result = await submitContactForm(data);
      if (result.success) {
        setIsSuccess(true);
        form.reset();
      } else {
        setServerError(result.error);
      }
    } catch {
      setServerError("Something went wrong. Please try again.");
    }
  }

  function handleSendAnother() {
    setIsSuccess(false);
    setServerError(null);
    form.reset();
  }

  if (isSuccess) {
    return (
      <div className="rounded-2xl border bg-card p-8 sm:p-10 shadow-sm">
        <div
          role="status"
          aria-live="polite"
          className="flex flex-col items-center gap-5 text-center"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <CheckCircle2 className="h-8 w-8 text-primary" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">Thank you!</h2>
            <p className="text-muted-foreground text-base max-w-sm">
              Thanks for reaching out! We&apos;ll be in touch shortly.
            </p>
          </div>
          <Button variant="outline" onClick={handleSendAnother} className="mt-2">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Send another message
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border bg-card p-6 sm:p-8 shadow-sm space-y-6">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
          {serverError && (
            <Alert variant="destructive" role="alert">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}

          <div className="grid gap-5 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="contactName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Name <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Your full name"
                      autoComplete="name"
                      disabled={isSubmitting}
                      className="text-base h-11"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="contactEmail"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Email <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="email"
                      inputMode="email"
                      placeholder="you@example.com"
                      autoComplete="email"
                      disabled={isSubmitting}
                      className="text-base h-11"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="phoneNumber"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Phone number</FormLabel>
                <FormControl>
                  <Input
                    type="tel"
                    inputMode="tel"
                    placeholder="+44 7700 900000"
                    autoComplete="tel"
                    disabled={isSubmitting}
                    className="text-base h-11"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="productInterest"
            render={() => (
              <FormItem>
                <FormLabel>Which product(s) are you interested in?</FormLabel>
                <div className="flex flex-col gap-3 sm:flex-row sm:gap-5">
                  {productInterestOptions.map((product) => (
                    <FormField
                      key={product}
                      control={form.control}
                      name="productInterest"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-2 space-y-0">
                          <FormControl>
                            <Checkbox
                              checked={field.value?.includes(product)}
                              disabled={isSubmitting}
                              onCheckedChange={(checked) => {
                                const current = field.value ?? [];
                                field.onChange(
                                  checked
                                    ? [...current, product]
                                    : current.filter((v) => v !== product)
                                );
                              }}
                            />
                          </FormControl>
                          <FormLabel className="text-sm font-normal cursor-pointer">
                            {product}
                          </FormLabel>
                        </FormItem>
                      )}
                    />
                  ))}
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="message"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Message <span className="text-destructive">*</span>
                </FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="Tell us how we can help you..."
                    className="text-base resize-y"
                    style={{ fieldSizing: "fixed", minHeight: "140px" }}
                    disabled={isSubmitting}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="submit"
            disabled={isSubmitting}
            className="w-full h-11"
            size="lg"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Send Message
              </>
            )}
          </Button>
        </form>
      </Form>
    </div>
  );
}
