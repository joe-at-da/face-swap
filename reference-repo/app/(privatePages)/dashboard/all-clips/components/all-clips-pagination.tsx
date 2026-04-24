"use client";

import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis,
} from "@/components/ui/pagination";

interface AllClipsPaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function AllClipsPagination({
  currentPage,
  totalPages,
  onPageChange,
}: AllClipsPaginationProps) {
  if (totalPages <= 1) return null;

  const pages: (number | "ellipsis")[] = [];
  const showEllipsis = totalPages > 7;

  if (!showEllipsis) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (currentPage <= 4) {
      for (let i = 2; i <= 5; i++) pages.push(i);
      pages.push("ellipsis");
      pages.push(totalPages);
    } else if (currentPage >= totalPages - 3) {
      pages.push("ellipsis");
      for (let i = totalPages - 4; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push("ellipsis");
      for (let i = currentPage - 1; i <= currentPage + 1; i++) pages.push(i);
      pages.push("ellipsis");
      pages.push(totalPages);
    }
  }

  return (
    <Pagination>
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            href="#"
            onClick={(e) => {
              e.preventDefault();
              if (currentPage > 1) onPageChange(currentPage - 1);
            }}
            className={`[&>span]:hidden ${
              currentPage === 1 ? "pointer-events-none opacity-50" : ""
            }`}
          />
        </PaginationItem>

        {pages.map((item, index) => {
          if (item === "ellipsis") {
            return (
              <PaginationItem key={`ellipsis-${index}`}>
                <PaginationEllipsis />
              </PaginationItem>
            );
          }
          return (
            <PaginationItem key={item}>
              <PaginationLink
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  onPageChange(item);
                }}
                isActive={currentPage === item}
                className={
                  currentPage === item
                    ? "border-0 shadow-none text-foreground hover:text-foreground hover:bg-transparent"
                    : "text-muted-foreground hover:text-foreground"
                }
              >
                {item}
              </PaginationLink>
            </PaginationItem>
          );
        })}

        <PaginationItem>
          <PaginationNext
            href="#"
            onClick={(e) => {
              e.preventDefault();
              if (currentPage < totalPages) onPageChange(currentPage + 1);
            }}
            className={`[&>span]:hidden ${
              currentPage === totalPages
                ? "pointer-events-none opacity-50"
                : ""
            }`}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
