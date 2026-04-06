import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: string;
}

const styles = {
  card: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 32,
    margin: 16,
    borderRadius: 12,
    background: "#12121a",
    border: "1px solid #2a2a35",
    color: "#e4e4e7",
    minHeight: 120,
  },
  icon: {
    fontSize: 32,
    color: "#ef4444",
    lineHeight: 1,
  },
  heading: {
    margin: 0,
    fontSize: 16,
    fontWeight: 600 as const,
    color: "#e4e4e7",
  },
  message: {
    margin: 0,
    fontSize: 13,
    color: "#a1a1aa",
    textAlign: "center" as const,
    maxWidth: 420,
    lineHeight: 1.5,
  },
  button: {
    marginTop: 8,
    padding: "8px 20px",
    fontSize: 13,
    fontWeight: 500 as const,
    color: "#fff",
    background: "#3b82f6",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
  },
};

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: "" };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const info = errorInfo.componentStack || "";
    this.setState({ errorInfo: info });
    console.error(`[ErrorBoundary${this.props.name ? `:${this.props.name}` : ""}]`, error, info);
    this.props.onError?.(error, errorInfo);
  }

  reset = () => {
    this.setState({ hasError: false, error: null, errorInfo: "" });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback(this.state.error!, this.reset);
    }

    const label = this.props.name ? ` in ${this.props.name}` : "";

    return (
      <div style={styles.card}>
        <span style={styles.icon}>&#9888;</span>
        <h3 style={styles.heading}>Something went wrong{label}</h3>
        <p style={styles.message}>
          {this.state.error?.message || "An unexpected error occurred."}
        </p>
        <button style={styles.button} onClick={this.reset}>
          Try Again
        </button>
      </div>
    );
  }
}

export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  name: string
) {
  const Wrapped = (props: P) => (
    <ErrorBoundary name={name}>
      <Component {...props} />
    </ErrorBoundary>
  );
  Wrapped.displayName = `withErrorBoundary(${Component.displayName || Component.name || "Component"})`;
  return Wrapped;
}

export default ErrorBoundary;
