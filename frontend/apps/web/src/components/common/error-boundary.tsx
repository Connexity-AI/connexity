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
        <div className="p-4 border border-red-400 rounded-lg bg-red-50 text-red-800">
          <h2 className="font-semibold text-lg truncate">
            Oops, something went wrong.
          </h2>
          <Button
            variant="destructive"
            onClick={this.handleRetry}
            className="mt-3 bg-red-600 hover:bg-red-700"
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
