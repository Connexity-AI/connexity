'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

import { Button } from '@workspace/ui/components/ui/button';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage?: string;
}

/** Can't catch async http errors. */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: undefined };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message }; // can't log promise
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', { error, errorInfo });
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorMessage: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-xl bg-critical-bg p-4 text-critical">
          <h2 className="truncate text-body font-medium">
            Oops, something went wrong.
          </h2>
          <Button
            variant="secondary"
            onClick={this.handleRetry}
            className="mt-3"
          >
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
