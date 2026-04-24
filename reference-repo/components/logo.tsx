
import Link from "next/link";
import Image from "next/image";

interface LogoProps {
  className?: string;
}

export function Logo({ className = "" }: LogoProps) {
  return (
    <Link href="/" className={`flex items-center space-x-2 ${className}`}>
      <Image src="/parlament-connect-logo.svg" alt="Logo" width={185} height={64} className="w-full h-auto" />
    </Link>
  );
}