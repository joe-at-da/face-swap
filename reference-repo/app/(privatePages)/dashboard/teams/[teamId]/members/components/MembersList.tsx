"use client";

import { useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Crown, Shield, User, MoreVertical, UserMinus } from "lucide-react";
import { toast } from "sonner";
import { SmartAvatar } from "@/components/smart-avatar";
import { updateMemberRole } from "../actions";
import type { TeamMember, TeamRole } from "@/types/teams";

interface MembersListProps {
  members: TeamMember[];
  userRole: TeamRole | null;
  onRemoveMember: (userId: string) => void;
}

export function MembersList({ members, userRole, onRemoveMember }: MembersListProps) {
  const [isPending, startTransition] = useTransition();
  const [updatingMemberId, setUpdatingMemberId] = useState<string | null>(null);

  const userCanManage = userRole === "owner";

  async function handleUpdateRole(userId: string, newRole: "administrator" | "user", teamId: string) {
    setUpdatingMemberId(userId);
    startTransition(async () => {
      const result = await updateMemberRole(teamId, userId, newRole);

      if (result.success) {
        toast.success("Member role updated");
      } else {
        toast.error(result.error || "Failed to update member role");
      }
      setUpdatingMemberId(null);
    });
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "owner":
        return Crown;
      case "administrator":
        return Shield;
      default:
        return User;
    }
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case "owner":
        return "default";
      case "administrator":
        return "secondary";
      default:
        return "outline";
    }
  };

  if (members.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No members found
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {members.map((member) => {
        const Icon = getRoleIcon(member.role);
        const isUpdating = updatingMemberId === member.userId;

        return (
          <div key={member.id} className="flex items-center justify-between py-3 border-b last:border-0">
            <div className="flex items-center gap-3">
              <SmartAvatar
                email={member.email}
                className="h-10 w-10"
              />
              <div>
                <div className="font-medium">{member.email}</div>
                <div className="text-xs text-muted-foreground">
                  Joined {new Date(member.joinedAt).toLocaleDateString()}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant={getRoleBadgeVariant(member.role) as "default" | "secondary" | "outline"} className="flex items-center gap-1">
                <Icon className="h-3 w-3" />
                {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
              </Badge>

              {userCanManage && !member.isOwner && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" disabled={isUpdating || isPending}>
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {member.role !== "administrator" && (
                      <DropdownMenuItem
                        onClick={() => {
                          const teamId = window.location.pathname.split("/")[3];
                          handleUpdateRole(member.userId, "administrator", teamId);
                        }}
                        disabled={isUpdating}
                      >
                        <Shield className="mr-2 h-4 w-4" />
                        Make Administrator
                      </DropdownMenuItem>
                    )}
                    {member.role === "administrator" && (
                      <DropdownMenuItem
                        onClick={() => {
                          const teamId = window.location.pathname.split("/")[3];
                          handleUpdateRole(member.userId, "user", teamId);
                        }}
                        disabled={isUpdating}
                      >
                        <User className="mr-2 h-4 w-4" />
                        Change to User
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => onRemoveMember(member.userId)}
                      className="text-destructive"
                      disabled={isUpdating}
                    >
                      <UserMinus className="mr-2 h-4 w-4" />
                      Remove from Team
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}