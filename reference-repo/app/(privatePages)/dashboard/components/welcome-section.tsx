interface WelcomeSectionProps {
  isParliamentMember: boolean;
}

export function WelcomeSection({ isParliamentMember }: WelcomeSectionProps) {
  return (
    <div className="space-y-2">
      <h2 className="font-serif text-3xl font-bold text-foreground">
        Welcome Back{isParliamentMember && ", MP"}!
      </h2>
      <p className="text-muted-foreground">
        Your parliamentary content hub - create, manage, and share clips
      </p>
    </div>
  );
}