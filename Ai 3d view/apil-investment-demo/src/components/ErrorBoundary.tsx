import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}
interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: any) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-2xl mx-auto px-4 py-20 text-center">
          <h2 className="text-xl font-bold text-red-600 mb-4">React Render Error</h2>
          <pre className="text-left text-sm bg-red-50 p-4 rounded-lg overflow-auto max-h-96 mb-4">
            {this.state.error?.message}
            {'\n\n'}
            {this.state.error?.stack}
          </pre>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/'; }}
            className="bg-apil-blue text-white text-sm font-semibold px-6 py-3 rounded-lg"
          >
            Back to Home
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
