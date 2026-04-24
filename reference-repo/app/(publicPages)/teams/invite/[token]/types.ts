export interface InvitationData {
  id: string;
  email: string;
  role: string;
  team: {
    id: string;
    name: string;
    description: string;
    owner: {
      email: string;
      username: string | null;
      first_name: string | null;
      last_name: string | null;
    };
  };
  invitedBy: {
    email: string;
    username: string | null;
    first_name: string | null;
    last_name: string | null;
  };
  expiresAt: string;
}

export type InvitationStep = "view" | "verify" | "success";
