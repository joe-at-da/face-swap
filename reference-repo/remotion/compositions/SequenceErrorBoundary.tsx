import React from "react";

interface Props {
  children: React.ReactNode;
  itemId: string;
}

interface State {
  hasError: boolean;
  error: string | null;
}

/**
 * Error boundary for individual Sequences in the Remotion composition.
 * Shows an error frame instead of crashing the entire composition.
 */
export class SequenceErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            width: "100%",
            height: "100%",
            backgroundColor: "#1a1a2e",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            color: "#ef4444",
            fontSize: 14,
            gap: 8,
            padding: 16,
          }}
        >
          <span style={{ fontSize: 24 }}>!</span>
          <span>Video unavailable</span>
          <span style={{ color: "#666", fontSize: 11 }}>
            {this.state.error}
          </span>
        </div>
      );
    }

    return this.props.children;
  }
}
