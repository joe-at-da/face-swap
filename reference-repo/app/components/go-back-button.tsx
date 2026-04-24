'use client';

import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

export function GoBackButton() {
  return (
    <Button variant="outline" size="lg" onClick={() => window.history.back()}>
      <ArrowLeft className="h-4 w-4 mr-2" />
      Go Back
    </Button>
  );
}