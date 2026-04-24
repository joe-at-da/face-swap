"use client";

import { useState } from "react";
import { MembersList } from "./MembersList";
import { RemoveMemberDialog } from "./RemoveMemberDialog";
import type {
  TeamMember,
  TeamRole,
} from "@/types/teams";

interface MembersPageClientProps {
  members: TeamMember[];
  userRole: TeamRole | null;
  teamId: string;
}

export function MembersPageClient({
  members,
  userRole,
  teamId,
}: MembersPageClientProps) {
  const [removingMember, setRemovingMember] = useState<string | null>(null);

  return (
    <>
      <MembersList
        members={members}
        userRole={userRole}
        onRemoveMember={setRemovingMember}
      />

      <RemoveMemberDialog
        teamId={teamId}
        userId={removingMember}
        onClose={() => setRemovingMember(null)}
      />
    </>
  );
}
