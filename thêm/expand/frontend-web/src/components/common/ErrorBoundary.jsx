import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled Application Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0f1117] text-gray-100 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-[#181b26] border border-white/10 rounded-2xl p-6 text-center space-y-4 shadow-xl">
            <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">Đã xảy ra lỗi không mong muốn</h2>
            <p className="text-sm text-gray-400">
              Hệ thống đã ghi nhận sự cố. Vui lòng tải lại trang hoặc thử lại sau ít phút.
            </p>
            <div className="pt-2">
              <Button
                variant="primary"
                className="w-full justify-center"
                onClick={() => window.location.reload()}
              >
                <RefreshCw className="w-4 h-4 mr-2" /> Tải Lại Trang
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
