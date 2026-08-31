/**
 * ErrorBoundary.jsx — Catches unhandled render errors across the whole app.
 */
import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMessage: error?.message || 'Unknown error' };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary__icon">⚠️</div>
          <h2 className="error-boundary__title">Something went wrong</h2>
          <p className="error-boundary__detail">{this.state.errorMessage}</p>
          <button className="btn btn--primary" onClick={this.handleReload}>
            Reload App
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
