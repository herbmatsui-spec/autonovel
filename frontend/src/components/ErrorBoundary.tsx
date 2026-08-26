import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in React tree:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-[var(--bg-main)] p-6">
          <div className="glass-panel max-w-xl w-full p-8 text-center border border-red-500/30">
            <div className="text-4xl mb-3">⚠️</div>
            <h1 className="text-xl font-bold text-white mb-2">画面描画エラーが発生しました</h1>
            <p className="text-sm text-muted-foreground mb-4">
              予期せぬエラーによりコンポーネントの表示に失敗しました。
            </p>

            {this.state.error && (
              <div className="text-left bg-black/40 p-4 rounded-lg mb-6 overflow-x-auto border border-white/10">
                <p className="text-xs font-mono text-red-400 mb-1 font-bold">
                  {this.state.error.name}: {this.state.error.message}
                </p>
                {this.state.errorInfo?.componentStack && (
                  <pre className="text-[0.7rem] font-mono text-gray-400 whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="btn btn-primary"
              >
                🔄 ページを再読み込み
              </button>
              <button
                onClick={() => {
                  localStorage.clear();
                  window.location.reload();
                }}
                className="btn btn-secondary"
              >
                🧹 キャッシュを初期化して再読み込み
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
