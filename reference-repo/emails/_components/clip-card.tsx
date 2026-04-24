import { Column, Img, Row, Section, Text } from "@react-email/components";
import type { ClipData } from "@/emails/_components/types";

type ClipCardProps = ClipData;

export function ClipCard({
  title,
  description,
  image,
  duration,
}: ClipCardProps) {
  return (
    <Section className="mb-[32px]">
      {/* Thumbnail */}
      <Img
        src={image}
        alt={title}
        width="100%"
        style={{
          display: "block",
          width: "100%",
          borderRadius: "8px",
        }}
      />

      {/* Title | Duration badge */}
      <Row>
        <Column
          className="align-top"
          style={{ paddingTop: "8px", paddingBottom: "4px" }}
        >
          <Text
            className="text-[18px] font-bold leading-[24px] text-[#1c1a46] mt-[0px] mb-[0px]"
            style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
          >
            {title}
          </Text>
        </Column>
        <Column
          className="align-top"
          style={{
            paddingTop: "10px",
            whiteSpace: "nowrap",
            width: "70px",
            textAlign: "right",
          }}
        >
          <div
            style={{
              display: "inline-block",
              backgroundColor: "#1c1a46",
              color: "#ffffff",
              borderRadius: "4px",
              padding: "2px 8px",
              fontSize: "12px",
              fontWeight: "500",
              fontFamily: "Arial, Helvetica, sans-serif",
              lineHeight: "18px",
            }}
          >
            {duration}
          </div>
        </Column>
      </Row>

      {/* Description */}
      {description && (
        <Text
          className="text-[14px] leading-[22px] text-[#6d747d] mt-[0px] mb-[0px]"
          style={{ fontFamily: "Arial, Helvetica, sans-serif" }}
        >
          {description.length > 150
            ? `${description.slice(0, 150)}...`
            : description}
        </Text>
      )}
    </Section>
  );
}
