"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  AlertTriangle,
  Trash2,
  Loader2,
  Shield,
  AlertCircle
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";

interface AccountInfo {
  user_id: string;
  email: string;
  created_at: string;
  profile: {
    name: string;
    following_mp: string;
  } | null;
  clips_count: number;
  teams_count: number;
}

export function AccountDangerZone() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [confirmationText, setConfirmationText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [accountInfo, setAccountInfo] = useState<AccountInfo | null>(null);
  const [isLoadingInfo, setIsLoadingInfo] = useState(false);

  const isConfirmationValid = confirmationText === "DELETE_MY_ACCOUNT";

  // Fetch account info when dialog opens
  useEffect(() => {
    const fetchAccountInfo = async () => {
      if (!isDialogOpen) return;

      setIsLoadingInfo(true);
      try {
        const response = await fetch("/api/settings/account");
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch account information");
        }

        setAccountInfo(data.data);
      } catch (error) {
        console.error("Error fetching account info:", error);
        toast.error("Failed to load account information");
      } finally {
        setIsLoadingInfo(false);
      }
    };

    fetchAccountInfo();
  }, [isDialogOpen]);

  const handleDeleteAccount = async () => {
    if (!isConfirmationValid) {
      toast.error("Please type the confirmation text exactly as shown");
      return;
    }

    setIsDeleting(true);

    try {
      const response = await fetch("/api/settings/account", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          confirmation: "DELETE_MY_ACCOUNT",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to delete account");
      }

      toast.success("Account deleted successfully");

      // Use a browser-level navigation so the redirect still completes after the
      // current authenticated app shell has been torn down.
      window.setTimeout(() => {
        window.location.replace("/");
      }, 2000);

    } catch (error) {
      console.error("Error deleting account:", error);
      toast.error(error instanceof Error ? error.message : "Failed to delete account");
      setIsDeleting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  return (
    <Card className="border-destructive/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive pb-4">
          Delete Account
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 ">
        <div className="space-y-2">
          <p className="text-sm text-destructive bg-red-100 p-4 rounded">
            Permanently delete your account and all associated data. <br /> This action cannot be undone.
          </p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete My Account
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Delete Account
              </DialogTitle>
              <DialogDescription>
                This action is permanent and cannot be undone. All your data will be deleted.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {isLoadingInfo ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : accountInfo ? (
                <div className="space-y-3">
                  <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-destructive mb-2">
                      <Shield className="h-4 w-4" />
                      <span className="text-sm font-medium">What will be deleted:</span>
                    </div>
                    <ul className="text-sm space-y-1 ml-6">
                      <li>• Your account ({accountInfo.email})</li>
                      <li>• Your profile information</li>
                      {accountInfo.teams_count > 0 && (
                        <li>• All {accountInfo.teams_count} owned team{accountInfo.teams_count !== 1 ? "s" : ""} (team members will be notified)</li>
                      )}
                      <li>• All {accountInfo.clips_count} created clip{accountInfo.clips_count !== 1 ? "s" : ""} (personal {accountInfo.teams_count > 0 ? "and team " : ""}clips)</li>
                      <li>• All video files associated with your clips</li>
                      <li>• MP following preferences</li>
                      <li>• All associated data and settings</li>
                    </ul>
                  </div>

                  {accountInfo.profile && (
                    <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
                      <div className="font-medium mb-1">Account Summary:</div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>Name: {accountInfo.profile.name}</div>
                        <div>Following: {accountInfo.profile.following_mp}</div>
                        <div>Created: {formatDate(accountInfo.created_at)}</div>
                        <div>Clips: {accountInfo.clips_count}</div>
                        {accountInfo.teams_count > 0 && (
                          <div>Teams: {accountInfo.teams_count}</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-muted/50 p-3 rounded-lg">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm">Unable to load account information</span>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="confirmation" className="text-destructive">
                  Type <code className="bg-muted px-1 rounded">DELETE_MY_ACCOUNT</code> to confirm:
                </Label>
                <Input
                  id="confirmation"
                  value={confirmationText}
                  onChange={(e) => setConfirmationText(e.target.value)}
                  placeholder="Type confirmation text here..."
                  disabled={isDeleting}
                />
              </div>
            </div>

            <DialogFooter className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setIsDialogOpen(false)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteAccount}
                disabled={!isConfirmationValid || isDeleting}
                className="flex items-center gap-2"
              >
                {isDeleting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                {isDeleting ? "Deleting..." : "Delete Account"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
