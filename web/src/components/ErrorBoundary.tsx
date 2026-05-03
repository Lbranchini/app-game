import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Last-resort safety net for unhandled render or lifecycle errors.
 *
 * React lets a single bug throw and unmount the entire tree — without this
 * boundary the user sees a blank page and a console trace. We catch it,
 * show a recovery screen, and let the user reload or jump back to the
 * Characters page (the closest thing to a home).
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Surface the trace so the dev console still shows what blew up.
    // A real deploy would forward this to Sentry / Datadog here.
    console.error("ErrorBoundary caught:", error, info);
  }

  render(): ReactNode {
    if (this.state.error === null) {
      return this.props.children;
    }
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
        <div className="max-w-lg rounded-xl bg-slate-900 p-6 ring-1 ring-slate-800">
          <h1 className="text-2xl font-bold text-rose-300">Something broke</h1>
          <p className="mt-2 text-sm text-slate-400">
            The page hit an unexpected error. We've logged the trace; you can
            try a fresh load or head back to the Characters page.
          </p>
          <pre className="mt-4 overflow-x-auto rounded bg-slate-950 p-3 text-xs text-slate-400">
            {this.state.error.message}
          </pre>
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold hover:bg-blue-500"
            >
              Reload
            </button>
            <a
              href="/characters"
              className="rounded-md bg-slate-800 px-4 py-2 text-sm ring-1 ring-slate-700 hover:bg-slate-700"
            >
              Back to Characters
            </a>
          </div>
        </div>
      </div>
    );
  }
}
