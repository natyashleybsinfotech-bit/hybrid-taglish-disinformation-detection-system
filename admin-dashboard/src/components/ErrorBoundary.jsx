import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error('Admin dashboard rendering failed.', error);
  }

  render() {
    if (this.state.failed) {
      return <main style={{ padding: 40 }}><section className="card"><h1>The dashboard could not render this page.</h1><p style={{ color: 'var(--text-secondary)', margin: '12px 0' }}>Refresh the page. If the problem continues, check the dashboard runtime log.</p><button className="btn-primary" onClick={() => window.location.reload()}>Reload dashboard</button></section></main>;
    }
    return this.props.children;
  }
}
