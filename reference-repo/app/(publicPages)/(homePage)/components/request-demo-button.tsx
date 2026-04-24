import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import Link from "next/link";

interface RequestDemoButtonProps {
  variant?: "default" | "outline";
  className?: string;
  size?: "default" | "sm" | "lg" | "icon";
}

export function RequestDemoButton({
  variant = "default",
  className = "",
  size = "lg",
}: RequestDemoButtonProps) {
  return (
    <Link href="/contact">
      <Button
        size={size}
        variant={variant}
        className={`min-h-[48px] px-10 text-lg font-semibold ${className}`}
      >
        Request Free Demo <ArrowRight className="ml-2 w-5 h-5" />
      </Button>
    </Link>
  );
}
