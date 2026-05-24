import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="grid min-h-screen place-items-center bg-[#F5F5F7] px-6 text-center dark:bg-black">
          <div className="max-w-md rounded-apple bg-white/80 p-8 shadow-apple dark:bg-white/10">
            <h1 className="text-2xl font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">Something went wrong</h1>
            <p className="mt-3 text-sm text-[#6E6E73] dark:text-[#A1A1A6]">Refresh the page or contact support if the issue continues.</p>
            <button onClick={() => window.location.reload()} className="mt-6 rounded-2xl bg-[#007AFF] px-4 py-2 text-sm font-semibold text-white">Refresh</button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
