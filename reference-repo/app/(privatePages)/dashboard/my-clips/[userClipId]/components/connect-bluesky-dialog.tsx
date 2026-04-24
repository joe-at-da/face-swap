"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { RefreshCw } from "lucide-react";
import {
    blueskyConnectionSchema,
    type BlueskyConnectionData,
} from "@/schemas/socialMediaSchema";
import { toast } from "sonner";
import { connectBlueskyAccountAction } from "@/app/actions/postizActions";

interface ConnectBlueskyDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onRefetch?: () => void;
}

export function ConnectBlueskyDialog({
    open,
    onOpenChange,
    onRefetch,
}: ConnectBlueskyDialogProps) {
    const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);

    const blueskyForm = useForm<BlueskyConnectionData>({
        resolver: zodResolver(blueskyConnectionSchema),
        defaultValues: {
            service: "https://bsky.social",
            identifier: "",
            password: "",
        },
    });

    const handleBlueskyConnect = async (data: BlueskyConnectionData) => {
        setConnectingPlatform("bluesky");
        try {
            const result = await connectBlueskyAccountAction(
                data.service,
                data.identifier,
                data.password
            );

            if (result.error) {
                toast.error(result.error);
                return;
            }

            toast.success("Bluesky account connected successfully");
            if (onRefetch) {
                onRefetch();
            }
            blueskyForm.reset();
            onOpenChange(false);
        } catch (err) {
            toast.error(
                `Failed to connect Bluesky: ${err instanceof Error ? err.message : "Unknown error"}`
            );
        } finally {
            setConnectingPlatform(null);
        }
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(open) => {
                if (!open) {
                    setConnectingPlatform(null);
                    blueskyForm.reset();
                }
                onOpenChange(open);
            }}
        >
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Connect Bluesky</DialogTitle>
                    <DialogDescription>
                        Enter your Bluesky account credentials to connect your account.
                    </DialogDescription>
                </DialogHeader>
                <Form {...blueskyForm}>
                    <form
                        onSubmit={blueskyForm.handleSubmit(handleBlueskyConnect)}
                        className="space-y-4"
                    >
                        <FormField
                            control={blueskyForm.control}
                            name="service"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Service</FormLabel>
                                    <FormControl>
                                        <Input
                                            {...field}
                                            placeholder="https://bsky.social"
                                            disabled={!!connectingPlatform}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={blueskyForm.control}
                            name="identifier"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Identifier</FormLabel>
                                    <FormControl>
                                        <Input
                                            {...field}
                                            placeholder="example.bsky.social"
                                            disabled={!!connectingPlatform}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={blueskyForm.control}
                            name="password"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Password</FormLabel>
                                    <FormControl>
                                        <Input
                                            {...field}
                                            type="password"
                                            placeholder="Enter your password"
                                            disabled={!!connectingPlatform}
                                        />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <DialogFooter>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                    setConnectingPlatform(null);
                                    blueskyForm.reset();
                                    onOpenChange(false);
                                }}
                                disabled={!!connectingPlatform}
                                className="font-sans text-base border-1 border-primary"
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                disabled={!!connectingPlatform}
                                className="bg-primary text-primary-foreground hover:bg-primary/90 font-sans text-base"
                            >
                                {connectingPlatform ? (
                                    <>
                                        <RefreshCw className="h-3 w-3 mr-2 animate-spin" />
                                        Connecting...
                                    </>
                                ) : (
                                    "Connect"
                                )}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}

